"""CSV storage: read existing listings, deduplicate, append new ones.

On re-scrape of an existing URL, updates last_scraped_date (and last_modified_date
if the description changed). Never overwrites the status column.
"""

import csv
import logging
from collections import OrderedDict
from datetime import date
from pathlib import Path

import config
from scrapers.base import JobListing

logger = logging.getLogger(__name__)

CSV_COLUMNS = [
    "status",
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
    "contact_name",
    "contact_phone",
    "contact_email",
    "first_scraped_date",
    "last_scraped_date",
    "last_modified_date",
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


def _load_csv() -> OrderedDict[str, dict]:
    """Load entire CSV into an OrderedDict keyed by full_url."""
    _ensure_csv_exists()
    rows: OrderedDict[str, dict] = OrderedDict()
    try:
        with open(config.CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("full_url", "").strip()
                if url:
                    rows[url] = row
    except (OSError, csv.Error) as e:
        logger.warning(f"Error reading CSV: {e}")
    return rows


def _save_csv(rows: OrderedDict[str, dict]) -> None:
    """Write all rows back to the CSV."""
    try:
        with open(config.CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for row in rows.values():
                writer.writerow(row)
    except OSError as e:
        logger.error(f"Failed to write CSV: {e}")


def _listing_to_dict(listing: JobListing) -> dict:
    today = date.today().isoformat()
    return {
        "status": "",  # Initially blank, never override
        "job_site": listing.job_site,
        "full_url": listing.full_url,
        "agency_department": listing.agency_department,
        "position": listing.position,
        "salary_range": listing.salary_range,
        "qualification": listing.qualification,
        "education_requirement": listing.education_requirement,
        "org_boilerplate": listing.org_boilerplate,
        "role_description": listing.role_description,
        "keywords_swe": "; ".join(listing.keywords_swe),
        "keywords_general": "; ".join(listing.keywords_general),
        "keywords_domain": "; ".join(listing.keywords_domain),
        "contact_name": listing.contact_name,
        "contact_phone": listing.contact_phone,
        "contact_email": listing.contact_email,
        "first_scraped_date": today,
        "last_scraped_date": today,
        "last_modified_date": today,
    }


def _content_changed(existing: dict, new: dict) -> bool:
    """Check if any substantive content fields changed (not dates/status)."""
    compare_fields = [
        "position", "salary_range", "qualification",
        "education_requirement", "role_description",
    ]
    for field in compare_fields:
        old_val = existing.get(field, "").strip()
        new_val = new.get(field, "").strip()
        if old_val != new_val and new_val:
            return True
    return False


def merge_listings(listings: list[JobListing]) -> tuple[int, int]:
    """Merge scraped listings into the CSV.

    - New URLs get appended.
    - Existing URLs get last_scraped_date updated.
    - If content changed, last_modified_date is also updated.
    - status is never overwritten.

    Returns (new_count, updated_count).
    """
    if not listings:
        return 0, 0

    rows = _load_csv()
    today = date.today().isoformat()
    new_count = 0
    updated_count = 0

    for listing in listings:
        url = listing.full_url.strip()
        if not url:
            continue

        new_row = _listing_to_dict(listing)

        if url in rows:
            # Existing listing - update dates, preserve status
            existing = rows[url]
            existing["last_scraped_date"] = today
            if _content_changed(existing, new_row):
                existing["last_modified_date"] = today
                # Update content fields but preserve status
                for field in ["position", "salary_range", "qualification",
                              "education_requirement", "org_boilerplate",
                              "role_description", "keywords_swe",
                              "keywords_general", "keywords_domain",
                              "contact_name", "contact_phone", "contact_email"]:
                    if new_row[field]:
                        existing[field] = new_row[field]
            updated_count += 1
        else:
            rows[url] = new_row
            new_count += 1

    _save_csv(rows)
    logger.info(
        f"CSV updated: {new_count} new, {updated_count} updated, "
        f"{len(rows)} total"
    )
    return new_count, updated_count
