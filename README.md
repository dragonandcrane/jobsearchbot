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

python main.py

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

## Output

the output of the search should update a CSV file stored on my OneDrive to ensure sync across my devices:
C:\Users\drago\OneDrive - Los Angeles Community College District\Personal\career\job search 2026\listings.csv
