import os
import json
import pickle
import random
import time
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

INPUT_FILE = "linkedin_profiles.txt"
CREDENTIALS_FILE = "accounts.json"
COOKIES_DIR = "cookies/"
SHEET_CREDS_FILE = "service_account.json"
SPREADSHEET_ID = "1gtwXOp09GsNxDAWMnPy_WobQ6YXU2qschF0-FFYDwzE"  # FILL IN YOUR GOOGLE SHEET ID!
MAX_PROFILES = 50  # Change to desired batch size

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def load_accounts():
    if not os.path.exists(CREDENTIALS_FILE):
        return []
    with open(CREDENTIALS_FILE, "r") as f:
        return json.load(f)

def save_cookies(driver, filename):
    ensure_dir(COOKIES_DIR)
    with open(os.path.join(COOKIES_DIR, filename), "wb") as f:
        pickle.dump(driver.get_cookies(), f)

def load_cookies(driver, filename, url):
    cookie_path = os.path.join(COOKIES_DIR, filename)
    if os.path.exists(cookie_path):
        driver.get(url)
        try:
            with open(cookie_path, 'rb') as f:
                cookies = pickle.load(f)
        except Exception as e:
            print(f"Failed to load cookies: {e}")
            return False
        for cookie in cookies:
            if isinstance(cookie.get("expiry", None), float):
                cookie["expiry"] = int(cookie["expiry"])
            driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(2)
        return True
    return False

def human_typing(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.07, 0.25))

def login_to_site(driver, email, password, site):
    driver.get(site['login_url'])
    time.sleep(random.uniform(3, 6))
    print(f"Logging into {email}")
    human_typing(driver.find_element(By.ID, site['login_user_selector']), email)
    time.sleep(random.uniform(1, 3))
    human_typing(driver.find_element(By.ID, site['login_pass_selector']), password)
    time.sleep(random.uniform(1, 2))
    driver.find_element(By.XPATH, site['login_button_selector']).click()
    time.sleep(random.uniform(4, 7))

def mimic_human_browsing(driver):
    # Scroll to reveal more content
    for _ in range(random.randint(2, 4)):
        driver.execute_script(f"window.scrollBy(0, {random.randint(300, 600)});")
        time.sleep(random.uniform(1, 2))

def click_see_more_buttons(driver):
    """Click 'See more' buttons to expand content"""
    try:
        see_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'See more') or contains(@class, 'see-more')]")
        for button in see_more_buttons:
            try:
                button.click()
                time.sleep(random.uniform(1, 2))
                print("Clicked 'See more' button")
            except:
                continue
    except:
        pass

def scrape_profile(driver, url):
    driver.get(url)
    time.sleep(random.uniform(4, 8))
    mimic_human_browsing(driver)
    click_see_more_buttons(driver)
    time.sleep(random.uniform(2, 4))

    def selor(xpath, default=""):
        try:
            return driver.find_element(By.XPATH, xpath).text
        except:
            return default

    # Basic info
    name = selor("//h1")
    headline = selor("//div[contains(@class,'text-body-medium')]")
    location = selor("//span[contains(@class,'text-body-small')][1]")

    # Skills - Updated selector based on your HTML
    skills = []
    try:
        skill_elements = driver.find_elements(By.CSS_SELECTOR, "li.skill-item span[dir='ltr']")
        skills = [skill.text for skill in skill_elements if skill.text.strip()]
    except Exception as e:
        print(f"Skills extraction failed: {e}")
        # Fallback selector
        try:
            skill_elements = driver.find_elements(By.XPATH, "//ol[@class='skills-list']//span[@dir='ltr']")
            skills = [skill.text for skill in skill_elements if skill.text.strip()]
        except:
            pass

    # About - Updated selector based on your HTML
    about = ""
    try:
        about_element = driver.find_element(By.CSS_SELECTOR, "div.description[dir='ltr']")
        about = about_element.text
    except Exception:
        # Fallback selectors
        try:
            about = selor("//div[contains(@class, 'summary-container')]//div[contains(@class, 'description')]")
        except:
            about = selor("//div[contains(@class, 'whitespace-pre-line')]")

    # Education - Updated selector based on your HTML
    education_info = []
    try:
        education_items = driver.find_elements(By.CSS_SELECTOR, "section.education-container li.entity-lockup")
        for item in education_items:
            try:
                school = item.find_element(By.CSS_SELECTOR, "div.list-item-heading span[dir='ltr']").text
                degree_info = item.find_elements(By.CSS_SELECTOR, "div.body-small.text-color-text span[dir='ltr']")
                degree = degree_info[0].text if len(degree_info) > 0 else ""
                field = degree_info[1].text if len(degree_info) > 1 else ""
                dates = item.find_element(By.CSS_SELECTOR, "div.text-color-text-low-emphasis").text.strip()
                
                education_entry = f"{school} - {degree}"
                if field:
                    education_entry += f" in {field}"
                if dates:
                    education_entry += f" ({dates})"
                education_info.append(education_entry)
            except Exception as e:
                continue
    except Exception as e:
        print(f"Education extraction failed: {e}")

    # Experience - More robust selector
    experience_info = []
    try:
        experience_items = driver.find_elements(By.CSS_SELECTOR, "section.experience-container li.entity-lockup, section[aria-labelledby*='experience'] li")
        for item in experience_items:
            try:
                position = item.find_element(By.CSS_SELECTOR, "div.list-item-heading, h3").text
                company = item.find_element(By.CSS_SELECTOR, "div.body-small span[dir='ltr'], div.t-14").text
                dates = ""
                try:
                    dates = item.find_element(By.CSS_SELECTOR, "div.text-color-text-low-emphasis, div.t-12").text
                except:
                    pass
                
                exp_entry = f"{position} at {company}"
                if dates:
                    exp_entry += f" ({dates})"
                experience_info.append(exp_entry)
            except Exception:
                continue
    except Exception as e:
        print(f"Experience extraction failed: {e}")

    profile_dict = {
        "name": name,
        "headline": headline,
        "location": location,
        "about": about,
        "skills": ", ".join(skills),
        "education": " | ".join(education_info),
        "experience": " | ".join(experience_info),
        "profile_url": url
    }
    
    print(f"Extracted: {profile_dict['name']} | Skills: {len(skills)} | Education: {len(education_info)} | Experience: {len(experience_info)}")
    return profile_dict

