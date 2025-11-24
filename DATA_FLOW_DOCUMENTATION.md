# LinkedIn Scraper - Complete Data Flow Documentation

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     LINKEDIN SCRAPER SYSTEM                         │
└─────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │   User      │
                              │  Enters     │
                              │ Parameters  │
                              └──────┬──────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │  extracter.py         │
                         │  (Main Script)        │
                         └───────┬───────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │   main.py    │  │ Apify Actor  │  │ Output Files │
        │  (Flask)     │  │  (Remote API)│  │   (CSV/JSON) │
        │              │  │              │  │              │
        └──────────────┘  └──────────────┘  └──────────────┘
```

---

## Detailed Command & Data Flow

### **PHASE 1: User Input**
```
User Terminal
    │
    └─> python3 extracter.py
        │
        ├─> Display menu
        │
        └─> Get Input:
            ├─ Keyword: "Python Developer"
            ├─ Location: "India"
            └─ Pages: 2
```

---

### **PHASE 2: Fetch Basic Profile Links from main.py**

#### Command Flow:
```
extracter.py main()
    │
    └─> fetch_profile_links(keyword, location, pages)
        │
        ├─ Build HTTP GET Request:
        │  URL: "http://127.0.0.1:5000/scrape-linkedin"
        │  Params: {
        │    "keyword": "Python Developer",
        │    "location": "India",
        │    "with_email": "1",
        │    "pages": 2
        │  }
        │
        └─> Send Request to Flask Server (main.py)
```

#### Data Flow from main.py:
```
main.py (/scrape-linkedin endpoint)
    │
    ├─> Parse request parameters
    ├─> Build Google Search Query:
    │   "site:linkedin.com/in+Python+Developer+India+gmail.com"
    │
    ├─> Launch Selenium WebDriver (Chrome)
    │   │
    │   ├─ Page 1 (start=0):
    │   │   └─> Parse HTML → Extract 10 results
    │   │
    │   └─ Page 2 (start=10):
    │       └─> Parse HTML → Extract 10 results
    │
    └─> Return JSON Response:
        {
          "saved": 20,
          "profiles": [
            {
              "name": "John Doe",
              "designation": "Senior Python Developer",
              "company": "Tech Corp",
              "location": "Bangalore, India",
              "profile_url": "https://linkedin.com/in/johndoe",
              "snippet": "..."
            },
            ... (20 profiles total)
          ]
        }
```

#### Back to extracter.py:
```
receive_response()
    │
    ├─ Parse JSON
    ├─ Extract profiles list
    │
    └─> basic_profiles = [
          {name, designation, company, location, profile_url, snippet},
          {name, designation, company, location, profile_url, snippet},
          ... (20 items)
        ]
```

---

### **PHASE 3: Scrape Detailed Profile Information via Apify**

#### For Each Profile:
```
for each profile in basic_profiles:
    │
    ├─> profile_url = "https://linkedin.com/in/johndoe"
    │
    └─> scrape_profile_details(profile_url, client)
        │
        ├─> Create Apify Request:
        │   {
        │     "url": "https://linkedin.com/in/johndoe"
        │   }
        │
        └─> client.actor("e1xYKjtHLG2Js5YdC").call(run_input)
            │
            └─> API Call to Apify Remote Server
                │
                ├─> Apify Actor starts
                ├─> Visits LinkedIn profile URL
                ├─> Extracts detailed information:
                │   ├─ Full Name
                │   ├─ Headline
                │   ├─ About/Bio
                │   ├─ Experience (list)
                │   ├─ Education (list)
                │   ├─ Skills (list)
                │   ├─ Connections count
                │   └─ ... other fields
                │
                └─> Store in Apify Dataset
                    │
                    └─> Return Dataset ID
```

#### Receive Detailed Data:
```
client.dataset(run["defaultDatasetId"]).iterate_items()
    │
    └─> detailed_profile = {
          "name": "John Doe",
          "headline": "Senior Python Developer | AI/ML Specialist",
          "about": "Passionate about building scalable solutions...",
          "experience": [
            {
              "title": "Senior Developer",
              "company": "Tech Corp",
              "duration": "2+ years"
            },
            ...
          ],
          "education": [
            {
              "school": "IIT Delhi",
              "degree": "BTech",
              "field": "Computer Science"
            }
          ],
          "skills": ["Python", "Django", "AWS", "Docker"],
          "connections": 1243,
          ... (raw_data)
        }
