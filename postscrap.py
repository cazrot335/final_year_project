import os
import time
import random
from stage1 import perform_biometric_screening
from stage2 import screen_candidate_fit
from datetime import datetime
import json
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

# # Resume screening
# from resume_screening import resume_bp

load_dotenv()

# Configuration
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "pratikdani/linkedin-people-profile-scraper")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "linkedin_profiles")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_JSON = os.path.join(DATA_DIR, "linkedin_profiles_detailed.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "linkedin_profiles_detailed.csv")

app = Flask(__name__)
CORS(app)


# commented
# app.register_blueprint(resume_bp)

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

def api_scrape_single_profile():
    profile_url = request.args.get('url')
    
    if not profile_url:
        return jsonify({'error': 'LinkedIn URL is required'}), 400

    if not APIFY_API_TOKEN:
        return jsonify({'error': 'Apify API Token not configured'}), 500

    print(f"Targeting deep extraction for: {profile_url}")
    
    try:
        client = ApifyClient(APIFY_API_TOKEN)
        # Call the actor for the single specific URL
        run = client.actor(APIFY_ACTOR_ID).call(run_input={"url": profile_url})
        
        # Fetch the results from the dataset
        items = list(client.dataset(run['defaultDatasetId']).iterate_items())
        
        if not items:
            return jsonify({'error': 'No data found for this profile'}), 404
            
        detailed_data = items[0]
        
        # Return a structured response similar to your merge logic
        return jsonify({
            "status": "success",
            "data": {
                "name": detailed_data.get('fullName', ''),
                "headline": detailed_data.get('headline', ''),
                "about": detailed_data.get('about', ''),
                "experience": detailed_data.get('experience', []),
                "education": detailed_data.get('education', []),
                "skills": detailed_data.get('skills', []),
                "contact_info": detailed_data.get('contactInfo', {}),
                "raw": detailed_data
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    





# --- Flask endpoints ---
@app.route('/')
def home():
    return 'Server is running. Use /scrape-linkedin and /profiles/refresh.'

#scraps additional details  with apify actor 
@app.route('/scrape-profile', methods=['GET'])
def api_scrape_single_profile():
    profile_url = request.args.get('url')
    
    if not profile_url:
        return jsonify({'error': 'LinkedIn URL is required'}), 400
    
    try:
        # Initialize the ApifyClient
        client = ApifyClient(APIFY_API_TOKEN)
        
        # Prepare the Actor input
        run_input = {"url": profile_url}
        
        # Run the Actor and wait for it to finish
        run = client.actor(APIFY_ACTOR_ID).call(run_input=run_input)
        
        # Fetch results from the dataset
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if not items:
            return jsonify({'status': 'success', 'data': None}), 200
        
        return jsonify({
            'status': 'success',
            'data': items[0]  # Return first item
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    
#scraps linkedin profile links through search engine dorking 
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


#biometric screening using qwen model 
@app.route('/extract-relevant-data', methods=['POST'])
def api_intelligent_extraction():
    raw_input = request.get_json()
    if not raw_input:
        return jsonify({"error": "No data received"}), 400

    ai_result_str = perform_biometric_screening(raw_input)
    
    try:
        # ai_result_str is now cleaned by the backtick stripper in stage1.py
        data = json.loads(ai_result_str)
        
        return jsonify({
            "status": "success",
            "biometric_score": data.get("biometric_score", 0),
            "profile_analysis": {
                "identity": {
                    "name": data.get("name"),
                    "profile_id": data.get("profile_id"),
                    "address": data.get("address")
                },
                "contact": data.get("biometrics", {}),
                "professional": {
                    "skills": data.get("skills", []),
                    "experience": data.get("experience", []),
                    "education": data.get("education", [])
                }
            },
            "recruiter_notes": {
                "missing_static_fields": data.get("missing_fields", []),
                "ai_feedback": data.get("feedback")
            }
        })
    except Exception as e:
        # In case the model still sends bad formatting, we show it here to debug
        return jsonify({
            "error": "JSON Parsing Failed",
            "reason": str(e),
            "raw_ai_output": ai_result_str 
        }), 500
    
#ai screening against JD using qwen model
@app.route('/stage2-screen', methods=['POST'])
def api_stage2_screen():

    jd_text = request.args.get("jd")
    profile_data = request.get_json(silent=True)

    if not jd_text or not profile_data:
        return jsonify({"error": "Missing input data"}), 400

    raw_ai_output = screen_candidate_fit(profile_data, jd_text)

    try:
        screening_result = json.loads(raw_ai_output.strip())

        return jsonify({
            "status": "success",
            "candidate": profile_data.get("name", "Unknown"),
            "screening_report": screening_result
        })

    except Exception as e:
        return jsonify({
            "error": "Final JSON parsing failed",
            "reason": str(e),
            "raw_ai_content": raw_ai_output
        }), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)