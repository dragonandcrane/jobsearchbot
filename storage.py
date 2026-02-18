"""CSV storage: read existing listings, deduplicate, append new ones."""

import csv
import logging
from datetime import date
from pathlib import Path

import config
from scrapers.base import JobListing

logger = logging.getLogger(__name__)

CSV_COLUMNS = [
    "date_found",
    "job_site",
    "full_url",
    "agency_department",
    "position",
    "salary_range",
    "qualification",
    "education_requirement",
    "org_boilerplate",
    "role_description",
    "keywords_swe",
    "keywords_general",
    "keywords_domain",
]


def _ensure_csv_exists() -> None:
    """Create the CSV with headers if it doesn't exist yet."""
    path = config.CSV_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)
        logger.info(f"Created new CSV at {path}")


def load_existing_urls() -> set[str]:
    """Read the CSV and return a set of all URLs already recorded."""
    _ensure_csv_exists()
    urls = set()
    try:
        with open(config.CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("full_url", "").strip()
                if url:
                    urls.add(url)
    except (OSError, csv.Error) as e:
        logger.warning(f"Error reading CSV: {e}")
    return urls


def deduplicate(listings: list[JobListing]) -> list[JobListing]:
    """Remove listings whose URLs are already in the CSV or duplicated in batch."""
    existing = load_existing_urls()
    seen = set()
    unique = []
    for listing in listings:
        url = listing.full_url.strip()
        if url and url not in existing and url not in seen:
            seen.add(url)
            unique.append(listing)
    logger.info(
        f"Dedup: {len(listings)} total -> {len(unique)} new "
        f"({len(listings) - len(unique)} duplicates)"
    )
    return unique


def _listing_to_row(listing: JobListing) -> list[str]:
    return [
        date.today().isoformat(),
        listing.job_site,
        listing.full_url,
        listing.agency_department,
        listing.position,
        listing.salary_range,
        listing.qualification,
        listing.education_requirement,
        listing.org_boilerplate,
        listing.role_description,
        "; ".join(listing.keywords_swe),
        "; ".join(listing.keywords_general),
        "; ".join(listing.keywords_domain),
    ]


def append_listings(listings: list[JobListing]) -> int:
    """Append new listings to the CSV. Returns count of rows written."""
    if not listings:
        return 0
    _ensure_csv_exists()
    try:
        with open(config.CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for listing in listings:
                writer.writerow(_listing_to_row(listing))
    except OSError as e:
        logger.error(f"Failed to write CSV: {e}")
        return 0
    logger.info(f"Appended {len(listings)} new listings to CSV")
    return len(listings)