```

---

### **PHASE 4: Merge Data**

```
merge_profile_data(basic_profiles, detailed_profiles)
    │
    ├─ For each basic profile:
    │   │
    │   ├─ Get profile_url
    │   ├─ Find matching detailed profile
    │   │
    │   └─> Create merged_item:
    │       {
    │         # From main.py
    │         "name": "John Doe",
    │         "basic_designation": "Senior Python Developer",
    │         "basic_company": "Tech Corp",
    │         "basic_location": "Bangalore, India",
    │         "profile_url": "https://linkedin.com/in/johndoe",
    │         "snippet": "...",
    │
    │         # From Apify
    │         "detailed_headline": "Senior Python Developer | AI/ML Specialist",
    │         "detailed_about": "Passionate about building...",
    │         "detailed_experience": "[{title: ..., company: ...}, ...]",
    │         "detailed_education": "[{school: ..., degree: ...}, ...]",
    │         "detailed_skills": "[Python, Django, AWS, Docker]",
    │         "detailed_connections": "1243",
    │         "raw_data": "{full JSON from Apify}"
    │       }
    │
    └─> merged_profiles = [merged_item1, merged_item2, ...]
```

---

### **PHASE 5: Save Output Files**

#### CSV (Tabular Format):
```
save_to_csv(merged_profiles, "linkedin_profiles_detailed.csv")
    │
    ├─ Remove "raw_data" column (too large)
    │
    ├─ Create CSV with columns:
    │   name, basic_designation, basic_company, basic_location,
    │   profile_url, snippet, detailed_headline, detailed_about,
    │   detailed_experience, detailed_education, detailed_skills,
    │   detailed_connections
    │
    └─> Write to file: linkedin_profiles_detailed.csv
        ┌─────────────────────────────────────────────────────┐
        │ name      │ basic_designation │ basic_company │ ... │
        ├───────────┼───────────────────┼───────────────┼─────┤
        │ John Doe  │ Senior Developer  │ Tech Corp     │ ... │
        │ Jane Smith│ Data Scientist    │ AI Inc        │ ... │
        └─────────────────────────────────────────────────────┘
```

#### JSON (Raw Data):
```
save_to_json(merged_profiles, "linkedin_profiles_detailed.json")
    │
    ├─ Keep all fields including "raw_data"
    │
    └─> Write to file: linkedin_profiles_detailed.json
        {
          "name": "John Doe",
          "basic_designation": "...",
          "detailed_headline": "...",
          "raw_data": {
            "full": "Apify response"
          },
          ...
        }
```

---

### **PHASE 6: Display Results**

```
display_table(merged_profiles)
    │
    └─> For each profile, print:
        ┌─────────────────────────────────────────┐
        │ 1. John Doe                             │
        │    URL: https://linkedin.com/in/...     │
        │    Basic Role: Senior Developer at...   │
        │    Location: Bangalore, India           │
        │    Headline: Senior Python Developer... │
        │    Connections: 1243                    │
        ├─────────────────────────────────────────┤
        │ 2. Jane Smith                           │
        │    ...                                  │
        └─────────────────────────────────────────┘
