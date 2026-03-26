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

import config
from scrapers import ALL_SCRAPERS
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


def run(source_filter: str | None = None) -> None:
    logger = logging.getLogger("main")
    logger.info("=== Job Search Bot starting ===")

    # Phase 1: Scrape all sources
    all_listings: list[JobListing] = []
    counts: dict[str, int] = {}

    for scraper_cls in ALL_SCRAPERS:
        scraper = scraper_cls()
        if source_filter and scraper.name != source_filter:
            continue
        results = scraper.safe_scrape()
        counts[scraper.name] = len(results)
        all_listings.extend(results)

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

        # Phase 3: Write per-listing detail files (idempotent).
        # governmentjobs listings are skipped here — backfill writes them after
        # fetching the detail page and applying the location filter.
        written = sum(
            1 for l in all_listings
            if l.job_site != "governmentjobs.com" and write_listing_file(l) is not None
        )
        logger.info(f"Listing files: {written} written")

        # Phase 4: Merge into CSV (dedup, update dates, preserve status)
        new_count, updated_count = merge_listings(all_listings)
        logger.info(
            f"Merge complete: {new_count} new, {updated_count} updated "
            f"in {config.CSV_PATH.name}"
        )
    else:
        logger.info("No new listings found")

    # Phase 5: Backfill detail fields for governmentjobs rows, apply location
    # filter, and write listing.md files — all in one pass.
    # Runs unconditionally so re-runs fill gaps even when scrape yields nothing.
    if not source_filter or source_filter == "governmentjobs":
        logger.info("Backfilling governmentjobs detail fields...")
        location_filter = (
            frozenset(s.upper() for s in config.LOCATION_FILTER_STATES)
            if config.LOCATION_FILTER_STATES else None
        )
        backfill_missing_fields(
            fetch_location_remote, "governmentjobs.com",
            location_filter=location_filter,
        )

    logger.info("=== Done ===")


def main() -> None:
    parser = argparse.ArgumentParser(description="Job Search Bot")
    parser.add_argument(
        "--source",
        choices=["usajobs", "governmentjobs", "indeed", "linkedin"],
        help="Only run a specific scraper",
    )
    args = parser.parse_args()

    setup_logging()
    run(source_filter=args.source)


if __name__ == "__main__":
    main()