def push_profiles_to_sheets(data, spreadsheet_id, sheet_name='Sheet1'):
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SHEET_CREDS_FILE, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)
    headers = [['Name', 'Headline', 'Location', 'Skills', 'About', 'Education', 'Experience', 'Profile URL']]
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="RAW",
        body={'values': headers}
    ).execute()
    if data:
        seen = set()
        deduped = []
        for d in data:
            key = (d.get('name', ''), d.get('profile_url', ''))
            if key not in seen and d['profile_url']:
                deduped.append(d)
                seen.add(key)
        values = [
            [d.get('name', ''), d.get('headline', ''), d.get('location', ''), d.get('skills', ''), d.get('about', ''), d.get('education', ''), d.get('experience', ''), d.get('profile_url', '')]
            for d in deduped
        ]
        body = {"values": values}
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A2",
            valueInputOption="RAW",
            body=body
        ).execute()
        print(f"Pushed {len(deduped)} profiles to Google Sheet.")

def main():
    # Get input links
    profile_links = []
    with open(INPUT_FILE, "r") as f:
        for line in f:
            url = line.strip()
            if url.startswith('http'):
                profile_links.append(url)
            if len(profile_links) >= MAX_PROFILES:
                break
    print("Extracting from", len(profile_links), "profile links.")

    SITE = {
        "name": "LinkedIn",
        "login_url": "https://www.linkedin.com/login",
        "login_user_selector": "username",
        "login_pass_selector": "password",
        "login_button_selector": "//button[contains(@type, 'submit')]",
        "feed_url": "https://www.linkedin.com/feed/",
    }

    ensure_dir(COOKIES_DIR)
    accounts = load_accounts()
    bot_account = None
    for acc in accounts:
        if (
            acc["site"] == "linkedin" and
            acc.get("registered", False) and
            acc.get("password")
        ):
            bot_account = acc
            break
    if not bot_account:
        print("No registered LinkedIn account with password found!")
        return

    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.binary_location = "/usr/bin/google-chrome"

    driver = uc.Chrome(options=options)
    cookiefile = f"{SITE['name']}_{bot_account['email']}.pkl"
    logged_in = load_cookies(driver, cookiefile, SITE['feed_url'])
    if logged_in and "feed" in driver.current_url:
        print("Session restored via cookies!")
    else:
        print("Cookie session invalid or expired, logging in fresh...")
        try:
            login_to_site(driver, bot_account['email'], bot_account['password'], SITE)
            save_cookies(driver, cookiefile)
        except Exception as e:
            print(f"Login failed: {e}")
            driver.quit()
            return

    data = []
    for i, url in enumerate(profile_links):
        print(f"\nProcessing profile {i+1}/{len(profile_links)}: {url}")
        try:
            profile = scrape_profile(driver, url)
            if profile:
                data.append(profile)
            time.sleep(random.uniform(8, 15))  # Reduced delay between profiles
        except Exception as e:
            print(f"Failed for {url}: {e}")
        if len(data) >= MAX_PROFILES:
            break

    if data:
        push_profiles_to_sheets(data, SPREADSHEET_ID)
        print(f"\n=== EXTRACTION COMPLETE ===")
        print(f"Successfully extracted {len(data)} profiles with details")
    else:
        print("No suitable profiles scraped.")

    if os.path.exists(cookiefile):
        try:
            os.remove(cookiefile)
            print(f"Deleted cookie file: {cookiefile}")
        except Exception as e:
            print(f"Failed to delete cookie file: {cookiefile}, error: {e}")
    driver.quit()

if __name__ == "__main__":
    main()
