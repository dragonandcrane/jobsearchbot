"""Indeed.com scraper for government/nonprofit remote jobs.

WARNING: Indeed aggressively blocks automated scraping. This scraper is
inherently fragile and may need periodic maintenance when Indeed changes
their markup or adds new anti-bot measures. Failures are logged but
won't block other scrapers.
"""

import time
import httpx
from bs4 import BeautifulSoup

import config
from scrapers.base import BaseScraper, JobListing

SEARCH_URL = "https://www.indeed.com/jobs"
DELAY_SECONDS = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
}


class IndeedScraper(BaseScraper):
    name = "indeed"

    def scrape(self) -> list[JobListing]:
        all_listings: list[JobListing] = []
        # Use a few broad keywords to avoid rate-limiting with too many queries
        broad_keywords = [
            "DevOps remote government",
            "Software Engineer remote government nonprofit",
            "SDET remote government",
            "IT Specialist remote government",
            "Information Security remote government nonprofit",
            "Systems Administrator remote government",
        ]
        for keyword in broad_keywords:
            listings = self._search_keyword(keyword)
            all_listings.extend(listings)
            time.sleep(DELAY_SECONDS)
        return all_listings

    def _search_keyword(self, keyword: str) -> list[JobListing]:
        listings: list[JobListing] = []
        start = 0
        max_pages = 3  # Limit pages to avoid getting blocked

        while start < max_pages * 10:
            params = {
                "q": keyword,
                "l": "",  # No location, remote filter below
                "sc": "0kf:attr(DSQF7)jt(fulltime,parttime);",  # Remote filter
                "start": start,
                "fromage": "7",  # Last 7 days
            }
            try:
                resp = httpx.get(
                    SEARCH_URL, params=params, headers=HEADERS,
                    timeout=30, follow_redirects=True,
                )
                if resp.status_code == 403:
                    self.logger.warning("Indeed returned 403 - likely blocked")
                    break
                resp.raise_for_status()
            except httpx.HTTPError as e:
                self.logger.warning(f"Indeed search failed: {e}")
                break

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select(
                "div.job_seen_beacon, .jobsearch-ResultsList > li, "
                ".result, div[data-jk]"
            )
            if not cards:
                break

            for card in cards:
                listing = self._parse_card(card)
                if listing:
                    listings.append(listing)

            # Check for next page
            nav = soup.select_one("a[aria-label='Next']")
            if not nav:
                break
            start += 10
            time.sleep(DELAY_SECONDS)

        self.logger.info(f"  keyword '{keyword}': {len(listings)} results")
        return listings

    def _parse_card(self, card) -> JobListing | None:
        # Title and link
        title_el = card.select_one("h2 a, a.jcs-JobTitle, a[data-jk]")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        if href and not href.startswith("http"):
            href = f"https://www.indeed.com{href}"

        # Company/agency
        company_el = card.select_one(
            "span.companyName, span[data-testid='company-name'], "
            ".company, [class*='company']"
        )
        company = company_el.get_text(strip=True) if company_el else ""

        # Salary
        salary_el = card.select_one(
            "div.salary-snippet-container, .salaryText, "
            "[class*='salary'], div[data-testid='attribute_snippet_testid']"
        )
        salary = ""
        if salary_el:
            text = salary_el.get_text(strip=True)
            if "$" in text or "year" in text.lower() or "hour" in text.lower():
                salary = text

        # Snippet (brief description)
        snippet_el = card.select_one(
            ".job-snippet, div[class*='snippet'], .summary"
        )
        snippet = snippet_el.get_text(separator="\n").strip() if snippet_el else ""

        return JobListing(
            job_site="indeed.com",
            full_url=href,
            agency_department=company,
            position=title,
            salary_range=salary,
            full_description=snippet,
        )


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    scraper = IndeedScraper()
    results = scraper.safe_scrape()
    for r in results[:5]:
        print(f"{r.position} | {r.agency_department} | {r.salary_range}")
    print(f"Total: {len(results)}")
