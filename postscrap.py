import os
import time
import random
import requests
from stage1 import perform_biometric_screening
from stage2 import screen_candidate_fit
from datetime import datetime
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from models import AnalyzedProfile, db, Profile, ScrapeLog, GlobalStats
from routes.pipeline_routes import pipeline_bp
from routes.profile_routes import profile_bp

# Selenium + webdriver-manager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Apify
from apify_client import ApifyClient

load_dotenv()

# ── Interview module ────────────────────────────────────────────────────────
from stage4_interview import (
    generate_questions,
    speak_question,
    transcribe_answer,
    evaluate_answer,
    generate_final_report,
    InterviewReport,
    QAEntry,
    AUDIO_DIR,
)
import uuid
from concurrent.futures import ThreadPoolExecutor

# In-memory session store  { session_id: InterviewReport }
# Swap for Redis in production
_interview_sessions: dict = {}

# ── Config ──────────────────────────────────────────────────────────────────
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_ACTOR_ID  = os.getenv("APIFY_ACTOR_ID", "pratikdani/linkedin-people-profile-scraper")

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "linkedin_profiles")
os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_JSON = os.path.join(DATA_DIR, "linkedin_profiles_detailed.json")
OUTPUT_CSV  = os.path.join(DATA_DIR, "linkedin_profiles_detailed.csv")

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///recruiter.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

    from sqlalchemy import text
    try:
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS interview_results (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_url      TEXT,
                candidate_name   TEXT,
                interview_date   DATETIME DEFAULT CURRENT_TIMESTAMP,
                overall_score    REAL,
                recommendation   TEXT,
                summary          TEXT,
                full_report_json TEXT,
                created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.commit()
    except Exception:
        pass

    # Add synced_at column to profiles if missing (safe no-op if already exists)
    try:
        db.session.execute(text("ALTER TABLE profiles ADD COLUMN synced_at DATETIME"))
        db.session.commit()
    except Exception:
        pass


# ── Dork cache (in-memory, 24h TTL per keyword+location combo) ───────────────
_dork_cache: dict = {}
_DORK_CACHE_TTL = 86400  # seconds


app.register_blueprint(pipeline_bp, url_prefix="/api/pipeline")
app.register_blueprint(profile_bp,  url_prefix="/api/profiles")


# ────────────────────────────────────────────────────────────────────────────
# Helpers (unchanged from original)
# ────────────────────────────────────────────────────────────────────────────

def scrape_google_profiles(keyword, location, pages=3, with_email=True):
    cache_key = f"{keyword.lower()}|{location.lower()}"
    cached = _dork_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < _DORK_CACHE_TTL:
        return cached["results"]

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
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/119 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=options)

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
            url   = f"{base_url}{start}"
            driver.get(url)
            time.sleep(random.uniform(2, 4))

            search_results = driver.find_elements(By.CSS_SELECTOR, 'div.MjjYud')
            if not search_results:
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

                    href    = link_el.get_attribute('href') if link_el else ''
                    title   = title_el.text.strip() if title_el else ''
                    snippet = snippet_el.text.strip() if snippet_el else ''

                    title_parts = title.split(' - ')
                    name        = title_parts[0].strip() if title_parts else ''
                    designation = title_parts[1].strip() if len(title_parts) > 1 else ''
                    company     = title_parts[2].strip() if len(title_parts) > 2 else ''

                    try:
                        info_el   = result.find_element(By.CSS_SELECTOR, '.YrbPuc')
                        info_line = info_el.text.strip()
                    except Exception:
                        info_line = ''

                    info_parts = info_line.split(' · ')
                    if not designation and len(info_parts) > 1:
                        designation = info_parts[1].strip()
                    if not company and len(info_parts) > 2:
                        company = info_parts[2].strip()
                    loc = info_parts[0].strip() if info_parts else ''

                    if 'linkedin.com/in' in href:
                        results.append({
                            "name":        name,
                            "designation": designation,
                            "company":     company,
                            "location":    loc,
                            "profile_url": href,
                            "snippet":     snippet,
                        })
                except Exception:
                    continue

            time.sleep(random.uniform(1.5, 2.5))
    finally:
        driver.quit()

    _dork_cache[cache_key] = {"ts": time.time(), "results": results}
    return results


