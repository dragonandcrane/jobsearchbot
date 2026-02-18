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
from processing.boilerplate import process_boilerplate
from processing.keywords import process_keywords
from storage import deduplicate, append_listings


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

    if not all_listings:
        logger.info("No listings found, exiting")
        return

    # Phase 2: Deduplicate against existing CSV
    new_listings = deduplicate(all_listings)
    if not new_listings:
        logger.info("No new listings after deduplication, exiting")
        return

    # Phase 3: Process descriptions
    logger.info("Processing boilerplate detection...")
    new_listings = process_boilerplate(new_listings)

    logger.info("Extracting keywords...")
    new_listings = process_keywords(new_listings)

    # Phase 4: Save to CSV
    written = append_listings(new_listings)
    logger.info(
        f"=== Done: {written} new listings added to {config.CSV_PATH.name} ==="
    )


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
