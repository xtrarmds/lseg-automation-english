import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright


BASE_URL = "https://visa-bulletin.us/employment-based/china/"

URLS = {
    "finalActionDates": (
        f"{BASE_URL}?action_type=final_action"
    ),
    "datesForFiling": (
        f"{BASE_URL}?action_type=filing"
    ),
}

OUTPUT_FILE = Path("docs/result.json")


# These are the categories that the script attempts to extract.
#
# EB-1, EB-2, EB-3 and EB-3 Other Workers are required.
# EB-4 and EB-5 categories are optional because the source site
# may associate some legacy EB-5 categories with an older bulletin.
CATEGORY_PATTERNS = {
    "EB-1": (
        r"EB-1:\s*Priority Workers"
    ),
    "EB-2": (
        r"EB-2:\s*Professionals with Advanced Degrees"
    ),
    "EB-3": (
        r"EB-3:\s*Skilled Workers,\s*Professionals"
    ),
    "EB-3 Other Workers": (
        r"EB-3:\s*Other Workers"
    ),
    "EB-4 Special Immigrants": (
        r"EB-4:\s*Special Immigrants"
    ),
    "EB-4 Religious Workers": (
        r"EB-4:\s*Religious Workers"
    ),
    "EB-5 Unreserved": (
        r"EB-5:\s*Unreserved"
    ),
    "EB-5 Targeted Employment Areas / Regional Centers": (
        r"EB-5:\s*Targeted Employment Areas\s*/\s*"
        r"Regional Centers"
    ),
}


REQUIRED_CATEGORIES = {
    "EB-1",
    "EB-2",
    "EB-3",
    "EB-3 Other Workers",
}


MONTH_NUMBERS = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}


MONTH_ABBREVIATIONS = {
    "01": "Jan",
    "02": "Feb",
    "03": "Mar",
    "04": "Apr",
    "05": "May",
    "06": "Jun",
    "07": "Jul",
    "08": "Aug",
    "09": "Sep",
    "10": "Oct",
    "11": "Nov",
    "12": "Dec",
}


# This pattern must always be enclosed in a non-capturing group
# when combined with additional regex expressions because it
# contains alternation operators.
MONTH_PATTERN = (
    r"Jan(?:uary)?|"
    r"Feb(?:ruary)?|"
    r"Mar(?:ch)?|"
    r"Apr(?:il)?|"
    r"May|"
    r"Jun(?:e)?|"
    r"Jul(?:y)?|"
    r"Aug(?:ust)?|"
    r"Sep(?:t(?:ember)?|tember)?|"
    r"Oct(?:ober)?|"
    r"Nov(?:ember)?|"
    r"Dec(?:ember)?"
)


def normalize_bulletin_month(value: str) -> str:
    """
    Convert a bulletin month to YYYY-MM.

    Examples:
        August 2026 -> 2026-08
        Aug 2026    -> 2026-08
        Apr 2022    -> 2022-04
    """
    value = " ".join(value.split()).strip()

    match = re.fullmatch(
        rf"((?:{MONTH_PATTERN}))\s+(\d{{4}})",
        value,
        re.IGNORECASE,
    )

    if not match:
        raise ValueError(
            f"Unsupported bulletin month: {value!r}"
        )

    month_name = match.group(1).lower()
    year = match.group(2)

    month_number = MONTH_NUMBERS.get(month_name)

    if month_number is None:
        raise ValueError(
            f"Unknown bulletin month name: {month_name!r}"
        )

    return f"{year}-{month_number}"


def format_bulletin_month(value: str) -> str:
    """
    Convert YYYY-MM to an abbreviated display value.

    Example:
        2026-08 -> Aug 2026
    """
    match = re.fullmatch(
        r"(\d{4})-(\d{2})",
        value,
    )

    if not match:
        raise ValueError(
            f"Invalid normalized bulletin month: {value!r}"
        )

    year, month_number = match.groups()
    month_name = MONTH_ABBREVIATIONS.get(month_number)

    if month_name is None:
        raise ValueError(
            f"Invalid bulletin month number: {month_number!r}"
        )

    return f"{month_name} {year}"


