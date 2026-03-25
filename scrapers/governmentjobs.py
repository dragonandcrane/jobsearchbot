"""GovernmentJobs.com scraper using requests + BeautifulSoup."""

import time
import httpx
from bs4 import BeautifulSoup

import config
from scrapers.base import BaseScraper, JobListing

_US_STATE_ABBREVS = frozenset({
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
})

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

    @staticmethod
    def _passes_location_filter(location: str) -> bool:
        """Return True if location is in LOCATION_FILTER_STATES, or if unknown.

        Parses "City, ST" and "City, ST XXXXX" formats.
        Empty location passes through (may be backfilled later).
        """
        if not config.LOCATION_FILTER_STATES:
            return True
        if not location:
            return True
        allowed = {s.upper() for s in config.LOCATION_FILTER_STATES}
        if "," in location:
            # "Sacramento, CA" or "Sacramento, CA 95814" -> "CA"
            state_word = location.rsplit(",", 1)[1].strip().split()[0].upper()
            return state_word in allowed
        # No comma: only block if we can positively identify a non-allowed US state.
        # "Remote" alone has no state info and should pass through.
        words = {w.upper().rstrip(".,;") for w in location.split()}
        state_words = words & _US_STATE_ABBREVS
        if not state_words:
            return True  # No recognisable state; can't filter
        return bool(state_words & allowed)

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

        location_el = card.select_one(".job-location")
        location = location_el.get_text(strip=True) if location_el else ""

        if not self._passes_location_filter(location):
            return None

        return JobListing(
            job_site="governmentjobs.com",
            full_url=href,
            location=location,
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

        # Location
        if not listing.location:
            loc_el = soup.select_one(".job-location")
            if loc_el:
                listing.location = loc_el.get_text(strip=True)

        # Salary (more detailed on detail page)
        if not listing.salary_range:
            salary_el = soup.select_one("[class*='salary'], [class*='pay']")
            if salary_el:
                listing.salary_range = salary_el.get_text(strip=True)

        time.sleep(DELAY_SECONDS)
        return listing


def fetch_location_remote(url: str) -> tuple[str, str]:
    """Fetch a governmentjobs.com detail page and return (location, remote).

    Returns empty strings on any error or if the fields are not found.
    """
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError:
        return "", ""

    soup = BeautifulSoup(resp.text, "lxml")
    location = ""
    remote = ""

    for item in soup.select("div.job-detail-item"):
        label_el = item.select_one("span.job-detail-label")
        value_el = item.select_one("span.job-detail-value")
        if not label_el or not value_el:
            continue
        label = label_el.get_text(strip=True).lower()
        value = value_el.get_text(strip=True)
        if "location" in label and not location:
            location = value
        elif "remote" in label and not remote:
            remote = value

    return location, remote


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    scraper = GovernmentJobsScraper()
    results = scraper.safe_scrape()
    for r in results[:5]:
        print(f"{r.position} | {r.agency_department} | {r.salary_range}")
    print(f"Total: {len(results)}")
