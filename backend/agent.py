import time
import requests
import os
GEMINI_API_KEY = "AIzaSyAh2-zBZpOdM2U-E1YPx6HUz0Iv-v1PVqk"

def detect_misinformation(claim_text: str) -> float:
    """
    Analyzes a claim for common markers of misinformation.
    Returns a score between 0 and 1.
    """
    print(f"  [AI] Analyzing claim for misinformation markers: '{claim_text}'")
    score = 0.1
    # Increase score for sensationalist language
    if "!" in claim_text or "BREAKING" in claim_text.upper():
        score += 0.3
    # Increase score for keywords suggesting conspiracy or secrecy
    if any(word in claim_text.lower() for word in ["cover-up", "hiding", "secret", "they don't want you to know"]):
        score += 0.4
    # Decrease score for keywords suggesting official sources
    if "official" in claim_text.lower() or "confirmed" in claim_text.lower():
        score -= 0.2
    
    score = max(0, min(1, score)) # Ensure score is between 0 and 1
    print(f"  [AI] Misinformation score: {score:.2f}")
    return score

def verify_claim_with_gemini(claim_text: str):
    """
    Sends the claim to the Google Gemini API for dynamic fact-checking.
    """
    if not GEMINI_API_KEY:
        return {"status": "error", "truth": "Gemini API key is not configured. Please set the GEMINI_API_KEY environment variable."}

    # The official endpoint for Gemini Flash model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={GEMINI_API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    # --- CORRECTED PAYLOAD STRUCTURE ---
    payload = {
        "contents": [{
            "parts": [{
                "text": f"Fact-check the following claim and provide a concise, clear explanation of whether it is true, false, or unverified. Claim: \"{claim_text}\""
            }]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status() 
        
        data = response.json()
        
        # Safely access the nested text output
        text_output = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No explanation provided.")
        
        # Simple logic to determine status from Gemini's response
        if "true" in text_output.lower():
            status = "true"
        elif "false" in text_output.lower():
            status = "false"
        else:
            status = "unverified"
            
        return {"status": status, "truth": text_output}

    except requests.exceptions.HTTPError as http_err:
        print(f"  [AGENT-ERROR] HTTP error occurred: {http_err} - {response.text}")
        return {"status": "error", "truth": f"Error interacting with Gemini API: {response.text}"}
    except Exception as e:
        print(f"  [AGENT-ERROR] An unexpected error occurred: {e}")
        return {"status": "error", "truth": f"An unexpected error occurred: {str(e)}"}

def process_new_claim(claim_data: dict) -> dict:
    """
    Processes a new claim by scoring it and, if necessary, verifying it with Gemini.
    """
    print(f"\n--- [AGENT] Processing claim from '{claim_data['source']}' ---")
    misinfo_score = detect_misinformation(claim_data['claim'])
    
    truth_text = "Low probability of misinformation; monitoring..."
    status = "unverified" # Default status
    
    # If score is high, trigger Gemini verification
    if misinfo_score > 0.4:
        print("  [AGENT] High misinformation score. Engaging Gemini API for verification.")
        verification_result = verify_claim_with_gemini(claim_data['claim'])
        status = verification_result['status']
        truth_text = verification_result['truth']
    else:
        print("  [AGENT] Low misinformation score. Monitoring claim.")
    
    return {
        "claim": claim_data['claim'],
        "status": status,
        "truth": truth_text,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": claim_data['source']
    }
# Function to call the Gemini Text API for the frontend
def call_gemini_text_api(prompt: str, is_grounded: bool = False, system_instruction: str = None) -> dict:
    if not GEMINI_API_KEY:
        return {"status": "error", "text": "Gemini API key is not configured."}

    # Using the same model as intended in the frontend (or your preferred version)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={GEMINI_API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    contents = [{"parts": [{"text": prompt}]}]
    payload = {"contents": contents}
    
    if is_grounded:
        payload["tools"] = [{"google_search": {}}]
    if system_instruction:
        payload["config"] = {"systemInstruction": system_instruction}
        
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status() 
        data = response.json()
        
        text_output = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response from AI.")
        
        return {"status": "success", "text": text_output}

    except requests.exceptions.HTTPError as http_err:
        print(f"  [PROXY-ERROR] HTTP error occurred: {http_err} - {response.text}")
        return {"status": "error", "text": f"Error calling Gemini Text API: {response.text}"}
    except Exception as e:
        print(f"  [PROXY-ERROR] An unexpected error occurred in text proxy: {e}")
        return {"status": "error", "text": f"An unexpected error occurred: {str(e)}"}

# Function to call the Imagen API for the frontend
def call_gemini_image_api(prompt: str) -> dict:
    if not GEMINI_API_KEY:
        return {"status": "error", "image_url": None}

    # Endpoint for Imagen
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={GEMINI_API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "instances": [{"prompt": prompt}], 
        "parameters": {"sampleCount": 1}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status() 
        data = response.json()
        
        # Safely extract the base64 image data
        image_base64 = data.get("predictions", [{}])[0].get("bytesBase64Encoded")
        
        if image_base64:
            # Return the image as a data URL for the frontend
            image_url = f"data:image/png;base64,{image_base64}"
            return {"status": "success", "image_url": image_url}
        else:
            return {"status": "error", "image_url": None}

    except requests.exceptions.HTTPError as http_err:
        print(f"  [PROXY-ERROR] HTTP error occurred: {http_err} - {response.text}")
        return {"status": "error", "image_url": None}
    except Exception as e:
        print(f"  [PROXY-ERROR] An unexpected error occurred in image proxy: {e}")
        return {"status": "error", "image_url": None}
