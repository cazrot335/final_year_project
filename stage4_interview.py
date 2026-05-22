"""
stage4_interview.py  —  Interview Module
"""

import os, json, requests
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

# ── Static config ─────────────────────────────────────────────────────────────
SARVAM_TTS_URL    = "https://api.sarvam.ai/text-to-speech/stream"
SARVAM_STT_URL    = "https://api.sarvam.ai/speech-to-text"
TTS_MODEL         = "bulbul:v3"
TTS_DEFAULT_SPEAKER = "sumit"
HF_API_URL        = "https://router.huggingface.co/v1/chat/completions"
LLM_MODEL         = "Qwen/Qwen2.5-72B-Instruct"

AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interview_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# ── Live key helpers (never frozen at import) ─────────────────────────────────
def _sarvam_key(): return os.getenv("SARVAM_API_KEY", "")
def _hf_token():   return os.getenv("HF_TOKEN", "")
def _tts_lang():   return os.getenv("SARVAM_LANGUAGE", "en-IN")


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class QAEntry:
    question_number: int
    question: str
    answer_transcript: str = ""
    evaluation: dict = field(default_factory=dict)
    audio_file: str = ""

@dataclass
class InterviewReport:
    candidate_name: str
    profile_url: str
    interview_date: str
    questions: List[QAEntry] = field(default_factory=list)
    overall_score: float = 0.0
    recommendation: str = ""
    summary: str = ""
    raw_profile: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


# ── LLM call ──────────────────────────────────────────────────────────────────

def _llm_call(system: str, user: str) -> str:
    token = _hf_token()
    if not token:
        raise ValueError("HF_TOKEN not set")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
        "stream": False
    }
    resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=90)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()
    return content


# ── Step 1: Question generation ───────────────────────────────────────────────

def _build_profile_context(profile: dict) -> str:
    """
    Build a rich, structured context string from the normalized profile
    so the LLM has full detail to generate specific technical questions.
    """
    lines = []
    lines.append(f"Name       : {profile.get('name', '')}")
    lines.append(f"Headline   : {profile.get('headline', '')}")
    lines.append(f"Location   : {profile.get('address', '')}")

    skills = profile.get("skills", [])
    if skills:
        lines.append(f"\nTechnical Skills ({len(skills)} total):")
        lines.append("  " + ", ".join(str(s) for s in skills))

    exp_list = profile.get("experience", [])
    if exp_list:
        lines.append(f"\nWork Experience ({len(exp_list)} roles):")
        for e in exp_list:
            lines.append(f"  • {e.get('role','?')} at {e.get('company','?')}  [{e.get('duration','')}]")
            if e.get("description"):
                lines.append(f"    {e['description'][:200]}")

    edu_list = profile.get("education", [])
    if edu_list:
        lines.append(f"\nEducation:")
        for e in edu_list:
            lines.append(f"  • {e.get('degree','?')} — {e.get('institution','?')}  [{e.get('years','')}]")

    if profile.get("feedback"):
        lines.append(f"\nProfile Summary: {profile['feedback'][:300]}")

    return "\n".join(lines)


def generate_questions(profile: dict, num_questions: int = 5) -> List[str]:
    """
    Generate intern-level interview questions — friendly, beginner-appropriate,
    referencing the candidate's actual skills and background.
    """
    context = _build_profile_context(profile)

    system = """You are a friendly hiring manager interviewing a fresher or intern candidate.
Your goal is to make the candidate comfortable while checking their basic understanding.

RULES:
- Questions must be EASY — suitable for a fresher, recent graduate, or intern
- Avoid architecture, system design, production-scale, or senior-level topics
- Focus on: basic concept understanding, what they learned in college/projects,
  tools they have listed, simple how-would-you-approach scenarios
- Tone must be warm and encouraging — not intimidating
- Reference their actual skills/tools so questions feel personal, not generic
- Do NOT ask about distributed systems, microservices, performance optimization,
  or anything requiring years of industry experience
- Return ONLY valid JSON: {"questions": ["q1", "q2", ...]}"""

    basic_count  = max(2, round(num_questions * 0.5))   # basic concept checks
    project_count = max(1, round(num_questions * 0.3))  # about their own projects/education
    soft_count   = num_questions - basic_count - project_count  # learning mindset

    user = f"""Generate exactly {num_questions} intern/fresher-level interview questions.

Distribution:
- {basic_count} basic concept questions (simple definitions, how does X work, what is Y)
  based on skills they have listed — ask at a textbook / tutorial level
- {project_count} questions about their own projects or education background
  (what did you build, what did you learn, what tools did you use)
- {soft_count} learning/growth questions (how do you learn new things, what interests you)

Difficulty level: A student who has done 1-2 small projects should be able to answer these.
Keep each question to 1-2 sentences. No trick questions.

Candidate Profile:
{context}

Remember: Intern level — keep it simple, encouraging, and specific to their background."""

    try:
        raw = _llm_call(system, user)
        parsed = json.loads(raw)
        questions = parsed.get("questions", [])
        if not questions:
            raise ValueError("Empty questions list")
        return questions[:num_questions]
    except Exception as e:
        print(f"[InterviewModule] Question generation failed: {e}")
        skills  = profile.get("skills", ["programming"])
        edu     = profile.get("education", [{}])
        degree  = edu[0].get("degree", "your degree") if edu else "your degree"
        skill0  = skills[0] if skills else "your main skill"
        skill1  = skills[1] if len(skills) > 1 else skill0
        return [
            f"Can you explain what {skill0} is and how you first learned it?",
            f"Tell me about a small project you built using {skill1}.",
            f"What was the most interesting thing you studied in {degree}?",
            f"How do you usually debug a problem when something isn't working?",
            f"What would you like to learn more about in your first internship?"
        ][:num_questions]


