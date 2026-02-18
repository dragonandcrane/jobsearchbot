"""GovernmentJobs.com scraper using requests + BeautifulSoup."""

import time
import httpx
from bs4 import BeautifulSoup

import config
from scrapers.base import BaseScraper, JobListing

BASE_URL = "https://www.governmentjobs.com/careers/home/index"
SEARCH_URL = "https://www.governmentjobs.com/jobs"
DELAY_SECONDS = 1.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class GovernmentJobsScraper(BaseScraper):
    name = "governmentjobs"

    def scrape(self) -> list[JobListing]:
        all_listings: list[JobListing] = []
        for keyword in config.SEARCH_KEYWORDS:
            listings = self._search_keyword(keyword)
            all_listings.extend(listings)
            time.sleep(DELAY_SECONDS)
        return all_listings

    def _search_keyword(self, keyword: str) -> list[JobListing]:
        listings: list[JobListing] = []
        page = 1
        max_pages = 5
        while page <= max_pages:
            params = {
                "keyword": keyword,
                "isRemote": "true",
                "page": page,
            }
            try:
                resp = httpx.get(
                    SEARCH_URL, params=params, headers=HEADERS,
                    timeout=30, follow_redirects=True,
                )
                resp.raise_for_status()
            except httpx.HTTPError as e:
                self.logger.warning(f"  keyword '{keyword}' page {page}: {e}")
                break

            soup = BeautifulSoup(resp.text, "lxml")
            job_cards = soup.select("li.job-item[data-job-id]")
            if not job_cards:
                break

            for card in job_cards:
                listing = self._parse_card(card)
                if listing:
                    listings.append(listing)

            # Stop if fewer than a full page of results (no more pages)
            if len(job_cards) < 10:
                break
            page += 1
            time.sleep(DELAY_SECONDS)

        self.logger.info(f"  keyword '{keyword}': {len(listings)} results")
        return listings

    def _parse_card(self, card) -> JobListing | None:
        # Title and link - use the specific class from the actual site
        link_el = card.select_one("a.job-details-link")
        if not link_el:
            link_el = card.select_one("a[href]")
        if not link_el:
            return None
        href = link_el.get("href", "")
        if href and not href.startswith("http"):
            href = f"https://www.governmentjobs.com{href}"
        title = link_el.get_text(strip=True)

        # Agency/organization
        agency_el = card.select_one(".job-organization, .primaryInfo.job-organization")
        agency = agency_el.get_text(strip=True) if agency_el else ""

        # Salary and schedule info from the primaryInfo divs
        salary = ""
        info_divs = card.select("div.primaryInfo")
        for div in info_divs:
            text = div.get_text(strip=True)
            if "$" in text or "hourly" in text.lower() or "annually" in text.lower():
                salary = text
                break

        return JobListing(
            job_site="governmentjobs.com",
            full_url=href,
            agency_department=agency,
            position=title,
            salary_range=salary,
        )

    def enrich_listing(self, listing: JobListing) -> JobListing:
        """Fetch the full listing page to get description, quals, education."""
        if not listing.full_url:
            return listing
        try:
            resp = httpx.get(
                listing.full_url, headers=HEADERS,
                timeout=30, follow_redirects=True,
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            return listing

        soup = BeautifulSoup(resp.text, "lxml")

        # Description
        desc_el = soup.select_one(
            "#TextContent, .description, .job-description, "
            "[class*='description'], [class*='duties']"
        )
        if desc_el:
            listing.full_description = desc_el.get_text(separator="\n").strip()

        # Qualifications
        qual_el = soup.select_one(
            "[class*='qualification'], [class*='requirement'], "
            "[class*='minimum']"
        )
        if qual_el:
            listing.qualification = qual_el.get_text(separator="\n").strip()

        # Education
        edu_el = soup.select_one("[class*='education']")
        if edu_el:
            listing.education_requirement = edu_el.get_text(separator="\n").strip()

        # Salary (more detailed on detail page)
        if not listing.salary_range:
            salary_el = soup.select_one("[class*='salary'], [class*='pay']")
            if salary_el:
                listing.salary_range = salary_el.get_text(strip=True)

        time.sleep(DELAY_SECONDS)
        return listing


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    scraper = GovernmentJobsScraper()
    results = scraper.safe_scrape()
    for r in results[:5]:
        print(f"{r.position} | {r.agency_department} | {r.salary_range}")
    print(f"Total: {len(results)}")
