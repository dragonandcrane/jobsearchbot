"""LinkedIn scraper using the public guest jobs API.

WARNING: Like Indeed, LinkedIn may block automated access. This scraper
uses the unauthenticated guest job search endpoint which is publicly
accessible but may change without notice. Failures are logged but
won't block other scrapers.
"""

import re
import time
import httpx
from bs4 import BeautifulSoup

import config
from scrapers.base import BaseScraper, JobListing

# LinkedIn guest jobs API - returns HTML fragments, no auth needed
SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
DELAY_SECONDS = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# LinkedIn filter codes
F_REMOTE = "2"  # f_WT=2 means remote
F_FULLTIME = "F"
F_PARTTIME = "P"
F_PAST_WEEK = "r604800"  # Last 7 days


class LinkedInScraper(BaseScraper):
    name = "linkedin"

    def scrape(self, limit: int | None = None) -> list[JobListing]:
        all_listings: list[JobListing] = []
        broad_keywords = [
            "DevOps Engineer government",
            "Software Engineer government nonprofit",
            "SDET government",
            "IT Specialist government",
            "Information Security government nonprofit",
            "Site Reliability Engineer government",
            "Cloud Engineer government nonprofit",
        ]
        for keyword in broad_keywords:
            for job_type in [F_FULLTIME, F_PARTTIME]:
                listings = self._search(keyword, job_type)
                all_listings.extend(listings)
                time.sleep(DELAY_SECONDS)
        return all_listings

    def _search(self, keyword: str, job_type: str) -> list[JobListing]:
        listings: list[JobListing] = []
        start = 0
        max_results = 75  # 3 pages of 25

        while start < max_results:
            params = {
                "keywords": keyword,
                "location": "Los Angeles, California",
                "f_WT": F_REMOTE,
                "f_JT": job_type,
                "f_TPR": F_PAST_WEEK,
                "start": start,
            }
            try:
                resp = httpx.get(
                    SEARCH_URL, params=params, headers=HEADERS,
                    timeout=30, follow_redirects=True,
                )
                if resp.status_code == 429:
                    self.logger.warning("LinkedIn rate limited, backing off")
                    time.sleep(10)
                    break
                if resp.status_code != 200:
                    self.logger.warning(f"LinkedIn returned {resp.status_code}")
                    break
            except httpx.HTTPError as e:
                self.logger.warning(f"LinkedIn request failed: {e}")
                break

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select("li, .base-card, .job-search-card")
            if not cards:
                break

            found_any = False
            for card in cards:
                listing = self._parse_card(card)
                if listing:
                    listings.append(listing)
                    found_any = True

            if not found_any:
                break
            start += 25
            time.sleep(DELAY_SECONDS)

        self.logger.info(
            f"  keyword '{keyword}' type={job_type}: {len(listings)} results"
        )
        return listings

    def _parse_card(self, card) -> JobListing | None:
        # Title + link
        title_el = card.select_one(
            "h3.base-search-card__title, .base-search-card__title, "
            "a.base-card__full-link"
        )
        link_el = card.select_one(
            "a.base-card__full-link, a[href*='/jobs/view/']"
        )
        if not title_el and not link_el:
            return None

        title = title_el.get_text(strip=True) if title_el else ""
        href = ""
        if link_el:
            href = link_el.get("href", "")
            if not title:
                title = link_el.get_text(strip=True)
        # Clean tracking params from URL
        if "?" in href:
            href = href.split("?")[0]

        if not title or not href:
            return None

        # Company
        company_el = card.select_one(
            "h4.base-search-card__subtitle, .base-search-card__subtitle, "
            "a[data-tracking-control-name*='company']"
        )
        company = company_el.get_text(strip=True) if company_el else ""

        # Location
        loc_el = card.select_one(
            ".job-search-card__location, .base-search-card__metadata"
        )

        # Salary (sometimes shown)
        salary_el = card.select_one(
            ".job-search-card__salary-info, [class*='salary']"
        )
        salary = salary_el.get_text(strip=True) if salary_el else ""

        return JobListing(
            job_site="linkedin.com",
            full_url=href,
            agency_department=company,
            position=title,
            salary_range=salary,
        )


def fetch_single_listing(url: str) -> JobListing | None:
    """Fetch a single LinkedIn job posting by URL.

    Parses the unauthenticated guest job detail API. Returns None on failure.
    """
    import logging
    log = logging.getLogger("scrapers.linkedin")

    # Extract numeric job ID from URL (e.g. /jobs/view/4395174358/)
    m = re.search(r"/jobs/view/(\d+)", url)
    if not m:
        log.warning(f"Cannot extract job ID from URL: {url}")
        return None
    job_id = m.group(1)

    clean_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
    detail_url = DETAIL_URL.format(job_id=job_id)

    try:
        resp = httpx.get(detail_url, headers=HEADERS, timeout=30, follow_redirects=True)
        if resp.status_code != 200:
            log.warning(f"LinkedIn detail API returned {resp.status_code} for {detail_url}")
            return None
    except httpx.HTTPError as e:
        log.warning(f"LinkedIn detail request failed: {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    title_el = soup.select_one(
        "h2.top-card-layout__title, h1.top-card-layout__title, "
        ".topcard__title, h2[class*='title']"
    )
    title = title_el.get_text(strip=True) if title_el else ""

    company_el = soup.select_one(
        "a.topcard__org-name-link, .topcard__org-name-link, "
        ".top-card-layout__company, a[class*='company']"
    )
    company = company_el.get_text(strip=True) if company_el else ""

    location_el = soup.select_one(
        ".topcard__flavor--bullet, .top-card-layout__bullet, "
        "[class*='location']"
    )
    location = location_el.get_text(strip=True) if location_el else ""

    salary_el = soup.select_one("[class*='salary'], [class*='compensation']")
    salary = salary_el.get_text(strip=True) if salary_el else ""

    # Full description
    desc_el = soup.select_one(
        ".description__text, .show-more-less-html__markup, "
        "[class*='description']"
    )
    description = desc_el.get_text(separator="\n").strip() if desc_el else ""

    # Criteria (job type, seniority, etc.)
    criteria_items = soup.select(
        ".description__job-criteria-item, [class*='criteria-item']"
    )
    job_type = ""
    for item in criteria_items:
        label_el = item.select_one(
            ".description__job-criteria-subheader, [class*='criteria-subheader']"
        )
        value_el = item.select_one(
            ".description__job-criteria-text, [class*='criteria-text']"
        )
        if label_el and value_el:
            label = label_el.get_text(strip=True).lower()
            value = value_el.get_text(strip=True)
            if "employment type" in label:
                job_type = value

    return JobListing(
        job_site="linkedin.com",
        full_url=clean_url,
        position=title,
        agency_department=company,
        location=location,
        salary_range=salary,
        job_type=job_type,
        full_description=description,
    )


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    scraper = LinkedInScraper()
    results = scraper.safe_scrape()
    for r in results[:5]:
        print(f"{r.position} | {r.agency_department} | {r.salary_range}")
    print(f"Total: {len(results)}")
