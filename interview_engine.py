import requests
import chromadb

# ===============================
# CONFIG
# ===============================

OLLAMA_CHAT = "http://localhost:11434/api/chat"
OLLAMA_EMBED = "http://localhost:11434/api/embeddings"

LLM_MODEL = "CobaltPulse/Qwen2.5-VL-7B-Instruct:latest"
EMBED_MODEL = "qwen3-embedding"

ROUNDS = 3

# Vector DB
client = chromadb.PersistentClient(path="./vector_db")
collection = client.get_collection("resume_chunks")

conversation_history = []

# ===============================
# EMBEDDING
# ===============================

def embed_query(text):

    payload = {
        "model": EMBED_MODEL,
        "prompt": text
    }

    r = requests.post(OLLAMA_EMBED, json=payload)

    if r.status_code != 200:
        raise Exception("Embedding failed")

    return r.json()["embedding"]


# ===============================
# RETRIEVAL
# ===============================

def retrieve_resume_context(query, k=5):

    embedding = embed_query(query)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=k
    )

    docs = results["documents"][0]

    return "\n".join(docs)


# ===============================
# GENERATE QUESTION
# ===============================

def generate_question(context, topic):

    system_prompt = """
You are a senior technical interviewer.

Generate ONE interview question based on the candidate resume.

If previous conversation exists, ask a follow-up question.
"""

    messages = [{"role": "system", "content": system_prompt}]

    messages.extend(conversation_history)

    messages.append({
        "role": "user",
        "content": f"""
Candidate Resume Context:

{context}

Interview Topic: {topic}

Ask ONE interview question.
"""
    })

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7}
    }

    r = requests.post(OLLAMA_CHAT, json=payload)

    if r.status_code != 200:
        raise Exception("LLM request failed")

    return r.json()["message"]["content"]


# ===============================
# EVALUATE ANSWER
# ===============================

def evaluate_answer(question, answer):

    system_prompt = """
You are a technical interviewer evaluating a candidate answer.

Return structured feedback.
"""

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""
Question:
{question}

Candidate Answer:
{answer}

Evaluate:

Return format:

Score: /10
Strengths:
Weaknesses:
Suggested improvement:
"""
            }
        ],
        "stream": False,
        "options": {"temperature": 0.3}
    }

    r = requests.post(OLLAMA_CHAT, json=payload)

    return r.json()["message"]["content"]


# ===============================
# INTERVIEW LOOP
# ===============================

def run_interview(topic):

    context = retrieve_resume_context(topic)

    print("\n📚 Resume Context Loaded\n")

    for round_num in range(1, ROUNDS + 1):

        print(f"\n==========================")
        print(f"ROUND {round_num}")
        print(f"==========================")

        question = generate_question(context, topic)

        print("\n🎤 Question:\n")
        print(question)

        answer = input("\n💬 Your Answer: ")

        evaluation = evaluate_answer(question, answer)

        print("\n📊 Evaluation:\n")
        print(evaluation)

        # store conversation
        conversation_history.append(
            {"role": "assistant", "content": question}
        )

        conversation_history.append(
            {"role": "user", "content": answer}
        )


# ===============================
# RUN
# ===============================

if __name__ == "__main__":

    topic = input("Enter interview topic: ")

    run_interview(topic)