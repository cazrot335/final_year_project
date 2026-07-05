import requests
import json
import os
 
def perform_biometric_screening(profile_data):
    HF_TOKEN = os.getenv("HF_TOKEN")
    API_URL = "https://router.huggingface.co/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    system_prompt = (
        "You are a recruitment data extractor. Analyze the volatile JSON provided. "
        "Extract the following fields into a clean JSON structure: "
        "1. name, address (location), profile_id. "
        "2. education (list), experience (list), skills (list). "
        
        "3. biometric_score: (0-100). "
        "4. missing_fields: A static list of required fields that are empty (e.g. ['email', 'phone']). "
        "5. feedback: A brief professional summary. "
        "IMPORTANT: Return ONLY the raw JSON object. NO markdown, NO backticks, NO explanations."
    )

    payload = {
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Parse this: {json.dumps(profile_data)}"}
        ],
        "response_format": {"type": "json_object"},
        "stream": False
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        resp_json = response.json()
        
        if 'choices' in resp_json:
            content = resp_json['choices'][0]['message']['content'].strip()
            
            # THE FIX: Strip markdown backticks manually if they appear
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            return content
        return json.dumps({"error": "Model Error", "biometric_score": 0})
    except Exception as e:
        return json.dumps({"error": str(e), "biometric_score": 0})