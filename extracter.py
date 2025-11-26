import requests
import json
import csv
import time
import os
from datetime import datetime
from dotenv import load_dotenv
from apify_client import ApifyClient

# Load environment variables from .env file
load_dotenv()

# ============================================
# CONFIGURATION (from .env file)
# ============================================
FLASK_SERVER = os.getenv("FLASK_SERVER", "http://127.0.0.1:5000")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "e1xYKjtHLG2Js5YdC")

# Output files
OUTPUT_JSON = "linkedin_profiles_detailed.json"
OUTPUT_CSV = "linkedin_profiles_detailed.csv"

# ============================================
# STEP 1: Fetch profile links from main.py
# ============================================
def fetch_profile_links(keyword, location, pages=2, with_email=1):
    """Fetch LinkedIn profile links from main.py Flask server"""
    print(f"\n🔍 Fetching profile links for: {keyword} in {location}")
    
    params = {
        "keyword": keyword,
        "location": location,
        "with_email": with_email,
        "pages": pages
    }
    
    try:
        response = requests.get(f"{FLASK_SERVER}/scrape-linkedin", params=params, timeout=600)
        response.raise_for_status()
        data = response.json()
        
        profiles = data.get("profiles", [])
        print(f"✅ Found {len(profiles)} profile links")
        
        return profiles
    
    except requests.exceptions.ConnectionError:
        print("❌ Error: Flask server not running. Start it with: python3 main.py")
        return []
    except Exception as e:
        print(f"❌ Error fetching profiles: {e}")
        return []

# ============================================
# STEP 2: Scrape detailed info using Apify
# ============================================
def scrape_profile_details(profile_url, client):
    """Use Apify Actor to scrape detailed profile information"""
    try:
        print(f"  📍 Scraping: {profile_url}")
        
        # Prepare Apify input
        run_input = {"url": profile_url}
        
        # Run the Actor
        run = client.actor(APIFY_ACTOR_ID).call(run_input=run_input)
        
        # Fetch results from dataset
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if items:
            return items[0]  # Return first item (main profile data)
        else:
            return None
    
    except Exception as e:
        print(f"  ❌ Error scraping {profile_url}: {str(e)[:100]}")
        return None

# ============================================
# STEP 3: Merge and process data
# ============================================
def merge_profile_data(basic_profiles, detailed_profiles):
    """Merge basic info (from main.py) with detailed info (from Apify)"""
    merged = []
    
    for basic in basic_profiles:
        profile_url = basic.get("profile_url", "")
        
        # Find corresponding detailed data
        detailed = next((p for p in detailed_profiles if p and profile_url in str(p)), None)
        
        merged_item = {
            # Basic info from main.py
            "name": basic.get("name", ""),
            "basic_designation": basic.get("designation", ""),
            "basic_company": basic.get("company", ""),
            "basic_location": basic.get("location", ""),
            "profile_url": profile_url,
            "snippet": basic.get("snippet", ""),
            
            # Detailed info from Apify (if available)
            "detailed_headline": detailed.get("headline", "") if detailed else "",
            "detailed_about": detailed.get("about", "") if detailed else "",
            "detailed_experience": str(detailed.get("experience", [])) if detailed else "",
            "detailed_education": str(detailed.get("education", [])) if detailed else "",
            "detailed_skills": str(detailed.get("skills", [])) if detailed else "",
            "detailed_connections": detailed.get("connections", "") if detailed else "",
            "raw_data": json.dumps(detailed) if detailed else ""
        }
        
        merged.append(merged_item)
    
    return merged

# ============================================
# STEP 4: Save to CSV (Tabular format)
# ============================================
def save_to_csv(profiles, filename):
    """Save profiles to CSV file"""
    if not profiles:
        print("❌ No profiles to save")
        return
    
    try:
        # Remove raw_data for CSV (too large)
        profiles_for_csv = []
        for p in profiles:
            p_copy = p.copy()
            p_copy.pop("raw_data", None)
            profiles_for_csv.append(p_copy)
        
        keys = profiles_for_csv[0].keys()
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(profiles_for_csv)
        
        print(f"✅ Saved to CSV: {filename}")
    
    except Exception as e:
        print(f"❌ Error saving CSV: {e}")

# ============================================
# STEP 5: Save to JSON
# ============================================
def save_to_json(profiles, filename):
    """Save profiles to JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved to JSON: {filename}")
    
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")

# ============================================
# STEP 6: Display results in table format
# ============================================
def display_table(profiles):
    """Display profiles in table format"""
    if not profiles:
        print("❌ No profiles to display")
        return
    
    print("\n" + "="*120)
    print("SCRAPED LINKEDIN PROFILES")
    print("="*120)
    
    for i, profile in enumerate(profiles, 1):
        print(f"\n{i}. {profile['name']}")
        print(f"   URL: {profile['profile_url']}")
        print(f"   Basic Role: {profile['basic_designation']} at {profile['basic_company']}")
        print(f"   Location: {profile['basic_location']}")
        
        if profile['detailed_headline']:
            print(f"   Headline: {profile['detailed_headline']}")
        
        if profile['detailed_connections']:
            print(f"   Connections: {profile['detailed_connections']}")
        
        print("-" * 120)

# ============================================
# MAIN EXECUTION
# ============================================
def main():
    print("\n" + "="*60)
    print("LINKEDIN PROFILE SCRAPER & EXTRACTOR")
    print("="*60)
    
    # Check Apify API token
    if not APIFY_API_TOKEN or APIFY_API_TOKEN == "":
        print("\n❌ ERROR: APIFY_API_TOKEN not found in .env file!")
        print("Please add your token to .env file:")
        print("   APIFY_API_TOKEN=your_token_here")
        print("Get your token from: https://apify.com/account/integrations")
        return
    
    # Initialize Apify client
    try:
        client = ApifyClient(APIFY_API_TOKEN)
        print("✅ Apify client initialized")
    except Exception as e:
        print(f"❌ Error initializing Apify: {e}")
        return
    
    # Get search parameters
    print("\n📝 Enter search parameters:")
    keyword = input("   Keyword (e.g., 'Python Developer'): ").strip() or "Python Developer"
    location = input("   Location (e.g., 'India'): ").strip() or "India"
    pages = int(input("   Pages (default 1): ").strip() or "1")
    
    # Step 1: Fetch profile links from main.py
    basic_profiles = fetch_profile_links(keyword, location, pages)
    
    if not basic_profiles:
        print("❌ No profiles found. Exiting.")
        return
    
    print(f"\n🔗 Found {len(basic_profiles)} profiles to scrape")
    
    # Step 2: Scrape detailed info for each profile
    print("\n⏳ Scraping detailed information (this may take a while)...")
    detailed_profiles = []
    
    for i, profile in enumerate(basic_profiles, 1):
        print(f"\n[{i}/{len(basic_profiles)}]")
        details = scrape_profile_details(profile["profile_url"], client)
        detailed_profiles.append(details)
        time.sleep(2)  # Rate limiting
    
    # Step 3: Merge data
    print("\n🔄 Merging profile data...")
    merged_profiles = merge_profile_data(basic_profiles, detailed_profiles)
    
    # Step 4: Save results
    print("\n💾 Saving results...")
    save_to_csv(merged_profiles, OUTPUT_CSV)
    save_to_json(merged_profiles, OUTPUT_JSON)
    
    # Step 5: Display table
    display_table(merged_profiles)
    
    print("\n" + "="*60)
    print("✅ COMPLETED!")
    print(f"   CSV: {OUTPUT_CSV}")
    print(f"   JSON: {OUTPUT_JSON}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
