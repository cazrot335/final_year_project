from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import random

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Flask LinkedIn Google Scraper is running!"

@app.route("/scrape-linkedin", methods=["GET"])
def scrape_linkedin():
    keyword = request.args.get("keyword")
    location = request.args.get("location")
    with_email = request.args.get("with_email", "1") == "1"
    pages = int(request.args.get("pages", 3))

    if not keyword or not location:
        return jsonify({"error": "Keyword and location are required"}), 400

    # Build search query
    query = f'site:linkedin.com/in {keyword} {location}'
    if with_email:
        query += ' gmail.com'
    query = query.strip().replace(' ', '+')

    base_url = f"https://www.google.com/search?q={query}&start="

    # Setup Chrome options
    options = Options()
    options.headless = True
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119 Safari/537.36")

    # Initialize browser
    driver = webdriver.Chrome(options=options)

    # Bypass bot detection
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
        """
    })

    results = []

    try:
        for page in range(pages):
            start = page * 10
            url = f"{base_url}{start}"
            print(f"🔍 Fetching page {page + 1}: {url}")
            driver.get(url)
            time.sleep(random.uniform(2, 4))

            search_results = driver.find_elements(By.CSS_SELECTOR, 'div.MjjYud')
            print(f"📄 Found {len(search_results)} results")

            for result in search_results:
                try:
                    link_el = result.find_element(By.CSS_SELECTOR, 'a')
                    title_el = result.find_element(By.CSS_SELECTOR, 'h3')
                    snippet_el = result.find_element(By.CSS_SELECTOR, '.VwiC3b')

                    href = link_el.get_attribute('href')
                    if 'linkedin.com/in' in href:
                        results.append({
                            "name": title_el.text.strip() if title_el else '',
                            "profile_url": href,
                            "snippet": snippet_el.text.strip() if snippet_el else ''
                        })
                except Exception as e:
                    print(f"❌ Error parsing result: {e}")
                    continue

            time.sleep(random.uniform(1, 2))

    finally:
        driver.quit()

    return jsonify({
        "saved": len(results),
        "profiles": results
    })

if __name__ == "__main__":
    app.run(debug=True)
