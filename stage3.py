import os
import re
import json
import requests
from docling.document_converter import DocumentConverter
import chromadb

# -----------------------------
# CONFIG
# -----------------------------

OLLAMA_CHAT = "http://localhost:11434/api/chat"
OLLAMA_EMBED = "http://localhost:11434/api/embeddings"

PARSER_MODEL = "CobaltPulse/Qwen2.5-VL-7B-Instruct:latest"
EMBED_MODEL = "qwen3-embedding:latest"

CHROMA_PATH = "./vector_db"

# -----------------------------
# CLEAN JSON
# -----------------------------

def clean_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


# -----------------------------
# PDF → MARKDOWN
# -----------------------------

def convert_pdf_to_markdown(pdf_path):

    print("📄 Converting PDF → Markdown")

    converter = DocumentConverter()

    result = converter.convert(pdf_path)

    markdown = result.document.export_to_markdown()

    return markdown


# -----------------------------
# RESUME PARSER
# -----------------------------

def parse_resume_with_llm(markdown):

    system_prompt = """
You are an expert resume parser.
Return ONLY valid JSON.

Format:
{
  "name": "",
  "email": "",
  "phone": "",
  "profile_link": [],
  "address": "",
  "skills": [],
  "education": [],
  "experience": [
    {
      "company": "",
      "role": "",
      "duration": "",
      "description": ""
    }
  ]
}
"""

    payload = {
        "model": PARSER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": markdown}
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_ctx": 8192
        }
    }

    print("🧠 Parsing resume with local LLM")

    response = requests.post(OLLAMA_CHAT, json=payload)

    response.raise_for_status()

    data = response.json()

    content = data["message"]["content"]

    return clean_json(content)


# -----------------------------
# CHUNKING
# -----------------------------

def chunk_resume(resume):

    chunks = []

    candidate = resume.get("name", "unknown").lower().replace(" ", "_")

    # profile
    profile_text = f"""
Candidate {resume.get('name')}
Email {resume.get('email')}
Phone {resume.get('phone')}
Address {resume.get('address')}
"""

    chunks.append({
        "candidate_id": candidate,
        "section": "profile",
        "text": profile_text.strip()
    })

    # skills
    for skill in resume.get("skills", []):

        text = f"{skill['category']}: {', '.join(skill['items'])}"

        chunks.append({
            "candidate_id": candidate,
            "section": "skills",
            "text": text
        })

    # education
    for edu in resume.get("education", []):

        text = f"{edu['degree']} from {edu['institution']} GPA {edu.get('gpa','')}"

        chunks.append({
            "candidate_id": candidate,
            "section": "education",
            "text": text
        })

    # experience
    for exp in resume.get("experience", []):

        text = f"""
Role: {exp['role']}
Company: {exp['company']}
Duration: {exp['duration']}
Description: {exp['description']}
"""

        chunks.append({
            "candidate_id": candidate,
            "section": "experience",
            "text": text.strip()
        })

    return chunks


# -----------------------------
# EMBEDDINGS (OLLAMA)
# -----------------------------

def generate_embeddings(texts):

    embeddings = []

    for text in texts:

        payload = {
            "model": EMBED_MODEL,
            "prompt": text
        }

        response = requests.post(OLLAMA_EMBED, json=payload)

        response.raise_for_status()

        data = response.json()

        embeddings.append(data["embedding"])

    return embeddings


# -----------------------------
# STORE VECTOR DB
# -----------------------------

def store_chunks(chunks):

    print("📦 Generating embeddings using Qwen3...")

    texts = [c["text"] for c in chunks]

    embeddings = generate_embeddings(texts)

    print("🗄️ Storing vectors in ChromaDB")

    client = chromadb.PersistentClient(path=CHROMA_PATH)

    collection = client.get_or_create_collection("resume_chunks")

    for i, chunk in enumerate(chunks):

        collection.add(
            ids=[f"{chunk['candidate_id']}_{i}"],
            embeddings=[embeddings[i]],
            documents=[chunk["text"]],
            metadatas=[{
                "candidate": chunk["candidate_id"],
                "section": chunk["section"]
            }]
        )

    print("✅ Resume stored successfully")


# -----------------------------
# PIPELINE
# -----------------------------

def process_resume(pdf_path):

    markdown = convert_pdf_to_markdown(pdf_path)

    json_data = parse_resume_with_llm(markdown)

    resume_dict = json.loads(json_data)

    chunks = chunk_resume(resume_dict)

    store_chunks(chunks)

    return markdown, resume_dict, chunks


# -----------------------------
# RUN
# -----------------------------

if __name__ == "__main__":

    print("🚀 Resume ingestion pipeline starting")

    input_file = "resume.pdf"

    if not os.path.exists(input_file):

        print("❌ resume.pdf not found")

    else:

        markdown, resume_json, chunks = process_resume(input_file)

        print("\n📄 Markdown Preview:\n")

        print(markdown[:400])

        print("\n📊 Parsed Resume JSON:\n")

        print(json.dumps(resume_json, indent=2))

        print("\n📦 Generated Chunks:\n")

        for c in chunks:

            print(c)

            print("-" * 50)