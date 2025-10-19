from flask import Flask, jsonify, request
from flask_cors import CORS
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import process_new_claim, verify_claim_with_gemini
import threading, time
import requests

app = Flask(__name__)
CORS(app)

# --- Mock DB ---
mock_db = {"alerts": []}

# --- API Endpoints ---
@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    return jsonify(mock_db["alerts"])

class Claim(BaseModel):
    claim: str
    source: str

app = FastAPI()

@app.post("/api/submit_claim")
async def submit_claim(claim: Claim):
    result = process_new_claim(claim.dict())
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["truth"])
    mock_db["alerts"].append(result)
    return result

# --- Background simulation ---
def simulate_claims():
    time.sleep(5)
    new_claims = [
        {"claim": "Cyclone has been upgraded to Category 4.", "source": "Messaging Apps"},
        {"claim": "Evacuation centers are being set up in Colaba schools.", "source": "BMC Official"},
        {"claim": "Government is hiding the real cyclone path!", "source": "Anonymous Forum"}
    ]
    for claim in new_claims:
        try:
            requests.post("http://127.0.0.1:8000/api/submit_claim", json=claim)
        except:
            print("Server not ready yet...")
        time.sleep(10)

if __name__ == '__main__':
    threading.Thread(target=simulate_claims, daemon=True).start()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
