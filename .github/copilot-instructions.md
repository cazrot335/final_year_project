<!-- Copilot instructions for working on the LinkedIn batch scraper toolkit -->

# What this repository is and the big picture

This repo contains two small CLI Python scripts that automate LinkedIn browsing and data extraction:

- `scrapper.py` — interactive Profile URL collector. It logs into LinkedIn (via `accounts.json`), runs searches, scrolls and clicks "Show more"/Next to collect profile URLs and writes them to `linkedin_profiles.txt`.
- `extracter.py` — Profile Detail extractor. It reads `linkedin_profiles.txt`, visits each profile, expands sections (see more), scrapes fields (name, headline, skills, education, experience) and appends rows to a Google Sheet using a service account JSON (`service_account.json`).

Both use `undetected_chromedriver` + Selenium for browser automation and rely on a local cookies directory (`cookies/`) to persist sessions. The README contains setup and credential steps — respect sensitive files that are intentionally not tracked.

# Key patterns and conventions for changes

- Human-like interaction: both scripts implement `human_typing`, randomized delays, `realistic_scroll_behavior` or `mimic_human_browsing`, and occasional mouse movement. Preserve and extend this pattern when modifying navigation or adding new interactions.
- Cookie-based session reuse: `load_cookies` / `save_cookies` use pickled cookie files named `<Site>_<email>.pkl` in `cookies/`. Keep this naming scheme and update removal logic if adding cleanup steps.
- Minimal configuration via top-of-file constants: e.g. `INPUT_FILE`, `OUTPUT_FILE`, `SPREADSHEET_ID`, `MAX_PROFILES`. Prefer adding new flags as constants near the top of the relevant script.
- Selectors are fragile: the code uses multiple CSS/XPath fallbacks (see `scrape_profile` and skills/about selectors). When updating selectors, add the specific example selector and the fallback used in the file.

# Developer workflows & commands

- Install dependencies (see README): undetected-chromedriver, selenium, google-api-python-client, google-auth-\*.
- Run collector (interactive):
  - Windows (cmd/Powershell): `python scrapper.py`
  - WSL/macOS: `python3 scrapper.py`
- Run extractor (non-interactive): `python extracter.py` (ensure `linkedin_profiles.txt`, `accounts.json`, `service_account.json` and `SPREADSHEET_ID` are present).
- Troubleshooting tips to include in PRs: if login fails, check cookies in `cookies/` for stale pickles; if Sheets push fails, verify `service_account.json` and that the sheet is shared with the service account email.

# Integration points & external dependencies

- LinkedIn site — scripts assume HTML structure used by LinkedIn (selectors in code). Any LinkedIn layout change requires selector updates in the specific script.
- Google Sheets API — `push_profiles_to_sheets` uses `googleapiclient` & service account credentials. The spreadsheet ID is defined in `extracter.py` as `SPREADSHEET_ID`.
- Browser automation: `undetected_chromedriver` is used to reduce detection; code sets `options.binary_location = "/usr/bin/google-chrome"` (Linux default). On Windows, ensure `options.binary_location` or PATH is correct (Windows-specific adaptations may be needed).

# What to add to PR descriptions when changing scraping logic

- Mention which selectors you changed and paste one example profile URL used to test locally.
- Show before/after extraction sample output for 1 profile (JSON) and include the corresponding CSS/XPath used.
- If you modify delays or interaction behavior, run a short local extraction (1–3 profiles) and report runtime and any detection issues observed.

# Small, concrete examples to follow

- Adding a new fallback selector for skills: include both the primary selector and a fallback in the same function (see `extracter.py::scrape_profile` for examples using CSS then XPath fallback).
- When changing cookie logic: maintain `cookies/<Site>_<email>.pkl` naming and ensure `load_cookies` converts float expiry to int (the existing code does this — preserve it).

# Privacy & safety notes (copy from README)

- This tool automates scraping LinkedIn and requires credentials. Do not commit `accounts.json` or `service_account.json` to the repo. Respect LinkedIn's Terms of Service and use this for limited, research-focused work.

# Where to look in the code

- `scrapper.py` — URL collection, advanced scrolling behavior, search variations.
- `extracter.py` — profile scraping, selector fallbacks, Google Sheets push logic.
- `scrapper.md` / `README.md` — setup and usage instructions (repeat of README; keep these in sync when updating scripts).

# If anything is unclear

Please point to a line or function (e.g. `extracter.py::scrape_profile`) and state what you want the agent to change or add. I will update these instructions accordingly.
