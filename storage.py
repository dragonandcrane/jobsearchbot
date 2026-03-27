"""CSV storage: read existing listings, deduplicate, append new ones, backfill gaps.

On re-scrape of an existing URL, updates last_scraped_date (and last_modified_date
if the description changed). Never overwrites the status column.
"""

import csv
import logging
import time
from collections import OrderedDict
from datetime import date
from pathlib import Path
from typing import Callable

_US_STATE_ABBREVS = frozenset({
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
})

import config
from scrapers.base import JobListing

logger = logging.getLogger(__name__)

CSV_COLUMNS = [
    "status",
    "job_site",
    "full_url",
    "location",
    "state",
    "remote",
    "job_type",
    "department",
    "closing_date",
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


def _infer_state(location: str) -> str:
    """Extract 2-letter US state abbreviation from a location string, or ''."""
    if not location:
        return ""
    for part in location.split(","):
        word = part.strip().split()[0].upper().rstrip(".,;") if part.strip() else ""
        if word in _US_STATE_ABBREVS:
            return word
    return ""


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
    for row in rows.values():
        if not row.get("state") and row.get("location"):
            row["state"] = _infer_state(row["location"])
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
        "location": listing.location,
        "state": _infer_state(listing.location),
        "remote": listing.remote,
        "job_type": listing.job_type,
        "department": listing.department,
        "closing_date": listing.closing_date,
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
                for field in ["location", "position", "salary_range", "qualification",
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


_BACKFILL_CSV_FIELDS = ["location", "remote", "job_type", "department", "closing_date"]


def backfill_missing_fields(
    fetch_fn: Callable[[str], dict[str, str]],
    job_site: str,
    delay: float = 0.5,
    limit: int | None = None,
    regen: bool = False,
) -> int:
    """Fill empty detail fields for rows from `job_site`.

    Calls fetch_fn(url) -> dict for each row missing any of: location, remote,
    job_type, department, closing_date.  Also rebuilds the listing.md file when
    full_description is returned.  Returns the count of rows updated.

    limit: if set, stop after processing this many rows.
    """
    from listing_files import listing_has_description, write_listing_file  # avoid circular import

    rows = _load_csv()
    updated = 0
    processed = 0

    for url, row in rows.items():
        if limit is not None and processed >= limit:
            break
        if row.get("job_site", "") != job_site:
            continue

        csv_complete = all(row.get(f, "").strip() for f in _BACKFILL_CSV_FIELDS)
        file_has_desc = (not regen) and listing_has_description(url, job_site)
        if csv_complete and file_has_desc:
            continue  # nothing to do

        processed += 1
        fetched = fetch_fn(url)

        changed = False
        if not csv_complete:
            for field in _BACKFILL_CSV_FIELDS:
                if fetched.get(field) and not row.get(field, "").strip():
                    row[field] = fetched[field]
                    changed = True

        if changed:
            updated += 1
            logger.info(
                f"  backfill {url}: "
                + ", ".join(f"{f}={row[f]!r}" for f in _BACKFILL_CSV_FIELDS if row.get(f))
            )

        # Rebuild listing file whenever we fetched data and the file needs a description
        if not file_has_desc:
            listing = JobListing(
                job_site=row.get("job_site", ""),
                full_url=url,
                position=row.get("position", ""),
                agency_department=row.get("agency_department", ""),
                salary_range=row.get("salary_range", ""),
                location=row.get("location", ""),
                remote=row.get("remote", ""),
                job_type=row.get("job_type", ""),
                department=row.get("department", ""),
                closing_date=row.get("closing_date", ""),
                full_description=fetched.get("full_description", ""),
                education_requirement=row.get("education_requirement", ""),
                contact_name=row.get("contact_name", ""),
                contact_phone=row.get("contact_phone", ""),
                contact_email=row.get("contact_email", ""),
            )
            write_listing_file(listing, force=True)

        time.sleep(delay)

    if updated:
        _save_csv(rows)
    logger.info(f"Backfill complete: {updated} updated, {processed} fetched")
    return updated


def _location_passes_state_filter(location: str, allowed: frozenset[str]) -> bool:
    """Return True if the location's state is in `allowed`, or if it can't be determined."""
    if not location:
        return True
    if "," in location:
        state_word = location.rsplit(",", 1)[1].strip().split()[0].upper().rstrip(".,;")
        return state_word not in _US_STATE_ABBREVS or state_word in allowed
    words = {w.upper().rstrip(".,;") for w in location.split()}
    state_words = words & _US_STATE_ABBREVS
    if not state_words:
        return True
    return bool(state_words & allowed)


def purge_by_location(allowed_states: list[str], job_site: str | None = None) -> int:
    """Remove rows whose location resolves to a state not in `allowed_states`.

    Rows with an empty location are left alone (location may still be unknown).
    If `job_site` is given, only rows from that site are checked.
    Returns the number of rows removed.
    """
    if not allowed_states:
        return 0

    allowed = frozenset(s.upper() for s in allowed_states)
    rows = _load_csv()
    before = len(rows)
    to_delete = [
        url for url, row in rows.items()
        if (job_site is None or row.get("job_site", "") == job_site)
        and not _location_passes_state_filter(row.get("location", ""), allowed)
    ]
    for url in to_delete:
        logger.info(f"  purge (location filter): {rows[url].get('location')!r} — {url}")
        del rows[url]

    if to_delete:
        _save_csv(rows)
    removed = before - len(rows)
    logger.info(f"Location purge complete: {removed} rows removed")
    return removed
