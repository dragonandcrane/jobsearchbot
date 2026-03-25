#!/usr/bin/env python3
"""Verify that the location filter drops non-CA listings.

Tests two things:
1. Unit: _passes_location_filter accepts CA and rejects WA/OR/NY/etc.
2. Live: first page of "Software Engineer" results are all CA (or blank location).

Usage:
    python test_location_filter.py           # unit tests only (fast)
    python test_location_filter.py --live    # also hits governmentjobs.com
"""

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def test_unit() -> bool:
    from scrapers.governmentjobs import GovernmentJobsScraper

    f = GovernmentJobsScraper._passes_location_filter

    cases = [
        # (location, expected, description)
        ("Sacramento, CA", True, "plain CA city"),
        ("Sacramento, CA 95814", True, "CA with ZIP"),
        ("Lynnwood, WA", False, "WA city should be filtered"),
        ("Portland, OR", False, "OR city should be filtered"),
        ("New York, NY", False, "NY city should be filtered"),
        ("Los Angeles, CA 90012", True, "LA with ZIP"),
        ("", True, "empty location passes through"),
        ("Remote", True, "no comma — no state word found, passes through"),
        ("Remote - CA", True, "explicit CA in no-comma string"),
        ("Remote - WA", False, "explicit WA in no-comma string"),
    ]

    passed = True
    for location, expected, desc in cases:
        result = f(location)
        status = "PASS" if result == expected else "FAIL"
        if result != expected:
            passed = False
        print(f"  [{status}] {desc!r}: location={location!r} -> {result} (expected {expected})")

    return passed


def test_live(n: int = 5) -> bool:
    import config
    from scrapers.governmentjobs import GovernmentJobsScraper

    print(f"\nFetching first page of 'Software Engineer' (filter states: {config.LOCATION_FILTER_STATES})...")
    scraper = GovernmentJobsScraper()
    listings = scraper._search_keyword("Software Engineer")

    sample = listings[:n]
    print(f"\nFirst {len(sample)} listings returned:")
    for listing in sample:
        print(f"  {listing.location!r:30s}  {listing.position}")

    bad = [
        listing for listing in sample
        if listing.location and not GovernmentJobsScraper._passes_location_filter(listing.location)
    ]
    if bad:
        print(f"\nFAIL: {len(bad)} listing(s) bypassed the filter:")
        for listing in bad:
            print(f"  {listing.location!r}  {listing.full_url}")
        return False

    print(f"\nPASS: all {len(sample)} listings are CA (or have no location yet)")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Also run live scrape test")
    args = parser.parse_args()

    print("=== Unit tests ===")
    unit_ok = test_unit()

    live_ok = True
    if args.live:
        print("\n=== Live scrape test ===")
        live_ok = test_live()

    if not unit_ok or not live_ok:
        sys.exit(1)
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
