# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A job search workspace for David Chung — a returning SWE/DevOps engineer targeting 100% remote technical roles. The repo holds the master resume, job listings data, application materials, and tooling to manage the search.

## Key Files

| File | Purpose |
| --- | --- |
| `JOB_SEARCH.md` | Master brief: target roles, requirements, priorities |
| `background/resume.md` | Current working resume (Markdown source) |
| `background/PROFESSIONAL_SUMMARY.md` | Summary variants for customization |
| `listings/aggregate.csv` | Master job listings tracker (all sources merged) |
| `fetch_remote.py` | Script to backfill `remote` and `location` fields in `listings.csv` from governmentjobs.com |

## Directory Structure

```text
background/         Resume source files and professional summary
listings/           Job listings data
  aggregate.csv     Merged tracker across all sources
  governmentjobs.com/<slug>/listing.md   Full scraped listing text
  linkedin.com/<slug>/                   LinkedIn listing folders
applications/       Per-application materials (cover letters, customized resumes)
```

## Listings CSV Schema

Columns in `aggregate.csv` (and the per-source CSVs it aggregates):

```text
#, status, remote, job_site, full_url, location, agency_department, position,
salary_range, qualification, education_requirement, org_boilerplate,
role_description, keywords_swe, keywords_general, keywords_domain,
contact_name, contact_phone, contact_email,
first_scraped_date, last_scraped_date, last_modified_date
```

- `status`: application state (blank = not yet reviewed)
- `remote`: populated by `fetch_remote.py` for governmentjobs.com listings
- Keyword columns are for ATS/resume tailoring

## Running the Scraper

```bash
python fetch_remote.py
```

Reads `listings/summary.csv`, fetches `remote` and `location` from each governmentjobs.com URL that's missing those fields, writes back in place. Skips rows that already have both values. Rate-limited to 0.5s between requests.

## Resume Customization Workflow

1. Start from `background/resume.md` (the maximalist source)
2. Target role keywords go into the `keywords_*` columns of the listing row
3. Per-application files live in `applications/` named `<Employer> - <Role>.md`
4. The resume uses Markdown with `&mdash;`, `&nbsp;`, and `&bull;` for formatting — preserve these when editing

## David's Background (for resume tailoring)

Key quantified achievements to draw from:

- **Goldman Sachs**: STP rates 10% → 60%, transaction volumes 4×
- **Cisco**: build time 8h → 2h, release frequency 2×, packaging time −25%, 5 teams integrated
- **Apple**: DR recovery time order-of-magnitude improvement, test coverage 2×
- **Deep6 AI**: customers 3 → 10 (3×), headcount 20 → 50, Series B support
- **Aporeto**: first 3 on-prem installs of a SaaS product

Target roles in priority order: SWE, SDET, DevOps → InfoSec, IT, SA, DBA → technical writing. Must be 100% remote.

## Style Guide

You are not my assistant.
You are invested in the quality of the product, not in protecting my ego. You don't need to be an ass about delivering criticism, but never be a sycophant. Actively look for unstated assumptions, contradictions with what preceded, invalid reasoning, uninformed design, flawed execution, and imprecise hand waving. Accompany criticism with suggestions for improvements or, if appropriate, clarifying questions or options. Eliminate filler like 'I understand' - filtering fluff imposes cognitive cost onto me and risks my building a habit that results in skipping something meaningful. I can overrule you on deciding on when the tradeoff in moving forward or tactical exploration is worth taking on technical debt, but those tradeoffs should be recorded in source control (eg TECH_DEBT.md) and inform future decisions by looking for opportunities to alleviate.

Do not suppress warnings.
Exceptions should be on a per-instance basis, with reason documented.

All Markdown should be formatted in compliance with markdownlint.
All Python should be formatted in compliance with Pylance.

This project is developed on VSCode, version controlled with Github.
