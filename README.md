# LinkedIn Profile Batch Scraper Toolkit

Extract LinkedIn profile URLs and profile details into a Google Sheet using browser automation.

**Two scripts:**
1. **Profile URL Collector** — Gathers LinkedIn profile links based on your search.
2. **Profile Detail Extractor** — Extracts names, skills, education, experience, and more from each profile.

## Application Overview

**Collector:** Mimics human browsing to collect profile URLs via search keywords and location.

**Extractor:** Visits each profile from a list, scrapes attributes (Name, Headline, Skills, About, Education, Experience), and sends to Google Sheets.

Both scripts use browser automation (undetected_chromedriver) and Google Sheets API integration.

## Installation

### 1. Clone or Download

```bash
# WSL/zsh/Terminal:
git clone https://github.com/cazrot335/final_year_project.git
cd final_year_project
```

Or download the scripts and place them in a dedicated folder.

### 2. Python Environment

```bash
# (Recommended) Use virtualenv
python3 -m venv venv
source venv/bin/activate    # For WSL/zsh/Terminal
venv\Scripts\activate       # For cmd (Windows)
```

### 3. Dependencies

```bash
pip install undetected-chromedriver selenium google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 4. Chrome/Chromedriver

Install Google Chrome on your system.

Update with:

**Ubuntu/WSL:**
```bash
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get -f install
```

**Windows/macOS:** Download from [Google Chrome](https://www.google.com/chrome/).

## Credential Setup

### A. LinkedIn Login

Create `accounts.json`:

```json
[
  {
    "site": "linkedin",
    "email": "your_email_here@gmail.com",
    "password": "YOUR_LINKEDIN_PASSWORD",
    "registered": true,
    "created_at": "2025-10-21T22:00:00"
  }
]
```

Put it in the project folder.

### B. Google Sheets API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2. Enable **Google Sheets API** for your project.
3. Create **Credentials → Service Account → Create Key (JSON)**.
4. Download as `service_account.json` to your project folder.
5. Share your Google Sheet with the service account's email (found in the JSON as `client_email`)—must have **Editor access**.

### How to Get Your Spreadsheet ID

1. Open your sheet.
2. Look for: `https://docs.google.com/spreadsheets/d/<THIS_PART>/edit#gid=0`
3. Copy `<THIS_PART>`; for example:

```python
SPREADSHEET_ID = "1gtwXOp09GsNxDAWMnPy_WobQ6YXU2qschF0-FFYDwzE"
```

Insert in both scripts.

## Usage

### 1. Run Profile URL Collector

Collect LinkedIn profile URLs based on your keywords and location!

```bash
python3 scrapper.py
```

Or (Windows/cmd):
```cmd
python scrapper.py
```

- Follow prompts (Skill, Location, Max links).
- Creates `linkedin_profiles.txt` with one URL per line.

### 2. Run Profile Detail Extractor

Extract profile details and push them to your Google Sheet.

```bash
python3 extracter.py
```

Or (Windows/cmd):
```cmd
python extracter.py
```

The script reads `linkedin_profiles.txt`, logs into LinkedIn, visits each URL, scrapes info, and sends all details (Name, Headline, Location, Skills, About, Education, Experience, Profile URL) to your sheet.

## Notes for All Shells

- **WSL/bash/zsh:** Use `python3 ...` with forward slashes and Unix-style paths.
- **Windows CMD:** Use `python ...` with backslashes if needed.
- **macOS Terminal/zsh:** Same usage as WSL.

Ensure your Chrome version matches Chromedriver used by `undetected_chromedriver` library! If you have a new Chrome, run:

```bash
pip install --upgrade undetected-chromedriver
```

## Troubleshooting

- If you get login or cookies errors, delete the `.pkl` file in `cookies/` directory.
- For "permission" errors from Sheets API, check you properly shared the Sheet with your service account.
- For "SessionNotCreatedException", upgrade Google Chrome or undetected-chromedriver.
- Scraper selectors may need updating if LinkedIn changes its HTML. Inspect profile pages and update `CSS_SELECTOR` or `XPATH` in your script as needed.

## Security & Compliance

⚠️ **Important:** Automated scraping can violate LinkedIn's Terms of Service. Use responsibly and in limited, research-focused volumes.

## Project Structure

```
linkedin-batch-scraper/
├── scrapper.py              # Profile URL collector
├── extracter.py             # Profile detail extractor
├── accounts.json            # LinkedIn credentials (not in repo)
├── service_account.json     # Google service account (not in repo)
├── linkedin_profiles.txt    # Generated profile URLs
├── cookies/                 # Browser session storage
└── README.md               # This file
```

## Files Not Tracked in Git

- `accounts.json` - Contains LinkedIn login credentials
- `service_account.json` - Contains Google API credentials
- `cookies/` - Browser session data
- `linkedin_profiles.txt` - Generated profile URLs
