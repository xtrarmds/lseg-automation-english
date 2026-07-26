import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright


BASE_URL = "https://visa-bulletin.us/employment-based/china/"

URLS = {
    "finalActionDates": f"{BASE_URL}?action_type=final_action",
    "datesForFiling": f"{BASE_URL}?action_type=filing",
}

OUTPUT_FILE = Path("docs/result.json")

# 第一版先抓取最重要、最容易准确解析的类别。
CATEGORY_PATTERNS = {
    "EB-1": r"EB-1:\s*Priority Workers",
    "EB-2": r"EB-2:\s*Professionals with Advanced Degrees",
    "EB-3": r"EB-3:\s*Skilled Workers,\s*Professionals",
    "EB-3 Other Workers": r"EB-3:\s*Other Workers",
    "EB-4 Special Immigrants": r"EB-4:\s*Special Immigrants",
    "EB-4 Religious Workers": r"EB-4:\s*Religious Workers",
    "EB-5 Unreserved": r"EB-5:\s*Unreserved",
    "EB-5 Targeted Employment Areas / Regional Centers": (
        r"EB-5:\s*Targeted Employment Areas\s*/\s*Regional Centers"
    ),
}

REQUIRED_CATEGORIES = {
    "EB-1",
    "EB-2",
    "EB-3",
    "EB-3 Other Workers",
}

MONTHS = {
    "Jan": "01",
    "Feb": "02",
    "Mar": "03",
    "Apr": "04",
    "May": "05",
    "Jun": "06",
    "Jul": "07",
    "Aug": "08",
    "Sep": "09",
    "Oct": "10",
    "Nov": "11",
    "Dec": "12",
}


def normalize_cutoff(value: str) -> str:
    """
    Convert values such as:
      Dec 01, 2023 -> 2023-12-01
      Current      -> C
      Unavailable  -> U
    """
    value = " ".join(value.split()).strip()

    if value.lower() in {"current", "c"}:
        return "C"

    if value.lower() in {"unavailable", "unauthorized", "u"}:
        return "U"

    match = re.fullmatch(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+(\d{1,2}),\s+(\d{4})",
        value,
    )

    if not match:
        raise ValueError(f"Unsupported cutoff value: {value!r}")

    month, day, year = match.groups()
    return f"{year}-{MONTHS[month]}-{int(day):02d}"


def extract_bulletin_month(text: str) -> str:
    patterns = [
        r"Latest edition:\s*([A-Z][a-z]+\s+\d{4})\s+Visa Bulletin",
        r"Visa Bulletin\s*[—-]\s*([A-Z][a-z]+\s+\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return " ".join(match.group(1).split())

    raise RuntimeError("Could not determine the latest Visa Bulletin month")


def extract_category(text: str, category_pattern: str) -> tuple[str, str]:
    """
    Expected page text near a category:

    EB-1: Priority Workers
    Aug 2026
    Dec 01, 2023
    Dec 01, 2023
    ...

    Only the first date after the bulletin month is Current Cutoff.
    The later dates belong to prediction columns and must be ignored.
    """
    pattern = (
        rf"{category_pattern}"
        rf"\s+"
        rf"([A-Z][a-z]{{2}}\s+\d{{4}})"
        rf"\s+"
        rf"("
        rf"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        rf"\s+\d{{1,2}},\s+\d{{4}}"
        rf"|Current"
        rf"|Unavailable"
        rf"|C"
        rf"|U"
        rf")"
    )

    match = re.search(pattern, text, re.IGNORECASE)

    if not match:
        raise RuntimeError(
            f"Could not extract category using pattern: {category_pattern}"
        )

    bulletin = " ".join(match.group(1).split())
    cutoff = normalize_cutoff(match.group(2))

    return bulletin, cutoff


async def fetch_page_text(page, url: str) -> str:
    response = await page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=90000,
    )

    if response is None:
        raise RuntimeError(f"No HTTP response received for {url}")

    if response.status >= 400:
        raise RuntimeError(f"HTTP {response.status} returned for {url}")

    # Give client-side rendering time to finish.
    await page.wait_for_timeout(5000)

    body = page.locator("body")
    text = await body.inner_text(timeout=30000)

    if "Current Cutoff" not in text:
        raise RuntimeError(
            f"Page loaded but expected table content was not found: {url}"
        )

    return text


async def extract_chart(page, chart_name: str, url: str) -> dict:
    print(f"Fetching {chart_name}: {url}")

    text = await fetch_page_text(page, url)
    latest_month = extract_bulletin_month(text)

    data = {}
    row_months = set()

    for category_name, category_pattern in CATEGORY_PATTERNS.items():
        try:
            row_month, cutoff = extract_category(text, category_pattern)
            data[category_name] = cutoff
            row_months.add(row_month)
            print(f"  {category_name}: {cutoff}")
        except RuntimeError as exc:
            # Optional EB-4/EB-5 rows may change naming.
            if category_name in REQUIRED_CATEGORIES:
                raise
            print(f"  Warning: {category_name}: {exc}")

    missing = REQUIRED_CATEGORIES - data.keys()

    if missing:
        raise RuntimeError(
            f"{chart_name} is missing required categories: "
            f"{', '.join(sorted(missing))}"
        )

    if len(row_months) != 1:
        raise RuntimeError(
            f"{chart_name} contains inconsistent bulletin months: "
            f"{sorted(row_months)}"
        )

    row_month = next(iter(row_months))

    if latest_month.lower() != row_month.lower():
        raise RuntimeError(
            f"Latest edition is {latest_month}, but table rows show {row_month}"
        )

    return {
        "bulletin": row_month,
        "values": data,
    }


def load_existing_result() -> dict | None:
    if not OUTPUT_FILE.exists():
        return None

    try:
        return json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
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
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1440, "height": 1200},
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
            await browser.close()

    if final_action["bulletin"] != dates_for_filing["bulletin"]:
        raise RuntimeError(
            "Final Action and Dates for Filing bulletin months differ: "
            f"{final_action['bulletin']} vs "
            f"{dates_for_filing['bulletin']}"
        )

    result = {
        "schemaVersion": 2,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "source": {
            "name": "visa-bulletin.us",
            "country": "China (mainland born)",
            "category": "Employment-Based",
            "finalActionUrl": URLS["finalActionDates"],
            "datesForFilingUrl": URLS["datesForFiling"],
            "notice": (
                "Third-party data source. Predictions are not included. "
                "Verify important decisions against official USCIS and "
                "Department of State information."
            ),
        },
        "latest": {
            "bulletin": final_action["bulletin"],
            "finalActionDates": final_action["values"],
            "datesForFiling": dates_for_filing["values"],
        },
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = OUTPUT_FILE.with_suffix(".json.tmp")
    temporary_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_file.replace(OUTPUT_FILE)

    print(f"Successfully wrote {OUTPUT_FILE}")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # existing_result is intentionally only kept for diagnostics.
    # The output file is replaced only after both charts pass validation.
    if existing_result:
        print("Previous result existed and was replaced after validation.")


if __name__ == "__main__":
    asyncio.run(main())