def fetch_detailed_profiles(basic_profiles):
    if not APIFY_API_TOKEN:
        return [None] * len(basic_profiles)

    client   = ApifyClient(APIFY_API_TOKEN)
    detailed = []
    for profile in basic_profiles:
        url = profile.get('profile_url')
        try:
            run   = client.actor(APIFY_ACTOR_ID).call(run_input={"url": url})
            items = list(client.dataset(run['defaultDatasetId']).iterate_items())
            detailed.append(items[0] if items else None)
        except Exception:
            detailed.append(None)
        time.sleep(1)
    return detailed


def merge_profile_data(basic_profiles, detailed_profiles):
    merged = []
    for basic, detailed in zip(basic_profiles, detailed_profiles):
        merged.append({
            "name":                 basic.get('name', ''),
            "basic_designation":    basic.get('designation', ''),
            "basic_company":        basic.get('company', ''),
            "basic_location":       basic.get('location', ''),
            "profile_url":          basic.get('profile_url', ''),
            "snippet":              basic.get('snippet', ''),
            "detailed_headline":    detailed.get('headline', '')     if detailed else '',
            "detailed_about":       detailed.get('about', '')        if detailed else '',
            "detailed_experience":  detailed.get('experience', [])   if detailed else [],
            "detailed_education":   detailed.get('education', [])    if detailed else [],
            "detailed_skills":      detailed.get('skills', [])       if detailed else [],
            "detailed_connections": detailed.get('connections', '')  if detailed else '',
            "raw_data":             detailed if detailed else None,
        })
    return merged


# ────────────────────────────────────────────────────────────────────────────
# Original routes (unchanged)
# ────────────────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return 'Server is running.'


