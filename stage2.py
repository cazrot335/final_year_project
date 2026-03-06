import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/chat"

def clean_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def screen_candidate_fit(stage1_data, user_jd):
    """
    Compare extracted resume JSON against Job Description
    using local Ollama LLM.
    """

    system_prompt = """
You are a Senior Technical Recruiter.

You will receive:
1. Candidate Profile
2. Job Description

Perform a gap analysis and return ONLY JSON in this format:

{
  "fit_score": 0,
  "matches": [],
  "gaps": [],
  "recommendation": "",
  "summary": ""
}

Rules:
- fit_score must be between 0 and 100
- recommendation must be one of:
  Strong Hire, Potential, Reject
- summary must be 2 sentences
"""

    payload = {
        "model": "CobaltPulse/Qwen2.5-VL-7B-Instruct:latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""
Job Description:
{user_jd}

Candidate Profile:
{json.dumps(stage1_data, indent=2)}
"""
            }
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "num_ctx": 8192
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()

        data = response.json()
        content = data["message"]["content"]

        return clean_json(content)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "fit_score": 0
        })