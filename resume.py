import os
import fitz  # PyMuPDF
import pandas as pd
import ollama
import json
from tqdm import tqdm

# --- CONFIGURATION ---
SOURCE_DIR = os.path.abspath("./resumes")  # Use absolute path
OUTPUT_FILE = "resume_analysis_results.csv"
MODEL = "bobowg/gemini-3-flash"

# Ensure directory exists
if not os.path.exists(SOURCE_DIR):
    print(f"ERROR: Directory '{SOURCE_DIR}' not found!")
    exit()

def extract_clean_text(pdf_path):
    try:
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        # Remove null bytes and clean whitespace
        return " ".join(text.replace('\x00', '').split())
    except Exception as e:
        print(f"\n[Error] Reading PDF {os.path.basename(pdf_path)}: {e}")
        return None

def analyze_resume(text):
    prompt = f"""
    Extract from resume text: Name, Email, Phone, Skills, Years_of_Experience, Highest_Degree, Job_Title.
    Return ONLY a valid JSON object. 
    Use null if information is missing.
    Text: {text[:4000]}
    """
    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            format='json'
        )
        content = response['message']['content']
        # Clean potential markdown backticks if AI adds them
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"\n[Error] AI Analysis: {e}")
        return None

# --- MAIN EXECUTION ---
all_data = []
pdf_files = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith('.pdf')]

print(f"Found {len(pdf_files)} resumes in {SOURCE_DIR}. Starting...")

for filename in tqdm(pdf_files):
    full_path = os.path.join(SOURCE_DIR, filename)
    raw_text = extract_clean_text(full_path)
    
    if raw_text and len(raw_text.strip()) > 10:
        structured_data = analyze_resume(raw_text)
        if structured_data:
            # Ensure consistent keys for CSV columns
            row = {
                "Name": structured_data.get("Name"),
                "Email": structured_data.get("Email"),
                "Phone": structured_data.get("Phone"),
                "Skills": structured_data.get("Skills"),
                "Experience": structured_data.get("Years_of_Experience"),
                "Education": structured_data.get("Highest_Degree"),
                "Title": structured_data.get("Job_Title"),
                "File_Name": filename
            }
            all_data.append(row)
    else:
        print(f"\n[Skip] {filename} is empty or unreadable.")

# --- FINAL SAVE ---
if all_data:
    df = pd.DataFrame(all_data)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nDONE! {len(all_data)} resumes analyzed. Data saved to {OUTPUT_FILE}")
else:
    print("\nNo data was extracted. Check your PDF paths or API connection.")