def normalize_cutoff(value: str) -> str:
    """
    Convert cutoff values to consistent JSON values.

    Examples:
        Dec 01, 2023    -> 2023-12-01
        December 1, 2023 -> 2023-12-01
        Current          -> C
        Unavailable      -> U
    """
    value = " ".join(value.split()).strip()

    normalized_lower = value.lower()

    if normalized_lower in {
        "current",
        "c",
    }:
        return "C"

    if normalized_lower in {
        "unavailable",
        "unauthorized",
        "u",
    }:
        return "U"

    match = re.fullmatch(
        rf"((?:{MONTH_PATTERN}))"
        rf"\s+(\d{{1,2}}),\s+(\d{{4}})",
        value,
        re.IGNORECASE,
    )

    if not match:
        raise ValueError(
            f"Unsupported cutoff value: {value!r}"
        )

    month_name = match.group(1).lower()
    day = int(match.group(2))
    year = match.group(3)

    month_number = MONTH_NUMBERS.get(month_name)

    if month_number is None:
        raise ValueError(
            f"Unknown cutoff month: {month_name!r}"
        )

    if day < 1 or day > 31:
        raise ValueError(
            f"Invalid cutoff day: {day}"
        )

    return f"{year}-{month_number}-{day:02d}"


def extract_latest_bulletin_month(text: str) -> str:
    """
    Extract the latest bulletin month near the top of the page.

    Supported examples:
        Latest edition: August 2026 Visa Bulletin
        Visa Bulletin — August 2026
    """
    patterns = [
        (
            rf"Latest edition:\s*"
            rf"((?:{MONTH_PATTERN})\s+\d{{4}})"
            rf"\s+Visa Bulletin"
        ),
        (
            rf"Visa Bulletin\s*[—-]\s*"
            rf"((?:{MONTH_PATTERN})\s+\d{{4}})"
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        bulletin_text = " ".join(
            match.group(1).split()
        )

        print(
            f"Latest bulletin text matched: {bulletin_text}"
        )

        return normalize_bulletin_month(
            bulletin_text
        )

    raise RuntimeError(
        "Could not determine the latest Visa Bulletin month"
    )


def extract_category(
    text: str,
    category_pattern: str,
) -> tuple[str, str]:
    """
    Extract the bulletin month and Current Cutoff for a category.

    Expected rendered text resembles:

        EB-1: Priority Workers
        Aug 2026
        Jul 01, 2023
        Jul 01, 2023
        Jun 07-Aug 26, 2023
        ...

    The first date after the bulletin month is the Current Cutoff.
    All later dates are predictions and are ignored.
    """
    category_match = re.search(
        category_pattern,
        text,
        re.IGNORECASE,
    )

    if not category_match:
        raise RuntimeError(
            "Category heading not found using pattern: "
            f"{category_pattern}"
        )

    # Only inspect the text immediately after the category heading.
    # This helps avoid accidentally matching historical chart data.
    section = text[
        category_match.end():
        category_match.end() + 700
    ]

    bulletin_match = re.search(
        rf"\b((?:{MONTH_PATTERN}))"
        rf"\s+(\d{{4}})\b",
        section,
        re.IGNORECASE,
    )

    if not bulletin_match:
        raise RuntimeError(
            "Bulletin month not found after category: "
            f"{category_pattern}"
        )

    bulletin_text = (
        f"{bulletin_match.group(1)} "
        f"{bulletin_match.group(2)}"
    )

    bulletin_month = normalize_bulletin_month(
        bulletin_text
    )

    # Search only after the category's bulletin month.
    after_bulletin = section[
        bulletin_match.end():
    ]

    cutoff_match = re.search(
        rf"\b("
        rf"(?:{MONTH_PATTERN})"
        rf"\s+\d{{1,2}},\s+\d{{4}}"
        rf"|Current"
        rf"|Unavailable"
        rf"|Unauthorized"
        rf"|C"
        rf"|U"
        rf")\b",
        after_bulletin,
        re.IGNORECASE,
    )

    if not cutoff_match:
        raise RuntimeError(
            "Current Cutoff not found after category: "
            f"{category_pattern}"
        )

    cutoff = normalize_cutoff(
        cutoff_match.group(1)
    )

    return bulletin_month, cutoff


async def fetch_page_text(
    page,
    url: str,
) -> str:
    """
    Load the page through Chromium and return rendered body text.
    """
    print()
    print(f"Opening URL: {url}")

    response = await page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=90000,
    )

    if response is None:
        raise RuntimeError(
            f"No HTTP response received for {url}"
        )

    print(f"HTTP status: {response.status}")
    print(f"Final URL: {page.url}")

    if response.status >= 400:
        raise RuntimeError(
            f"HTTP {response.status} returned for {url}"
        )

    # Wait for client-side rendering to finish.
    await page.wait_for_timeout(7000)

    body = page.locator("body")

    text = await body.inner_text(
        timeout=30000
    )

    title = await page.title()

    print(f"Page title: {title}")
    print(f"Body text length: {len(text)}")

    if "Current Cutoff" not in text:
        raise RuntimeError(
            "Page loaded, but the Current Cutoff table "
            f"was not found: {url}"
        )

    if "EB-1: Priority Workers" not in text:
        raise RuntimeError(
            "Page loaded, but EB-1 data was not found: "
            f"{url}"
        )

    return text


async def extract_chart(
    page,
    chart_name: str,
    url: str,
) -> dict:
    """
    Extract one chart.

    Required categories must exist and belong to the latest
    bulletin. Optional categories are published only if they
    also belong to the latest bulletin.
    """
    print()
    print("=" * 70)
    print(f"Fetching {chart_name}: {url}")
    print("=" * 70)

    text = await fetch_page_text(
        page,
        url,
    )

    latest_month = extract_latest_bulletin_month(
        text
    )

    print(
        "Latest bulletin detected: "
        f"{format_bulletin_month(latest_month)}"
    )

    current_values = {}
    category_bulletins = {}
    skipped_categories = {}
    required_row_months = set()

    for category_name, category_pattern in CATEGORY_PATTERNS.items():
        try:
            category_month, cutoff = extract_category(
                text,
                category_pattern,
            )

            category_bulletins[
                category_name
            ] = format_bulletin_month(
                category_month
            )

            if category_name in REQUIRED_CATEGORIES:
                required_row_months.add(
                    category_month
                )

            # Only publish category data belonging to the current
            # latest bulletin. Some legacy EB-5 categories on the
            # website may still be associated with Apr 2022.
            if category_month == latest_month:
                current_values[
                    category_name
                ] = cutoff

                print(
                    f"  {category_name}: {cutoff} "
                    f"(bulletin: "
                    f"{format_bulletin_month(category_month)})"
                )
            else:
                skipped_categories[
                    category_name
                ] = {
                    "cutoff": cutoff,
                    "bulletin": format_bulletin_month(
                        category_month
                    ),
                    "reason": (
                        "Category does not belong to "
                        "the latest bulletin"
                    ),
                }

                print(
                    f"  Skipping {category_name}: {cutoff} "
                    f"(category bulletin: "
                    f"{format_bulletin_month(category_month)}, "
                    f"latest bulletin: "
                    f"{format_bulletin_month(latest_month)})"
                )

        except (RuntimeError, ValueError) as exc:
            if category_name in REQUIRED_CATEGORIES:
                raise RuntimeError(
                    f"Required category {category_name} "
                    f"failed: {exc}"
                ) from exc

            print(
                f"  Warning: optional category "
                f"{category_name}: {exc}"
            )

    missing_categories = (
        REQUIRED_CATEGORIES
        - set(current_values.keys())
    )

    if missing_categories:
        raise RuntimeError(
            f"{chart_name} is missing required "
            f"current categories: "
            f"{', '.join(sorted(missing_categories))}"
        )

    if len(required_row_months) != 1:
        displayed_months = [
            format_bulletin_month(month)
            for month in sorted(required_row_months)
        ]

        raise RuntimeError(
            f"{chart_name} required categories contain "
            f"inconsistent bulletin months: "
            f"{displayed_months}"
        )

    required_month = next(
        iter(required_row_months)
    )

    if required_month != latest_month:
        raise RuntimeError(
            f"{chart_name} latest edition is "
            f"{format_bulletin_month(latest_month)}, "
            f"but required categories show "
            f"{format_bulletin_month(required_month)}"
        )

    return {
        "bulletin": latest_month,
        "values": current_values,
        "categoryBulletins": category_bulletins,
        "skippedCategories": skipped_categories,
    }


def load_existing_result() -> dict | None:
    """
    Load the existing result for diagnostic purposes.

    The existing result is not overwritten until both charts
    have been fetched and validated successfully.
    """
    if not OUTPUT_FILE.exists():
        return None

    try:
        return json.loads(
            OUTPUT_FILE.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError):
        return None


async def main() -> None:
    existing_result = load_existing_result()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/126.0.0.0 "
                "Safari/537.36"
            ),
            locale="en-US",
            viewport={
                "width": 1440,
                "height": 1200,
            },
        )

        page = await context.new_page()

        try:
            final_action = await extract_chart(
                page,
                "Final Action Dates",
                URLS["finalActionDates"],
            )

            dates_for_filing = await extract_chart(
                page,
                "Dates for Filing",
                URLS["datesForFiling"],
            )
        finally:
            await context.close()
            await browser.close()

    if (
        final_action["bulletin"]
        != dates_for_filing["bulletin"]
    ):
        raise RuntimeError(
            "Final Action and Dates for Filing "
            "bulletin months differ: "
            f"{format_bulletin_month(final_action['bulletin'])} "
            "vs "
            f"{format_bulletin_month(dates_for_filing['bulletin'])}"
        )

    bulletin_month = final_action["bulletin"]

    result = {
        "schemaVersion": 2,
        "generatedAt": (
            datetime.now(timezone.utc).isoformat()
        ),
        "status": "ok",
        "source": {
            "name": "visa-bulletin.us",
            "country": "China (mainland born)",
            "category": "Employment-Based",
            "finalActionUrl": (
                URLS["finalActionDates"]
            ),
            "datesForFilingUrl": (
                URLS["datesForFiling"]
            ),
            "notice": (
                "Third-party data source. Prediction columns "
                "are not included. Verify important immigration "
                "decisions against official USCIS and Department "
                "of State information."
            ),
        },
        "latest": {
            "bulletin": format_bulletin_month(
                bulletin_month
            ),
            "bulletinKey": bulletin_month,
            "finalActionDates": (
                final_action["values"]
            ),
            "datesForFiling": (
                dates_for_filing["values"]
            ),
            "categoryBulletins": {
                "finalActionDates": (
                    final_action["categoryBulletins"]
                ),
                "datesForFiling": (
                    dates_for_filing["categoryBulletins"]
                ),
            },
            "skippedLegacyCategories": {
                "finalActionDates": (
                    final_action["skippedCategories"]
                ),
                "datesForFiling": (
                    dates_for_filing["skippedCategories"]
                ),
            },
        },
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Write to a temporary file first. A failed run will therefore
    # not corrupt the previously published JSON.
    temporary_file = OUTPUT_FILE.with_suffix(
        ".json.tmp"
    )

    temporary_file.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_file.replace(
        OUTPUT_FILE
    )

    print()
    print("=" * 70)
    print(f"Successfully wrote {OUTPUT_FILE}")
    print("=" * 70)

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    if existing_result is not None:
        print()
        print(
            "Previous result existed and was replaced only "
            "after both charts passed validation."
        )


if __name__ == "__main__":
    asyncio.run(main())