# ── Step 2: TTS ───────────────────────────────────────────────────────────────

def speak_question(text: str, question_number: int, session_id: str,
                   speaker: str = "") -> str:
    key = _sarvam_key()
    if not key:
        print("[TTS] SARVAM_API_KEY not set — skipping")
        return ""

    chosen_speaker = speaker or TTS_DEFAULT_SPEAKER
    headers = {"api-subscription-key": key, "Content-Type": "application/json"}
    payload = {
        "text":                 text,
        "target_language_code": _tts_lang(),
        "speaker":              chosen_speaker,
        "model":                TTS_MODEL,
        "pace":                 1.1,
        "speech_sample_rate":   22050,
        "output_audio_codec":   "mp3",
        "enable_preprocessing": True,
    }

    print(f"[TTS] Q{question_number} | speaker={chosen_speaker} model={TTS_MODEL}")

    try:
        filename = f"{session_id}_q{question_number}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        with requests.post(SARVAM_TTS_URL, headers=headers, json=payload,
                           stream=True, timeout=30) as resp:
            if not resp.ok:
                print(f"[TTS] HTTP {resp.status_code} — {resp.text[:300]}")
                resp.raise_for_status()

            total = 0
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)

        print(f"[TTS] Saved → {filepath}  ({total} bytes)")
        return filepath

    except Exception as e:
        print(f"[TTS] Failed for Q{question_number}: {type(e).__name__}: {e}")
        return ""


# ── Step 3: STT ───────────────────────────────────────────────────────────────

def _detect_mime(path: str) -> str:
    """Detect actual audio MIME type from file header bytes."""
    try:
        with open(path, "rb") as f:
            header = f.read(16)
        if header[:4] == b"RIFF":
            return "audio/wav"
        if header[:4] == b"OggS":
            return "audio/ogg"
        if header[:3] == b"ID3" or header[:2] == b"\xff\xfb":
            return "audio/mpeg"
        # webm / matroska magic: 0x1A 0x45 0xDF 0xA3
        if header[:4] == b"\x1a\x45\xdf\xa3":
            return "audio/webm"
        # fallback — browser MediaRecorder usually produces webm
        return "audio/webm"
    except Exception:
        return "audio/webm"


def transcribe_answer(audio_path: str) -> tuple:
    """Returns (transcript: str, error: str|None)."""
    key = _sarvam_key()
    if not key:
        return "", "SARVAM_API_KEY not set"
    if not os.path.exists(audio_path):
        return "", f"Audio file not found: {audio_path}"

    file_size = os.path.getsize(audio_path)
    mime      = _detect_mime(audio_path)
    ext       = {"audio/wav": "wav", "audio/ogg": "ogg",
                 "audio/mpeg": "mp3", "audio/webm": "webm"}.get(mime, "webm")
    fname     = os.path.basename(audio_path).rsplit(".", 1)[0] + "." + ext

    print(f"[STT] Transcribing {audio_path}  size={file_size}b  mime={mime}  fname={fname}")

    if file_size < 1000:
        return "", "Audio too short (< 1 KB) — recording may be empty"

    headers = {"api-subscription-key": key}
    try:
        with open(audio_path, "rb") as f:
            files = {"file": (fname, f, mime)}
            data  = {
                "language_code":   _tts_lang(),
                "model":           "saarika:v2.5",
                "with_timestamps": "false"
            }
            resp = requests.post(SARVAM_STT_URL, headers=headers,
                                 files=files, data=data, timeout=60)

        print(f"[STT] HTTP {resp.status_code}  body={resp.text[:400]}")

        if not resp.ok:
            return "", f"Sarvam HTTP {resp.status_code}: {resp.text[:200]}"

        result = resp.json()
        # Sarvam may return "transcript" or "text" depending on model version
        transcript = (result.get("transcript") or result.get("text") or "").strip()
        print(f"[STT] Transcript ({len(transcript)} chars): {transcript[:120]}")

        if not transcript:
            return "", f"Sarvam returned empty transcript. Full response: {json.dumps(result)[:300]}"

        return transcript, None

    except Exception as e:
        return "", f"{type(e).__name__}: {e}"


