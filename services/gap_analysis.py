import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/chat"


def clean_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def build_candidate_profile(db_profile):
    """
    Convert DB model to structured profile
    for LLM comparison.
    """

    skills = []
    try:
        skills = json.loads(db_profile.skills)
    except:
        if db_profile.skills:
            skills = [s.strip() for s in db_profile.skills.split(",")]

    return {
        "name": db_profile.name,
        "headline": db_profile.headline,
        "skills": skills,
        "experience": db_profile.experience,
        "education": db_profile.education,
        "biometric_score": db_profile.biometric_score
    }


def screen_candidate_fit(profile_data, user_jd):

    system_prompt = """
You are a Senior Technical Recruiter performing a technical hiring screen.

Return ONLY JSON in this structure:

{
  "fit_score": 0,
  "recommendation": "",
  "summary": "",
  "matches": [],
  "gaps": [],
  "radar_scores": {
    "skills": 0,
    "experience": 0,
    "domain": 0,
    "education": 0,
    "tools": 0
  }
}

Rules:

fit_score:
0-100

recommendation must be:
Strong Hire
Potential
Reject

radar_scores must represent candidate strength across:

skills
experience
domain
education
tools

summary must be 2 sentences explaining reasoning.

matches:
specific areas where candidate aligns with JD

gaps:
specific missing skills, tools, or experience
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
{json.dumps(profile_data, indent=2)}
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

        cleaned = clean_json(content)

        return json.loads(cleaned)

    except Exception as e:

        return {
            "error": str(e),
            "fit_score": 0,
            "recommendation": "Reject",
            "summary": "Analysis failed.",
            "matches": [],
            "gaps": [],
            "radar_scores": {
                "skills": 0,
                "experience": 0,
                "domain": 0,
                "education": 0,
                "tools": 0
            }
        }