@app.route('/scrape-profile', methods=['GET'])
def api_scrape_single_profile():
    profile_url = request.args.get('url')
    if not profile_url:
        return jsonify({'error': 'LinkedIn URL is required'}), 400
    try:
        client  = ApifyClient(APIFY_API_TOKEN)
        run     = client.actor(APIFY_ACTOR_ID).call(run_input={"url": profile_url})
        items   = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return jsonify({'status': 'success', 'data': None}), 200
        return jsonify({'status': 'success', 'data': items[0]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/scrape-linkedin', methods=['GET'])
def api_scrape_linkedin():
    keyword  = request.args.get('keyword')
    location = request.args.get('location')
    pages    = int(request.args.get('pages', 1))

    raw_results  = scrape_google_profiles(keyword, location, pages=pages)
    total_count  = len(raw_results)
    unique_count = 0
    
    for p in raw_results:
        url    = p.get('profile_url')
        exists = Profile.query.filter_by(profile_url=url).first()
        if not exists:
            db.session.add(Profile(
                profile_url=url,
                name=p.get('name'),
                designation=p.get('designation'),
                snippet=p.get('snippet')
            ))
            unique_count += 1

    db.session.add(ScrapeLog(
        keyword_used=keyword,
        total_found=total_count,
        unique_new=unique_count
    ))
    db.session.commit()

    return jsonify({
        "status":         "success",
        "session_total":  total_count,
        "session_unique": unique_count,
        "efficiency":     f"{(unique_count/total_count)*100 if total_count > 0 else 0:.1f}%"
    })


@app.route('/extract-relevant-data', methods=['POST'])
def api_intelligent_extraction():
    raw_input = request.get_json()
    if not raw_input:
        return jsonify({"error": "No data received"}), 400

    ai_result_str = perform_biometric_screening(raw_input)
    try:
        data = json.loads(ai_result_str)
        return jsonify({
            "status": "success",
            "biometric_score": data.get("biometric_score", 0),
            "profile_analysis": {
                "identity":     {"name": data.get("name"), "profile_id": data.get("profile_id"), "address": data.get("address")},
                "contact":      data.get("biometrics", {}),
                "professional": {"skills": data.get("skills", []), "experience": data.get("experience", []), "education": data.get("education", [])}
            },
            "recruiter_notes": {
                "missing_static_fields": data.get("missing_fields", []),
                "ai_feedback":           data.get("feedback")
            }
        })
    except Exception as e:
        return jsonify({"error": "JSON Parsing Failed", "reason": str(e), "raw_ai_output": ai_result_str}), 500


@app.route('/stage2-screen', methods=['POST'])
def api_stage2_screen():
    jd_text      = request.args.get("jd")
    profile_data = request.get_json(silent=True)
    if not jd_text or not profile_data:
        return jsonify({"error": "Missing input data"}), 400

    raw_ai_output = screen_candidate_fit(profile_data, jd_text)
    try:
        screening_result = json.loads(raw_ai_output.strip())
        return jsonify({"status": "success", "candidate": profile_data.get("name", "Unknown"), "screening_report": screening_result})
    except Exception as e:
        return jsonify({"error": "Final JSON parsing failed", "reason": str(e), "raw_ai_content": raw_ai_output}), 500


@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard():
    total_unique       = Profile.query.count()
    total_scraped_ever = db.session.query(db.func.sum(ScrapeLog.total_found)).scalar() or 0
    return jsonify({
        "total_unique_profiles":      total_unique,
        "total_scraped_links":        int(total_scraped_ever),
        "duplicate_profiles_filtered": int(total_scraped_ever) - total_unique
    })


@app.route('/api/scrape-logs', methods=['GET'])
def get_scrape_logs():
    logs = ScrapeLog.query.order_by(ScrapeLog.timestamp.desc()).limit(10).all()
    formatted = []
    for log in logs:
        efficiency = (log.unique_new / log.total_found * 100) if log.total_found else 0
        formatted.append({
            "timestamp":   log.timestamp.strftime("%H:%M:%S"),
            "keyword":     log.keyword_used,
            "total_found": log.total_found,
            "unique_new":  log.unique_new,
            "efficiency":  round(efficiency, 1)
        })
    return jsonify(list(reversed(formatted)))


@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    page        = int(request.args.get("page", 1))
    limit       = int(request.args.get("limit", 6))
    designation = request.args.get("designation")
    location    = request.args.get("location")

    query = Profile.query
    if designation:
        query = query.filter(Profile.designation.ilike(f"%{designation}%"))
    if location:
        query = query.filter(Profile.snippet.ilike(f"%{location}%"))

    total    = query.count()
    profiles = query.order_by(Profile.created_at.desc()).offset((page-1)*limit).limit(limit).all()

    return jsonify({
        "status":         "success",
        "total_profiles": total,
        "page":           page,
        "results": [{
            "id":          p.id,
            "name":        p.name,
            "designation": p.designation,
            "snippet":     p.snippet,
            "profile_url": p.profile_url,
            "synced_at":   p.synced_at.isoformat() if p.synced_at else None,
        } for p in profiles]
    })


@app.route('/api/profiles/<int:profile_id>/data', methods=['GET'])
def get_profile_data(profile_id):
    profile = Profile.query.get(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    ap = AnalyzedProfile.query.filter_by(profile_url=profile.profile_url).first()
    if not ap:
        return jsonify({
            "synced":      False,
            "id":          profile.id,
            "name":        profile.name,
            "designation": profile.designation,
            "snippet":     profile.snippet,
            "profile_url": profile.profile_url,
            "synced_at":   None,
        })

    raw = json.loads(ap.raw_json or "{}")
    return jsonify({
        "synced":      True,
        "id":          profile.id,
        "name":        ap.name or profile.name,
        "headline":    ap.headline,
        "profile_url": profile.profile_url,
        "synced_at":   profile.synced_at.isoformat() if profile.synced_at else None,
        "biometric_score": ap.biometric_score,
        "skills":      json.loads(ap.skills or "[]"),
        "experience":  json.loads(ap.experience or "[]"),
        "education":   json.loads(ap.education or "[]"),
        "ai_feedback": raw.get("feedback", ""),
        "missing_fields": raw.get("missing_fields", []),
    })


@app.route('/api/profiles/<int:profile_id>/sync', methods=['POST'])
def sync_profile(profile_id):
    profile = Profile.query.get(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    if not APIFY_API_TOKEN:
        return jsonify({"error": "APIFY_API_TOKEN not configured"}), 500

    try:
        client      = ApifyClient(APIFY_API_TOKEN)
        run         = client.actor(APIFY_ACTOR_ID).call(run_input={"url": profile.profile_url})
        items       = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return jsonify({"error": "Apify returned no data"}), 404
        raw_profile = items[0]
    except Exception as e:
        return jsonify({"error": f"Apify failed: {str(e)}"}), 500

    try:
        ai_result_str = perform_biometric_screening(raw_profile)
        ai_data       = json.loads(ai_result_str)
    except Exception as e:
        return jsonify({"error": "AI parsing failed", "reason": str(e)}), 500

    existing = AnalyzedProfile.query.filter_by(profile_url=profile.profile_url).first()
    if existing:
        existing.name            = ai_data.get("name", existing.name)
        existing.headline        = raw_profile.get("headline", existing.headline)
        existing.skills          = json.dumps(ai_data.get("skills", []))
        existing.experience      = json.dumps(ai_data.get("experience", []))
        existing.education       = json.dumps(ai_data.get("education", []))
        existing.biometric_score = ai_data.get("biometric_score", 0)
        existing.raw_json        = json.dumps(ai_data)
        existing.created_at      = datetime.utcnow()
    else:
        db.session.add(AnalyzedProfile(
            profile_url     = profile.profile_url,
            name            = ai_data.get("name"),
            headline        = raw_profile.get("headline", ""),
            skills          = json.dumps(ai_data.get("skills", [])),
            experience      = json.dumps(ai_data.get("experience", [])),
            education       = json.dumps(ai_data.get("education", [])),
            biometric_score = ai_data.get("biometric_score", 0),
            raw_json        = json.dumps(ai_data),
        ))

    profile.is_deep_scraped = True
    profile.synced_at       = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "status":    "synced",
        "synced_at": profile.synced_at.isoformat(),
        "name":      ai_data.get("name"),
        "headline":  raw_profile.get("headline", ""),
    })


@app.route('/api/pipeline/profile-analysis', methods=['POST'])
def pipeline_profile_analysis():
    data        = request.get_json()
    profile_url = data.get("url")
    if not profile_url:
        return jsonify({"error": "LinkedIn URL required"}), 400

    existing = AnalyzedProfile.query.filter_by(profile_url=profile_url).first()
    if existing:
        ai_data        = json.loads(existing.raw_json)
        analysed_count = AnalyzedProfile.query.count()
        return jsonify({
            "status": "cached",
            "candidate_summary": {
                "name": existing.name, "headline": existing.headline,
                "biometric_score": existing.biometric_score,
                "skills": json.loads(existing.skills),
                "experience": json.loads(existing.experience),
                "education": json.loads(existing.education)
            },
            "recruiter_notes":  {"missing_fields": ai_data.get("missing_fields", []), "ai_feedback": ai_data.get("feedback")},
            "pipeline_metrics": {"total_links_analysed": analysed_count}
        })

    try:
        client = ApifyClient(APIFY_API_TOKEN)
        run    = client.actor(APIFY_ACTOR_ID).call(run_input={"url": profile_url})
        items  = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return jsonify({"error": "Profile not found"}), 404
        raw_profile = items[0]
    except Exception as e:
        return jsonify({"error": f"Apify scrape failed: {str(e)}"}), 500

    try:
        ai_result_str = perform_biometric_screening(raw_profile)
        ai_data       = json.loads(ai_result_str)
    except Exception as e:
        return jsonify({"error": "AI parsing failed", "reason": str(e)}), 500

    try:
        new_profile = AnalyzedProfile(
            profile_url=profile_url,
            name=ai_data.get("name"),
            headline=raw_profile.get("headline", ""),
            skills=json.dumps(ai_data.get("skills", [])),
            experience=json.dumps(ai_data.get("experience", [])),
            education=json.dumps(ai_data.get("education", [])),
            biometric_score=ai_data.get("biometric_score", 0),
            raw_json=json.dumps(ai_data)
        )
        db.session.add(new_profile)
        db.session.commit()
    except Exception as e:
        return jsonify({"error": "DB insert failed", "reason": str(e)}), 500

    analysed_count = AnalyzedProfile.query.count()
    return jsonify({
        "status": "success",
        "candidate_summary": {
            "name": ai_data.get("name"), "headline": raw_profile.get("headline"),
            "biometric_score": ai_data.get("biometric_score"),
            "skills": ai_data.get("skills", []),
            "experience": ai_data.get("experience", []),
            "education": ai_data.get("education", [])
        },
        "recruiter_notes":  {"missing_fields": ai_data.get("missing_fields", []), "ai_feedback": ai_data.get("feedback")},
        "pipeline_metrics": {"total_links_analysed": analysed_count}
    })


# ════════════════════════════════════════════════════════════════════════════
# INTERVIEW MODULE ROUTES  (stage 4)
# ════════════════════════════════════════════════════════════════════════════

# ── POST /api/interview/start ────────────────────────────────────────────────
# Body: { "profile_url": "...", "num_questions": 5 }
# Returns session_id + questions + per-question audio URLs
@app.route('/api/interview/start', methods=['POST'])
def interview_start():
    data          = request.get_json()
    profile_url   = data.get("profile_url")
    num_questions = int(data.get("num_questions", 5))
    skip_audio    = bool(data.get("skip_audio", False))
    tts_speaker   = data.get("speaker", "")

    if not profile_url:
        return jsonify({"error": "profile_url is required"}), 400

    # Must be analyzed by stage1 first
    ap = AnalyzedProfile.query.filter_by(profile_url=profile_url).first()
    if not ap:
        return jsonify({
            "error": "Profile not analyzed yet.",
            "hint":  "Run POST /api/pipeline/profile-analysis first."
        }), 404

    # Normalize DB field names → interview module format
    # DB uses Apify keys: company_name/job_title/university_name
    # LLM prompt expects: company/role/institution/degree

    def _norm_exp(exp_list):
        out = []
        for e in exp_list:
            out.append({
                "company":     e.get("company_name") or e.get("company", ""),
                "role":        e.get("job_title")    or e.get("role", ""),
                "duration":    f"{e.get('start_date','')} – {e.get('end_date','')}".strip(" –"),
                "location":    e.get("location", ""),
                "description": e.get("description", "")
            })
        return out

    def _norm_edu(edu_list):
        out = []
        for e in edu_list:
            out.append({
                "institution": e.get("university_name") or e.get("institution", ""),
                "degree":      e.get("degree", ""),
                "grade":       e.get("grade", ""),
                "years":       f"{e.get('start_date','')} – {e.get('end_date','')}".strip(" –")
            })
        return out

    raw_exp    = json.loads(ap.experience or "[]")
    raw_edu    = json.loads(ap.education  or "[]")
    raw_skills = json.loads(ap.skills     or "[]")
    raw_data   = json.loads(ap.raw_json   or "{}")

    # skills may be list of strings OR list of dicts — flatten either way
    if raw_skills and isinstance(raw_skills[0], dict):
        raw_skills = [s.get("name") or s.get("skill", "") for s in raw_skills]

    profile = {
        "name":        ap.name        or "Unknown",
        "headline":    ap.headline    or "",
        "profile_url": ap.profile_url,
        "skills":      raw_skills,
        "experience":  _norm_exp(raw_exp),
        "education":   _norm_edu(raw_edu),
        "address":     raw_data.get("address", ""),
        "feedback":    raw_data.get("feedback", ""),
    }

    session_id = str(uuid.uuid4())[:12]

    # Generate questions via LLM
    questions = generate_questions(profile, num_questions)

    # Build skeleton report stored in session
    report = InterviewReport(
        candidate_name = profile["name"],
        profile_url    = profile_url,
        interview_date = datetime.utcnow().isoformat(),
        raw_profile    = profile
    )

    # Generate all TTS audio in parallel (skipped when client uses browser TTS)
    if not skip_audio:
        def _tts_task(args):
            i, q_text = args
            return i, speak_question(q_text, i, session_id, speaker=tts_speaker)

        with ThreadPoolExecutor(max_workers=min(len(questions), 5)) as pool:
            tts_results = dict(pool.map(_tts_task, enumerate(questions, start=1)))
    else:
        tts_results = {}

    question_payload = []
    for i, q_text in enumerate(questions, start=1):
        audio_path = tts_results.get(i, "")
        audio_url  = f"/api/interview/audio/{os.path.basename(audio_path)}" if audio_path else None

        report.questions.append(QAEntry(
            question_number = i,
            question        = q_text,
            audio_file      = audio_path or ""
        ))
        question_payload.append({
            "number":    i,
            "text":      q_text,
            "audio_url": audio_url
        })

    _interview_sessions[session_id] = report

    return jsonify({
        "session_id":      session_id,
        "candidate_name":  report.candidate_name,
        "total_questions": len(questions),
        "questions":       question_payload
    })


# ── POST /api/interview/submit-answer ───────────────────────────────────────
# Multipart form:  session_id, question_number, audio (file)
# OR JSON body:    { session_id, question_number, text_answer }
@app.route('/api/interview/submit-answer', methods=['POST'])
def interview_submit_answer():
    if request.content_type and "multipart" in request.content_type:
        session_id      = request.form.get("session_id")
        question_number = int(request.form.get("question_number", 1))
        audio_file      = request.files.get("audio")
        text_answer     = None
    else:
        body            = request.get_json()
        session_id      = body.get("session_id")
        question_number = int(body.get("question_number", 1))
        audio_file      = None
        text_answer     = body.get("text_answer", "")

    if not session_id or session_id not in _interview_sessions:
        return jsonify({"error": "Invalid or expired session_id"}), 400

    report = _interview_sessions[session_id]

    entry = next((q for q in report.questions if q.question_number == question_number), None)
    if not entry:
        return jsonify({"error": f"Question {question_number} not found"}), 404

    # Transcribe audio or use text bypass
    stt_error = None
    if audio_file:
        orig_filename = audio_file.filename or "answer.wav"
        ext           = orig_filename.rsplit(".", 1)[-1] if "." in orig_filename else "wav"
        tmp_path      = os.path.join(AUDIO_DIR, f"{session_id}_ans{question_number}.{ext}")
        audio_file.save(tmp_path)
        fsize = os.path.getsize(tmp_path)
        print(f"[SubmitAnswer] Saved → {tmp_path}  ({fsize} bytes)")
        transcript, stt_error = transcribe_answer(tmp_path)
        if stt_error:
            print(f"[SubmitAnswer] STT error: {stt_error}")
    elif text_answer:
        transcript = text_answer
    else:
        transcript = ""

    evaluation = evaluate_answer(entry.question, transcript, report.raw_profile)

    entry.answer_transcript = transcript
    entry.evaluation        = evaluation

    return jsonify({
        "question_number": question_number,
        "transcript":      transcript,
        "stt_error":       stt_error,
        "evaluation":      evaluation
    })


# ── POST /api/interview/finalize ─────────────────────────────────────────────
# Body: { "session_id": "..." }
# Generates final LLM report and saves to DB
@app.route('/api/interview/finalize', methods=['POST'])
def interview_finalize():
    data       = request.get_json()
    session_id = data.get("session_id")

    if not session_id or session_id not in _interview_sessions:
        return jsonify({"error": "Invalid or expired session_id"}), 400

    report = _interview_sessions.pop(session_id)
    report = generate_final_report(report)

    # Persist to SQLite
    report_id = None 
    try:
        from sqlalchemy import text as sql_text
        db.session.execute(sql_text("""
            INSERT INTO interview_results
                (profile_url, candidate_name, interview_date,
                 overall_score, recommendation, summary, full_report_json)
            VALUES
                (:profile_url, :candidate_name, :interview_date,
                 :overall_score, :recommendation, :summary, :full_report_json)
        """), {
            "profile_url":      report.profile_url,
            "candidate_name":   report.candidate_name,
            "interview_date":   report.interview_date,
            "overall_score":    report.overall_score,
            "recommendation":   report.recommendation,
            "summary":          report.summary,
            "full_report_json": json.dumps(report.to_dict())
        })
        db.session.commit()

        row = db.session.execute(sql_text(
            "SELECT id FROM interview_results WHERE profile_url=:u ORDER BY id DESC LIMIT 1"
        ), {"u": report.profile_url}).fetchone()
        report_id = row[0] if row else None

    except Exception as e:
        print(f"[Interview] DB save error: {e}")

    return jsonify({
        "status":         "complete",
        "report_id":      report_id,
        "candidate_name": report.candidate_name,
        "overall_score":  report.overall_score,
        "recommendation": report.recommendation,
        "summary":        report.summary,
        "qa_breakdown": [
            {
                "question":     qa.question,
                "answer":       qa.answer_transcript,
                "score":        qa.evaluation.get("score"),
                "strengths":    qa.evaluation.get("strengths"),
                "improvements": qa.evaluation.get("improvements"),
                "red_flags":    qa.evaluation.get("red_flags", [])
            }
            for qa in report.questions
        ]
    })


# ── GET /api/interview/audio/<filename> ──────────────────────────────────────
# Serves WAV files generated by TTS
@app.route('/api/interview/audio/<filename>', methods=['GET'])
def interview_serve_audio(filename):
    filename = os.path.basename(filename)
    filepath = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Audio file not found"}), 404
    mime = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
    return send_file(filepath, mimetype=mime)


# ── GET /api/interview/report/<id> ───────────────────────────────────────────
# Fetch a saved report by its DB id
@app.route('/api/interview/report/<int:report_id>', methods=['GET'])
def interview_get_report(report_id):
    from sqlalchemy import text as sql_text
    row = db.session.execute(
        sql_text("SELECT full_report_json FROM interview_results WHERE id=:id"),
        {"id": report_id}
    ).fetchone()
    if not row:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(json.loads(row[0]))


# ── GET /api/interview/reports ───────────────────────────────────────────────
# List all reports, optionally filtered by profile_url
@app.route('/api/interview/reports', methods=['GET'])
def interview_list_reports():
    from sqlalchemy import text as sql_text
    profile_url = request.args.get("profile_url")

    if profile_url:
        rows = db.session.execute(sql_text("""
            SELECT id, candidate_name, interview_date, overall_score, recommendation, summary
            FROM interview_results WHERE profile_url=:u ORDER BY interview_date DESC
        """), {"u": profile_url}).fetchall()
    else:
        rows = db.session.execute(sql_text("""
            SELECT id, candidate_name, interview_date, overall_score, recommendation, summary
            FROM interview_results ORDER BY interview_date DESC LIMIT 50
        """)).fetchall()

    return jsonify([
        {
            "id":             r[0],
            "candidate_name": r[1],
            "interview_date": str(r[2]),
            "overall_score":  r[3],
            "recommendation": r[4],
            "summary":        r[5]
        }
        for r in rows
    ])


# ── GET /api/interview/health ─────────────────────────────────────────────────
@app.route('/api/interview/health', methods=['GET'])
def interview_health():
    return jsonify({
        "status":          "ok",
        "sarvam_key_set":  bool(os.getenv("SARVAM_API_KEY")),
        "hf_token_set":    bool(os.getenv("HF_TOKEN")),
        "active_sessions": len(_interview_sessions),
        "audio_dir":       AUDIO_DIR,
    })


# ── GET /api/interview/debug-stt ─────────────────────────────────────────────
# Open in browser to see raw Sarvam STT response on the latest recorded audio.
@app.route('/api/interview/debug-stt', methods=['GET'])
def interview_debug_stt():
    import glob
    wav_files = sorted(
        glob.glob(os.path.join(AUDIO_DIR, "*_ans*.wav")),
        key=os.path.getmtime, reverse=True
    )
    if not wav_files:
        return jsonify({"error": "No answer WAV files found in " + AUDIO_DIR})

    latest    = wav_files[0]
    key       = os.getenv("SARVAM_API_KEY", "")
    file_size = os.path.getsize(latest)

    if not key:
        return jsonify({"error": "SARVAM_API_KEY not set", "file": latest})

    try:
        with open(latest, "rb") as f:
            resp = requests.post(
                "https://api.sarvam.ai/speech-to-text",
                headers={"api-subscription-key": key},
                files={"file": (os.path.basename(latest), f, "audio/wav")},
                data={"language_code": "en-IN", "model": "saarika:v2", "with_timestamps": "false"},
                timeout=30
            )
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:500]

        return jsonify({
            "file":          latest,
            "file_size_kb":  round(file_size / 1024, 1),
            "http_status":   resp.status_code,
            "sarvam_response": body,
        })
    except Exception as e:
        return jsonify({"error": str(e), "file": latest})


# ════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)