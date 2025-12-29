# backend/main.py
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware  
import subprocess
import os

app = FastAPI()

# Enable CORS so your Quasar frontend (localhost:9000) can talk to this backend (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In production, specify the URL.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Module 1 Backend Online"}

# 1. API Endpoint to trigger the Extractor (Non-interactive)
@app.post("/run-extraction")
def run_extraction():
    # This runs the script in the background
    try:
        subprocess.Popen(["python", "extracter.py"])
        return {"message": "Extraction started successfully."}
    except Exception as e:
        return {"error": str(e)}

# 2. WebSocket Endpoint for Scraping (Interactive/Real-time)
@app.websocket("/ws/scrape")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Wait for the frontend to send the search criteria
    data = await websocket.receive_json()
    job_role = data.get('role')
    location = data.get('location')

    await websocket.send_text(f"INFO: Received command to scrape {job_role} in {location}")

    # Run scrapper.py as a subprocess
    # We use '-u' to force unbuffered python output so we see logs instantly
    process = subprocess.Popen(
        ["python", "-u", "scrapper.py", job_role, location],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    try:
        # Loop through the script's output line by line
        for line in process.stdout:
            # Send the log line to the frontend
            await websocket.send_text(line.strip())
            
        # Wait for process to finish
        process.wait()
        await websocket.send_text("DONE: Process completed.")
        await websocket.close()
        
    except Exception as e:
        await websocket.send_text(f"ERROR: {str(e)}")
        process.kill()