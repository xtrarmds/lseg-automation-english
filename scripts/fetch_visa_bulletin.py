import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import pdfplumber
import requests
from bs4 import BeautifulSoup


INDEX_URL = (
    "https://travel.state.gov/content/travel/en/legal/"
    "visa-law0/visa-bulletin.html"
)

OUTPUT_FILE = Path("docs/result.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; VisaBulletinMonitor/1.0; "
        "+https://github.com/xtrarmds/lseg-automation-english)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

CATEGORY_NAMES = {
    "1st": "EB1",
    "2nd": "EB2",
    "3rd": "EB3",
    "other workers": "EB3OtherWorkers",
    "4th": "EB4",
    "certain religious workers": "EB4CertainReligiousWorkers",
    "5th unreserved": "EB5Unreserved",
    "5th set aside rural": "EB5Rural",
    "5th set aside high unemployment": "EB5HighUnemployment",
    "5th set aside infrastructure": "EB5Infrastructure",
}


def clean_text(value):
    """Normalize whitespace and non-breaking spaces."""
    if value is None:
        return ""

    value = str(value).replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_for_match(value):
    """Create a simplified string for case-insensitive matching."""
    value = clean_text(value).lower()

    replacements = {
        "–": "-",
        "—": "-",
        "‑": "-",
        "\u2019": "'",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return value


def normalize_date(value):
    """
    Convert Department of State values into app-friendly values.

    Examples:
      15NOV22 -> 2022-11-15
      15-NOV-22 -> 2022-11-15
      C -> CURRENT
      U -> UNAVAILABLE
    """
    value = clean_text(value).upper().replace(" ", "")

    if not value:
        return None

    if value in {"C", "CURRENT"}:
        return "CURRENT"

    if value in {"U", "UNAVAILABLE"}:
        return "UNAVAILABLE"

    month_numbers = {
        "JAN": "01",
        "FEB": "02",
        "MAR": "03",
        "APR": "04",
        "MAY": "05",
        "JUN": "06",
        "JUL": "07",
        "AUG": "08",
        "SEP": "09",
        "OCT": "10",
        "NOV": "11",
        "DEC": "12",
    }

    match = re.fullmatch(
        r"(\d{1,2})-?([A-Z]{3})-?(\d{2}|\d{4})",
        value,
    )

    if not match:
        return clean_text(value)

    day, month, year = match.groups()

    if month not in month_numbers:
        return clean_text(value)

    if len(year) == 2:
        numeric_year = int(year)
        year = (
            f"20{numeric_year:02d}"
            if numeric_year <= 69
            else f"19{numeric_year:02d}"
        )

    return f"{year}-{month_numbers[month]}-{int(day):02d}"


def category_key(value):
    """Map an official table category label to a stable JSON key."""
    text = normalize_for_match(value)

    text = text.replace("*", "")
    text = text.replace("employment-", "")
    text = text.replace("employment based", "")
    text = clean_text(text)

    if text.startswith("1st"):
        return "EB1"

    if text.startswith("2nd"):
        return "EB2"

    if text.startswith("3rd"):
        return "EB3"

    if "other workers" in text:
        return "EB3OtherWorkers"

    if text.startswith("4th") and "religious" not in text:
        return "EB4"

    if "certain religious workers" in text:
        return "EB4CertainReligiousWorkers"

    if "5th" in text and "unreserved" in text:
        return "EB5Unreserved"

    if "5th" in text and "rural" in text:
        return "EB5Rural"

    if "5th" in text and (
        "high unemployment" in text
        or "high-unemployment" in text
    ):
        return "EB5HighUnemployment"

    if "5th" in text and "infrastructure" in text:
        return "EB5Infrastructure"

    if text.startswith("5th"):
        return "EB5"

    return None


def is_china_header(value):
    """Identify the China-mainland born table column."""
    text = normalize_for_match(value)
    return "china" in text and "mainland" in text


def identify_table_type(context):
    """
    Determine whether a table is employment Table A or Table B.

    Table A = Final Action Dates
    Table B = Dates for Filing
    """
    text = normalize_for_match(context)

    if "employment" not in text:
        return None

    if "final action dates" in text:
        return "tableA"

    if "dates for filing" in text:
        return "tableB"

    return None


def extract_rows(rows):
    """Extract China employment values from a normalized table matrix."""
    cleaned_rows = []

    for row in rows:
        if not row:
            continue

        cleaned = [clean_text(cell) for cell in row]

        if any(cleaned):
            cleaned_rows.append(cleaned)

    if not cleaned_rows:
        return {}

    header_index = None
    china_index = None

    for row_index, row in enumerate(cleaned_rows[:6]):
        for column_index, cell in enumerate(row):
            if is_china_header(cell):
                header_index = row_index
                china_index = column_index
                break

        if china_index is not None:
            break

    if china_index is None:
        return {}

    values = {}

    for row in cleaned_rows[header_index + 1:]:
        if len(row) <= china_index:
            continue

        category = category_key(row[0])

        # Occasionally the first column is blank because of merged PDF cells.
        if category is None and len(row) > 1:
            category = category_key(row[1])

        if category is None:
            continue

        china_value = normalize_date(row[china_index])

        if china_value:
            values[category] = china_value

    return values


def extract_html_tables(content):
    """Extract employment Table A and Table B from an HTML bulletin."""
    soup = BeautifulSoup(content, "lxml")

    result = {
        "tableA": {},
        "tableB": {},
    }

    tables = soup.find_all("table")

    for table in tables:
        context_parts = []

        previous = table.find_previous(
            ["h1", "h2", "h3", "h4", "h5", "p", "strong"]
        )

        if previous:
            context_parts.append(previous.get_text(" ", strip=True))

        parent = table.parent
        if parent:
            context_parts.append(parent.get_text(" ", strip=True)[:1200])

        context = " ".join(context_parts)
        table_type = identify_table_type(context)

        rows = []

        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            rows.append(
                [cell.get_text(" ", strip=True) for cell in cells]
            )

        # If nearby text was insufficient, inspect the table itself.
        if table_type is None:
            table_type = identify_table_type(
                table.get_text(" ", strip=True)
            )

        if table_type:
            extracted = extract_rows(rows)
            if extracted:
                result[table_type].update(extracted)

    return result


def extract_pdf_tables(content):
    """Extract employment Table A and Table B from a PDF bulletin."""
    result = {
        "tableA": {},
        "tableB": {},
    }

    current_section = None

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            normalized_page_text = normalize_for_match(page_text)

            if (
                "final action dates for employment-based"
                in normalized_page_text
            ):
                current_section = "tableA"

            if (
                "dates for filing of employment-based"
                in normalized_page_text
                or "dates for filing employment-based"
                in normalized_page_text
            ):
                current_section = "tableB"

            tables = page.extract_tables(
                {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "intersection_tolerance": 5,
                    "snap_tolerance": 4,
                    "join_tolerance": 4,
                }
            )

            # Some PDFs have no visible table borders.
            if not tables:
                tables = page.extract_tables(
                    {
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "intersection_tolerance": 5,
                        "snap_tolerance": 4,
                        "join_tolerance": 4,
                        "min_words_vertical": 2,
                        "min_words_horizontal": 1,
                    }
                )

            for table in tables:
                if not table:
                    continue

                flattened = " ".join(
                    clean_text(cell)
                    for row in table
                    if row
                    for cell in row
                    if cell
                )

                table_type = identify_table_type(flattened)

                if table_type is None:
                    table_type = current_section

                if table_type not in {"tableA", "tableB"}:
                    continue

                extracted = extract_rows(table)

                if extracted:
                    result[table_type].update(extracted)

    return result


def get_page(url):
    """Download a page and return response content and content type."""
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=45,
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()

    return response.content, content_type


def find_bulletin_links():
    """Find Current and Upcoming bulletin links on the official index."""
    content, _ = get_page(INDEX_URL)
    soup = BeautifulSoup(content, "lxml")

    links = {
        "current": None,
        "upcoming": None,
    }

    for anchor in soup.find_all("a", href=True):
        text = clean_text(anchor.get_text(" ", strip=True))
        normalized = normalize_for_match(text)
        absolute_url = urljoin(INDEX_URL, anchor["href"])

        if (
            normalized.startswith("current visa bulletin")
            and links["current"] is None
        ):
            links["current"] = {
                "label": text,
                "url": absolute_url,
            }

        if (
            normalized.startswith("upcoming visa bulletin")
            and links["upcoming"] is None
        ):
            links["upcoming"] = {
                "label": text,
                "url": absolute_url,
            }

    if links["current"] is None:
        raise RuntimeError(
            "Could not find the Current Visa Bulletin link."
        )

    return links


def extract_month(label, url):
    """Extract a month/year label from link text or URL."""
    combined = f"{label} {url}"

    match = re.search(
        r"\b("
        r"January|February|March|April|May|June|July|August|"
        r"September|October|November|December"
        r")\s+(\d{4})\b",
        combined,
        re.IGNORECASE,
    )

    if match:
        month = match.group(1).capitalize()
        year = match.group(2)
        return f"{month} {year}"

    return None


def parse_bulletin(label, url):
    """Download and parse one current or upcoming bulletin."""
    content, content_type = get_page(url)

    is_pdf = (
        "application/pdf" in content_type
        or url.lower().split("?")[0].endswith(".pdf")
        or content.startswith(b"%PDF")
    )

    if is_pdf:
        tables = extract_pdf_tables(content)
        source_type = "pdf"
    else:
        tables = extract_html_tables(content)
        source_type = "html"

    if not tables["tableA"] and not tables["tableB"]:
        raise RuntimeError(
            "No China employment-based Table A or Table B data "
            f"was found in {url}"
        )

    return {
        "month": extract_month(label, url),
        "url": url,
        "sourceType": source_type,
        "employmentBased": tables,
    }


def main():
    generated_at = datetime.now(timezone.utc).isoformat()
    links = find_bulletin_links()

    result = {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "country": "CHINA-mainland born",
        "source": {
            "name": "U.S. Department of State Visa Bulletin",
            "indexUrl": INDEX_URL,
        },
        "current": None,
        "upcoming": None,
        "errors": [],
    }

    for bulletin_type in ("current", "upcoming"):
        bulletin_link = links.get(bulletin_type)

        if bulletin_link is None:
            result["errors"].append(
                {
                    "bulletin": bulletin_type,
                    "message": (
                        f"{bulletin_type.capitalize()} bulletin "
                        "link was not available."
                    ),
                }
            )
            continue

        try:
            result[bulletin_type] = parse_bulletin(
                bulletin_link["label"],
                bulletin_link["url"],
            )
        except Exception as error:
            result["errors"].append(
                {
                    "bulletin": bulletin_type,
                    "url": bulletin_link["url"],
                    "message": str(error),
                }
            )

    if (
        result["current"] is None
        and result["upcoming"] is None
    ):
        raise RuntimeError(
            "Neither Current nor Upcoming bulletin could be parsed: "
            + json.dumps(result["errors"], ensure_ascii=False)
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as output:
        json.dump(
            result,
            output,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )
        output.write("\n")

    print(f"Created {OUTPUT_FILE}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