```

---

## Complete Data Structure

### Input Data (from User):
```python
{
  "keyword": "Python Developer",
  "location": "India",
  "pages": 2,
  "with_email": 1
}
```

### Step 1: Basic Profiles (from main.py):
```python
[
  {
    "name": "John Doe",
    "designation": "Senior Python Developer",
    "company": "Tech Corp",
    "location": "Bangalore, India",
    "profile_url": "https://linkedin.com/in/johndoe",
    "snippet": "Senior developer with 5+ years..."
  },
  ... (multiple profiles)
]
```

### Step 2: Detailed Profiles (from Apify):
```python
[
  {
    "name": "John Doe",
    "headline": "Senior Python Developer | AI/ML Specialist",
    "about": "Passionate about building scalable solutions...",
    "experience": [
      {
        "title": "Senior Developer",
        "company": "Tech Corp",
        "duration": "2+ years",
        "location": "Bangalore"
      }
    ],
    "education": [
      {
        "school": "IIT Delhi",
        "degree": "BTech",
        "field": "Computer Science",
        "year": "2018"
      }
    ],
    "skills": ["Python", "Django", "AWS", "Docker", "Kubernetes"],
    "connections": 1243,
    "followers": 458,
    ... (other fields from Apify)
  },
  ... (multiple profiles)
]
```

### Step 3: Merged Final Data (saved to CSV/JSON):
```python
{
  # Basic info from main.py
  "name": "John Doe",
  "basic_designation": "Senior Python Developer",
  "basic_company": "Tech Corp",
  "basic_location": "Bangalore, India",
  "profile_url": "https://linkedin.com/in/johndoe",
  "snippet": "Senior developer with 5+ years...",
  
  # Detailed info from Apify
  "detailed_headline": "Senior Python Developer | AI/ML Specialist",
  "detailed_about": "Passionate about building scalable solutions...",
  "detailed_experience": "[{title: Senior Developer, company: Tech Corp, ...}]",
  "detailed_education": "[{school: IIT Delhi, degree: BTech, ...}]",
  "detailed_skills": "[Python, Django, AWS, Docker, Kubernetes]",
  "detailed_connections": "1243",
  
  # Full raw data from Apify
  "raw_data": "{complete JSON from Apify}"
}
```

---

## Execution Timeline

```
Time  │ Component      │ Action
──────┼────────────────┼─────────────────────────────────
  0s  │ User           │ Runs: python3 extracter.py
  1s  │ extracter.py   │ Initializes Apify client
  2s  │ extracter.py   │ Gets user input (keyword, location)
  3s  │ extracter.py   │ Sends HTTP GET to Flask
  4s  │ main.py        │ Launches Selenium + Chrome
  5s  │ main.py        │ Fetches Google page 1
  7s  │ main.py        │ Parses 10 results
  8s  │ main.py        │ Fetches Google page 2
 10s  │ main.py        │ Parses 10 results
 11s  │ main.py        │ Returns JSON to extracter
 12s  │ extracter.py   │ Receives 20 profiles
 13s  │ extracter.py   │ Loops through each profile
 14s  │ extracter.py   │ Profile 1 → Apify API call
 20s  │ Apify          │ Scrapes profile 1 details
 21s  │ extracter.py   │ Receives profile 1 data
 22s  │ extracter.py   │ Profile 2 → Apify API call
 28s  │ Apify          │ Scrapes profile 2 details
...   │ ...            │ (continues for all 20 profiles)
 ∞    │ extracter.py   │ Merges all data
 ∞+1  │ extracter.py   │ Saves CSV & JSON
 ∞+2  │ extracter.py   │ Displays table
 ∞+3  │ extracter.py   │ Program exits
```

---

## API Connections

### 1. extracter.py → main.py (Flask)
```
Method: GET
URL: http://127.0.0.1:5000/scrape-linkedin
Parameters: ?keyword=...&location=...&pages=...&with_email=...
Response: JSON with profile list
```

### 2. extracter.py → Apify (REST API)
```
Method: POST
Endpoint: Apify Client Library
Actor ID: e1xYKjtHLG2Js5YdC
Input: {"url": "https://linkedin.com/in/..."}
Output: Dataset with detailed profile info
```

---

## Error Handling

### If main.py is not running:
```
extracter.py attempts HTTP GET
    ↓
ConnectionError caught
    ↓
Display: "❌ Flask server not running. Start: python3 main.py"
    ↓
Exit gracefully
```

### If Apify API fails:
```
scrape_profile_details() called
    ↓
Apify API error
    ↓
Exception caught, print error message
    ↓
Continue with next profile (detailed = None)
    ↓
Merge with empty detailed data
    ↓
Save with missing detailed fields
```

---

## Summary

| Stage | Input | Process | Output |
|-------|-------|---------|--------|
| 1 | User parameters | extracter.py requests main.py | 20 basic profiles |
| 2 | Profile URLs | main.py scrapes Google | Basic profile info (name, company, location) |
| 3 | Profile URLs | extracter.py requests Apify | Detailed profile info (headline, experience, skills) |
| 4 | Basic + Detailed | Merge in extracter.py | Combined profile data |
| 5 | Merged data | Save to CSV & JSON | Files for analysis |
| 6 | Merged data | Display in terminal | Human-readable table |
