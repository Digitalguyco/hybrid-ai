from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os
from dotenv import load_dotenv
from groq import Groq

# Load Groq API key from .env
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

class SiteCheckRequest(BaseModel):
    target: str

@app.post("/check_site")
async def check_site(data: SiteCheckRequest):
    target = data.target.strip()

    if not target.startswith("http"):
        target = "http://" + target

    # 1. Run security tools
    try:
        port_scan = subprocess.getoutput(f"nmap -Pn -T4 --top-ports 10 {target}")
        tech_stack = subprocess.getoutput(f"whatweb {target}")
        headers = subprocess.getoutput(f"curl -I {target}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool execution error: {e}")

    # 2. Summarize with Groq Mixtral
    combined_output = f"""
    Port Scan:
    {port_scan}

    Technology Fingerprint:
    {tech_stack}

    HTTP Headers:
    {headers}
    """

    summary_prompt = f"""
    You are an AI security analyst. Analyze the following scan results and generate a basic website security report.

    {combined_output}

    Include observations on:
    - Open ports
    - Web technologies
    - Security headers
    - Potential vulnerabilities
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": summary_prompt}]
        )
        ai_summary = response.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API error: {e}")

    return {
        "ai_summary": ai_summary,
        "raw_output": {
            "nmap": port_scan,
            "whatweb": tech_stack,
            "curl_headers": headers
        }
    }