# ── Step 4: Answer evaluation ─────────────────────────────────────────────────

def evaluate_answer(question: str, answer: str, profile: dict) -> dict:
    if not answer.strip():
        return {"score": 0, "relevance": "low", "strengths": "No answer provided.",
                "improvements": "Candidate did not respond.", "red_flags": ["no_answer"]}

    system = (
        "You are a friendly hiring manager evaluating an intern/fresher candidate. "
        "Be encouraging — this is entry-level, not a senior role. "
        'Return ONLY JSON: {"score":0,"relevance":"high|medium|low","strengths":"...","improvements":"...","red_flags":[]}\n'
        "score 0-10: basic understanding=6, good textbook answer=7-8, clear with example=9-10, wrong/no effort=1-3. "
        "Only add red_flags for factually wrong or zero-effort answers. "
        "strengths must always find something positive. improvements must be gentle suggestions."
    )
    user = (
        f"Candidate: {profile.get('name')}\n"
        f"Skills: {', '.join(str(s) for s in profile.get('skills', []))}\n"
        f"Experience: {json.dumps(profile.get('experience', []), indent=2)}\n\n"
        f"Question: {question}\n\nAnswer: {answer}"
    )
    try:
        return json.loads(_llm_call(system, user))
    except Exception as e:
        print(f"[Eval] Failed: {e}")
        return {"score": 5, "relevance": "medium", "strengths": "Could not evaluate.",
                "improvements": "N/A", "red_flags": []}


# ── Step 5: Final report ──────────────────────────────────────────────────────

def generate_final_report(report: InterviewReport) -> InterviewReport:
    qa_summary = [{"question": qa.question, "answer": qa.answer_transcript,
                   "score": qa.evaluation.get("score", 0)} for qa in report.questions]

    system = (
        "You are a senior hiring manager. Return ONLY JSON:\n"
        '{"overall_score":0.0,"recommendation":"Strong Hire|Hire|Hold|Reject","summary":"2-3 sentences"}'
    )
    user = (
        f"Candidate: {report.candidate_name}\n"
        f"Q&A:\n{json.dumps(qa_summary, indent=2)}\n\n"
        "Give overall_score (0-100), recommendation, and summary."
    )
    try:
        result = json.loads(_llm_call(system, user))
        report.overall_score  = float(result.get("overall_score", 0))
        report.recommendation = result.get("recommendation", "Hold")
        report.summary        = result.get("summary", "")
    except Exception as e:
        print(f"[Report] Final generation failed: {e}")
        scores = [qa.evaluation.get("score", 0) for qa in report.questions]
        report.overall_score  = (sum(scores) / len(scores) * 10) if scores else 0
        report.recommendation = "Hold"
        report.summary        = "Automated scoring used due to LLM error."
    return report


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_interview(profile: dict, answer_audio_paths: Optional[List[str]] = None,
                  num_questions: int = 5) -> InterviewReport:
    session_id = (f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_"
                  f"{profile.get('name','unknown').replace(' ','_')}")

    report = InterviewReport(
        candidate_name = profile.get("name", "Unknown"),
        profile_url    = profile.get("profile_url", ""),
        interview_date = datetime.utcnow().isoformat(),
        raw_profile    = profile
    )

    print(f"\n[Interview] Starting for {report.candidate_name}")
    print(f"[Interview] Profile context:\n{_build_profile_context(profile)}\n")

    questions = generate_questions(profile, num_questions)

    for i, q_text in enumerate(questions, start=1):
        print(f"\n── Q{i}/{len(questions)} ──")
        audio_path        = speak_question(q_text, i, session_id)
        answer_transcript = ""
        if answer_audio_paths and i - 1 < len(answer_audio_paths):
            answer_transcript, _ = transcribe_answer(answer_audio_paths[i - 1])
        evaluation = evaluate_answer(q_text, answer_transcript, profile)
        report.questions.append(QAEntry(
            question_number=i, question=q_text,
            answer_transcript=answer_transcript,
            evaluation=evaluation, audio_file=audio_path
        ))
        print(f"Score: {evaluation.get('score','?')}/10")

    report = generate_final_report(report)
    print(f"\n[Interview] Done — {report.overall_score:.1f}/100 | {report.recommendation}")
    return report