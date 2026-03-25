# Topic: Job Search Bot

## Goal

write a simple bot in python that scrapes the web for job openings that meet my requirements:

- DevOps, SWE, SDET, IT, InfoSec, or related
- public or nonprofit sector
- 100% remote
- full time with flexible hours or part time - i am unavailable between 4-9pm
- prioritize stability and flexibility over salary and excitement

## Install

```sh
git clone https://github.com/dragonandcrane/jobsearchbot.git
```

## Usage

```sh
python main.py
```

## store fields

- status (initially blank, never override)
- job site (eg governmentjobs.com)
- full job url
- agency/department
- position
- salary range
- qualification
- education requirement
- org-generic boilerplate*
- role-specific description (block of text)
- keywords: SWE tools and technologies (eg "git", "kubernetes")
- keywords: non-SWE industry-wide (eg "powerpoint", "project management")
- keywords: domain- or vertical-specific ("2-sided accounting", "HIPAA compliance")
- listing contact name
- listing contact phone
- listing contact email
- first scraped date
- last scraped date
- last modified date

### Note

- to determine which part of role description is boilerplate, check other listings (including non-technical ones) from the same role

## Scheduling

the search should run automatically daily at 9am and 6pm

since `main.py` will be rerun repeatedly it should be idempotent.
This also means after updating the script to add or enrich columns, it can just be rerun.

## Listings Summary

The summary output of the search should update a CSV file:
listings\listings.csv

## Listing Details

For each listing, create a slug based on the url.
Create a dir based on the slug under the corresponding listings source dir.

Model after below example created by hand:

src: <https://www.governmentjobs.com/jobs/60587-1/cloud-engineer>
dst:

```text
/listings
    /governmentjobs.com
        /listings/governmentjobs.com/60587-1-cloud-engineer
            listing.md
```

The `listing.md` file should contain the listing text with markdown formatting, focusing on headers and bullets.

Since each listing is formatted differently, use simple heuristics eg:

- infer bullet lists from series of short sentence fragments even if source text does not use bullets
- infer section header from caps, bold, and/or line preceding bullets
