import os
import time
import random
import json
import csv
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# Selenium + webdriver-manager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Apify
from apify_client import ApifyClient

# Resume screening
from resume_screening import resume_bp

load_dotenv()

# Configuration
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "e1xYKjtHLG2Js5YdC")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "linkedin_profiles")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_JSON = os.path.join(DATA_DIR, "linkedin_profiles_detailed.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "linkedin_profiles_detailed.csv")

app = Flask(__name__)
CORS(app)
app.register_blueprint(resume_bp)

# --- Helper: scrape Google search results for LinkedIn profiles ---
def scrape_google_profiles(keyword, location, pages=3, with_email=True):
    query = f"site:linkedin.com/in {keyword} {location}"
    if with_email:
        query += " gmail.com"
    query = query.strip().replace(' ', '+')
    base_url = f"https://www.google.com/search?q={query}&start="

    options = Options()
    options.headless = True
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("start-maximized")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119 Safari/537.36"
    )

    # Use webdriver-manager to download driver if needed
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # hide webdriver
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
    except Exception:
        pass

    results = []

    try:
        for page in range(max(1, pages)):
            start = page * 10
            url = f"{base_url}{start}"
            driver.get(url)
            time.sleep(random.uniform(2, 4))

            # Google result container selector can vary
            search_results = driver.find_elements(By.CSS_SELECTOR, 'div.MjjYud')
            if not search_results:
                # fallback to generic search result selector
                search_results = driver.find_elements(By.CSS_SELECTOR, 'div.g')

            for result in search_results:
                try:
                    try:
                        link_el = result.find_element(By.CSS_SELECTOR, 'a[href*="linkedin.com"]')
                    except Exception:
                        link_el = result.find_element(By.TAG_NAME, 'a')

                    try:
                        title_el = result.find_element(By.TAG_NAME, 'h3')
                    except Exception:
                        title_el = None

                    try:
                        snippet_el = result.find_element(By.CSS_SELECTOR, '.VwiC3b')
                    except Exception:
                        snippet_el = None

                    href = link_el.get_attribute('href') if link_el else ''
                    title = title_el.text.strip() if title_el else ''
                    snippet = snippet_el.text.strip() if snippet_el else ''

                    title_parts = title.split(' - ')
                    name = title_parts[0].strip() if title_parts else ''
                    designation = title_parts[1].strip() if len(title_parts) > 1 else ''
                    company = title_parts[2].strip() if len(title_parts) > 2 else ''

                    try:
                        info_el = result.find_element(By.CSS_SELECTOR, '.YrbPuc')
                        info_line = info_el.text.strip()
                    except Exception:
                        info_line = ''

                    info_parts = info_line.split(' · ')
                    if not designation and len(info_parts) > 1:
                        designation = info_parts[1].strip()
                    if not company and len(info_parts) > 2:
                        company = info_parts[2].strip()
                    loc = info_parts[0].strip() if len(info_parts) > 0 else ''

                    if 'linkedin.com/in' in href:
                        results.append({
                            "name": name,
                            "designation": designation,
                            "company": company,
                            "location": loc,
                            "profile_url": href,
                            "snippet": snippet,
                        })
                except Exception:
                    continue

            time.sleep(random.uniform(1.5, 2.5))
    finally:
        driver.quit()

    return results


# --- Helper: call Apify actor for detailed profile scraping ---
def fetch_detailed_profiles(basic_profiles):
    if not APIFY_API_TOKEN:
        return [None] * len(basic_profiles)

    client = ApifyClient(APIFY_API_TOKEN)
    detailed = []
    for profile in basic_profiles:
        url = profile.get('profile_url')
        try:
            run = client.actor(APIFY_ACTOR_ID).call(run_input={"url": url})
            items = list(client.dataset(run['defaultDatasetId']).iterate_items())
            detailed.append(items[0] if items else None)
        except Exception:
            detailed.append(None)
        time.sleep(1)
    return detailed


# --- Helper: merge data and save ---
def merge_profile_data(basic_profiles, detailed_profiles):
    merged = []
    for basic, detailed in zip(basic_profiles, detailed_profiles):
        merged_item = {
            "name": basic.get('name', ''),
            "basic_designation": basic.get('designation', ''),
            "basic_company": basic.get('company', ''),
            "basic_location": basic.get('location', ''),
            "profile_url": basic.get('profile_url', ''),
            "snippet": basic.get('snippet', ''),
            "detailed_headline": detailed.get('headline', '') if detailed else '',
            "detailed_about": detailed.get('about', '') if detailed else '',
            "detailed_experience": detailed.get('experience', []) if detailed else [],
            "detailed_education": detailed.get('education', []) if detailed else [],
            "detailed_skills": detailed.get('skills', []) if detailed else [],
            "detailed_connections": detailed.get('connections', '') if detailed else '',
            "raw_data": detailed if detailed else None,
        }
        merged.append(merged_item)
    return merged


def save_to_json(profiles, filename=OUTPUT_JSON):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)


def save_to_csv(profiles, filename=OUTPUT_CSV):
    if not profiles:
        return
    profiles_for_csv = []
    for p in profiles:
        p_copy = p.copy()
        p_copy.pop('raw_data', None)
        # flatten lists to strings for CSV
        for k, v in p_copy.items():
            if isinstance(v, list):
                p_copy[k] = json.dumps(v, ensure_ascii=False)
        profiles_for_csv.append(p_copy)

    keys = list(profiles_for_csv[0].keys())
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(profiles_for_csv)


# --- Flask endpoints ---
@app.route('/')
def home():
    return 'Server is running. Use /scrape-linkedin and /profiles/refresh.'


@app.route('/scrape-linkedin', methods=['GET'])
def api_scrape_linkedin():
    keyword = request.args.get('keyword')
    location = request.args.get('location')
    with_email = request.args.get('with_email', '1') == '1'
    pages = int(request.args.get('pages', 1))

    if not keyword or not location:
        return jsonify({'error': 'keyword and location required'}), 400

    profiles = scrape_google_profiles(keyword, location, pages=pages, with_email=with_email)
    return jsonify({'saved': len(profiles), 'profiles': profiles})


@app.route('/profiles/refresh', methods=['GET'])
def api_refresh_profiles():
    """Trigger full flow: scrape google, call Apify, merge, save, return merged JSON"""
    keyword = request.args.get('keyword')
    location = request.args.get('location')
    with_email = request.args.get('with_email', '1') == '1'
    pages = int(request.args.get('pages', 1))

    if not keyword or not location:
        return jsonify({'error': 'keyword and location required'}), 400

    basic = scrape_google_profiles(keyword, location, pages=pages, with_email=with_email)
    detailed = fetch_detailed_profiles(basic)
    merged = merge_profile_data(basic, detailed)

    save_to_csv(merged)
    save_to_json(merged)

    return jsonify({'saved': len(merged), 'profiles': merged})


@app.route('/profiles', methods=['GET'])
def api_get_profiles():
    if not os.path.exists(OUTPUT_JSON):
        return jsonify({'error': 'no data found; run /profiles/refresh first'}), 404
    with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
