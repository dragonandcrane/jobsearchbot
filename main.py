#!/usr/bin/env python3
"""Job Search Bot - scrapes multiple job sites for public/nonprofit tech roles.

Searches for DevOps, SWE, SDET, IT, and InfoSec positions that are:
- Public sector or nonprofit
- 100% remote
- Full-time with flexible hours, or part-time

Run manually:  python main.py
Run one source: python main.py --source usajobs
"""

import argparse
import logging
import sys
from pathlib import Path

import config
from scrapers import ALL_SCRAPERS
from scrapers.base import JobListing
from scrapers.governmentjobs import fetch_location_remote
from processing.boilerplate import process_boilerplate
from processing.keywords import process_keywords
from listing_files import write_listing_file, write_resume_file
from storage import backfill_missing_fields, merge_listings


def setup_logging() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(config.LOG_PATH),
        ],
    )


def run_single_url(url: str, regen: bool = False) -> None:
    """Fetch, process, and write listing.md + resume.md for a single job URL."""
    from urllib.parse import urlparse
    logger = logging.getLogger("main")

    hostname = urlparse(url).netloc.removeprefix("www.")
    logger.info(f"Single-URL mode: {url} ({hostname})")

    listing = None

    if "governmentjobs.com" in hostname:
        fields = fetch_location_remote(url)
        listing = JobListing(
            job_site="governmentjobs.com",
            full_url=url,
            location=fields.get("location", ""),
            remote=fields.get("remote", ""),
            job_type=fields.get("job_type", ""),
            department=fields.get("department", ""),
            closing_date=fields.get("closing_date", ""),
            full_description=fields.get("full_description", ""),
        )
    elif "linkedin.com" in hostname:
        from scrapers.linkedin import fetch_single_listing
        listing = fetch_single_listing(url)
    else:
        logger.error(f"No single-URL fetcher available for {hostname}")
        return

    if not listing:
        logger.error(f"Failed to fetch listing for {url}")
        return

    listings = [listing]
    listings = process_boilerplate(listings)
    listings = process_keywords(listings)
    listing = listings[0]

    listing_path = write_listing_file(listing, force=regen)
    if listing_path:
        logger.info(f"Wrote listing.md: {listing_path}")
    else:
        logger.info("listing.md already exists (use --regen to overwrite)")

    resume_path = write_resume_file(listing, force=regen)
    if resume_path:
        logger.info(f"Wrote resume.md: {resume_path}")
    else:
        logger.info("resume.md already exists (use --regen to overwrite)")

    new_count, updated_count = merge_listings([listing])
    logger.info(f"CSV: {new_count} new, {updated_count} updated")


def run(source_filter: str | None = None, limit: int | None = None, regen: bool = False) -> None:
    logger = logging.getLogger("main")
    logger.info("=== Job Search Bot starting ===")

    # Phase 1: Scrape all sources
    all_listings: list[JobListing] = []
    counts: dict[str, int] = {}

    for scraper_cls in ALL_SCRAPERS:
        if limit is not None and len(all_listings) >= limit:
            break
        scraper = scraper_cls()
        if source_filter and scraper.name != source_filter:
            continue
        remaining = (limit - len(all_listings)) if limit is not None else None
        results = scraper.safe_scrape(limit=remaining)
        counts[scraper.name] = len(results)
        all_listings.extend(results)

    if limit is not None:
        logger.info(f"Limit applied: {len(all_listings)} listings")

    logger.info(
        f"Scraping complete: {len(all_listings)} total listings "
        f"({', '.join(f'{k}: {v}' for k, v in counts.items())})"
    )

    if all_listings:
        # Phase 2: Process descriptions
        logger.info("Processing boilerplate detection...")
        all_listings = process_boilerplate(all_listings)

        logger.info("Extracting keywords...")
        all_listings = process_keywords(all_listings)

        # Phase 3: Write per-listing detail files (idempotent)
        written = sum(1 for l in all_listings if write_listing_file(l) is not None)
        logger.info(f"Listing files: {written} written")

        # Phase 4: Merge into CSV (dedup, update dates, preserve status)
        new_count, updated_count = merge_listings(all_listings)
        logger.info(
            f"Merge complete: {new_count} new, {updated_count} updated "
            f"in {config.CSV_PATH.name}"
        )
    else:
        logger.info("No new listings found")

    # Phase 5: Backfill missing location/remote for governmentjobs rows
    # Runs unconditionally so re-runs fill gaps even when scrape yields nothing new.
    if not source_filter or source_filter == "governmentjobs":
        logger.info("Backfilling missing location/remote fields...")
        backfill_missing_fields(fetch_location_remote, "governmentjobs.com", limit=limit, regen=regen)

    logger.info("=== Done ===")


def main() -> None:
    parser = argparse.ArgumentParser(description="Job Search Bot")
    parser.add_argument(
        "--source",
        choices=["usajobs", "governmentjobs", "indeed", "linkedin"],
        help="Only run a specific scraper",
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Process at most N listings (for rapid iteration)",
    )
    parser.add_argument(
        "--regen",
        action="store_true",
        help="Force regeneration of all listing files (re-fetches and rewrites even if file exists)",
    )
    parser.add_argument(
        "--url",
        metavar="URL",
        help="Fetch, process, and write listing.md + resume.md for a single job URL",
    )
    args = parser.parse_args()

    setup_logging()
    if args.url:
        run_single_url(args.url, regen=args.regen)
    else:
        run(source_filter=args.source, limit=args.limit, regen=args.regen)


if __name__ == "__main__":
    main()
