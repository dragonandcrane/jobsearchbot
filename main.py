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
from listing_files import write_listing_file
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
    args = parser.parse_args()

    setup_logging()
    run(source_filter=args.source, limit=args.limit, regen=args.regen)


if __name__ == "__main__":
    main()
