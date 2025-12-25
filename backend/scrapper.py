import os
import json
import pickle
import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import undetected_chromedriver as uc

CREDENTIALS_FILE = "accounts.json"
COOKIES_DIR = "cookies/"
OUTPUT_FILE = "linkedin_profiles.txt"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def human_typing(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.07, 0.25))

def realistic_scroll_behavior(driver):
    """Mimics realistic human scrolling patterns"""
    scroll_types = ['smooth', 'jerky', 'fast', 'slow']
    scroll_type = random.choice(scroll_types)
    if scroll_type == 'smooth':
        for i in range(random.randint(3, 7)):
            driver.execute_script(f"window.scrollBy(0, {random.randint(200, 400)});")
            time.sleep(random.uniform(0.5, 1.2))
    elif scroll_type == 'jerky':
        for i in range(random.randint(2, 5)):
            driver.execute_script(f"window.scrollBy(0, {random.randint(100, 600)});")
            time.sleep(random.uniform(0.3, 0.8))
            driver.execute_script(f"window.scrollBy(0, -{random.randint(50, 150)});")
            time.sleep(random.uniform(0.2, 0.5))
    elif scroll_type == 'fast':
        driver.execute_script(f"window.scrollBy(0, {random.randint(800, 1200)});")
        time.sleep(random.uniform(0.8, 1.5))
    else:
        for i in range(random.randint(5, 10)):
            driver.execute_script(f"window.scrollBy(0, {random.randint(100, 250)});")
            time.sleep(random.uniform(1.0, 2.0))

def random_mouse_movement(driver):
    try:
        actions = ActionChains(driver)
        for _ in range(random.randint(1, 3)):
            x = random.randint(50, 800)
            y = random.randint(50, 600)
            actions.move_by_offset(x, y).perform()
            time.sleep(random.uniform(0.1, 0.3))
    except Exception:
        pass

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

def login_to_site(driver, email, password, site):
    driver.get(site['login_url'])
    time.sleep(random.uniform(3, 6))
    print(f"Logging into {email}")
    random_mouse_movement(driver)
    human_typing(driver.find_element(By.ID, site['login_user_selector']), email)
    time.sleep(random.uniform(1, 3))
    human_typing(driver.find_element(By.ID, site['login_pass_selector']), password)
    time.sleep(random.uniform(1, 2))
    driver.find_element(By.XPATH, site['login_button_selector']).click()
    time.sleep(random.uniform(4, 7))

def collect_profiles_with_advanced_scrolling(driver, max_profiles=100, max_attempts=50):
    profile_urls = set()
    attempts = 0
    consecutive_no_new = 0
    last_count = 0
    while len(profile_urls) < max_profiles and attempts < max_attempts and consecutive_no_new < 10:
        attempts += 1
        print(f"Attempt {attempts}: Collected so far: {len(profile_urls)}")
        all_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
        new_found = 0
        for link in all_links:
            try:
                url = link.get_attribute("href")
                if url and url.startswith("https://www.linkedin.com/in/") and "/company/" not in url:
                    clean_url = url.split("?")[0].split("#")[0]
                    if clean_url not in profile_urls:
                        profile_urls.add(clean_url)
                        new_found += 1
                        print(f"Found new profile: {clean_url}")
            except Exception:
                continue
        realistic_scroll_behavior(driver)
        time.sleep(random.uniform(2, 5))
        random_mouse_movement(driver)
        try:
            show_more_buttons = driver.find_elements(By.XPATH,
                "//*[contains(text(), 'Show more') or contains(text(), 'See more') or contains(text(), 'Load more')]")
            if show_more_buttons:
                show_more_buttons[0].click()
                print("Clicked 'Show more' button")
                time.sleep(random.uniform(3, 6))
        except Exception:
            pass
        try:
            next_buttons = driver.find_elements(By.XPATH,
                "//button[contains(@aria-label, 'Next') or contains(text(), 'Next')]")
            if next_buttons and next_buttons[0].is_enabled():
                next_buttons[0].click()
                print("Clicked Next page")
                time.sleep(random.uniform(4, 8))
        except Exception:
            pass
        if len(profile_urls) == last_count:
            consecutive_no_new += 1
        else:
            consecutive_no_new = 0
            last_count = len(profile_urls)
        if attempts % 10 == 0:
            print("Taking a longer break...")
            time.sleep(random.uniform(10, 20))
    return list(profile_urls)

def try_multiple_search_variations(driver, skill, location, max_profiles):
    all_profiles = set()
    search_variations = [
        f"{skill} open to work",
        f"{skill} developer",
        f"{skill} engineer", 
        f"{skill} programmer",
        f"{skill}"
    ]
    location_variations = [
        location,
        f"{location}, India" if "india" not in location.lower() else location,
        location.split()[0] if " " in location else location
    ]
    for i, skill_var in enumerate(search_variations):
        if len(all_profiles) >= max_profiles:
            break
        for j, loc_var in enumerate(location_variations):
            if len(all_profiles) >= max_profiles:
                break
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={skill_var.replace(' ','%20')}&location={loc_var.replace(' ','%20')}"
            print(f"\nTrying search variation {i+1}-{j+1}: {search_url}")
            driver.get(search_url)
            time.sleep(random.uniform(3, 6))
            profiles = collect_profiles_with_advanced_scrolling(driver,
                max_profiles=max_profiles-len(all_profiles),
                max_attempts=20
            )
            for profile in profiles:
                all_profiles.add(profile)
            print(f"Total unique profiles so far: {len(all_profiles)}")
            if i < len(search_variations)-1 or j < len(location_variations)-1:
                time.sleep(random.uniform(15, 25))
    return list(all_profiles)

def main():
    print("=== LinkedIn Profile URL Collector ===")
    print("What skill/role to search? (e.g. python developer, react developer, full stack)")
    skill = input("Skill: ").strip()
    print("What location? (e.g. India, San Francisco, Maharashtra)")
    location = input("Location: ").strip()
    print("How many profile links do you want to collect? (Recommended: 20-100)")
    try:
        max_profiles = int(input("Max links: ").strip())
    except:
        max_profiles = 50

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

    all_profiles = try_multiple_search_variations(driver, skill, location, max_profiles)
    with open(OUTPUT_FILE, "w") as f:
        for url in all_profiles:
            f.write(url + "\n")
    print(f"\n=== COLLECTION COMPLETE ===\nTotal unique profiles collected: {len(all_profiles)}\nSaved to: {OUTPUT_FILE}")

    if os.path.exists(cookiefile):
        try:
            os.remove(cookiefile)
            print(f"Deleted cookie file: {cookiefile}")
        except Exception as e:
            print(f"Failed to delete cookie file: {e}")
    driver.quit()

if __name__ == "__main__":
    main()
