import os
import re
import requests
import json
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "openai/gpt-oss-120b:free"

# Precise delimiters for robust long-form parsing
DELIM_LOC     = "<<<LOCATION>>>"
DELIM_SUMMARY = "<<<SUMMARY>>>"
DELIM_IEEE    = "<<<IEEE>>>"
DELIM_END     = "<<<END>>>"

def generate_research_brief(lat, lon, cnn_score, marine_data, final_label):
    """
    Calls OpenRouter to generate clean, professional technical narratives.
    Explicitly forbids redundant separators like '---'.
    """
    if not OPENROUTER_API_KEY:
        return {
            "location_name": "Regional Surveillance Point",
            "research_summary": "Intelligence Engine Offline. Analysis unavailable.",
            "ieee_report_body": "DATA UNAVAILABLE"
        }

    wind_ms = marine_data.get("wind_speed_ms", "N/A")
    sst = marine_data.get("temperature_c", "N/A")

    prompt = f"""
    Act as a Senior Satellite Intelligence Analyst. 
    Analyze this detection: {lat}N, {lon}E.
    CNN: {cnn_score}%. Wind: {wind_ms}m/s. SST: {sst}C. Verdict: {final_label}.

    STRICT FORMATTING (MANDATORY):
    1. Output exactly ONE deep technical paragraph for the summary.
    2. NO BULLET POINTS. NO HEADERS. NO BOLDING unless critical.
    3. ABSOLUTELY NO TRAILING DASHES OR SEPARATORS (e.g., No '---').
    4. Start immediately with text. End immediately with text.
    5. LOCATION NAME: Concise 2-line max identifier. NO SEPARATORS.

    OUTPUT STRUCTURE:

    {DELIM_LOC}
    [Summarized Geographic Subtitle - Clean text only, NO '---']

    {DELIM_SUMMARY}
    [Deep technical narrative paragraph - Clean text only, NO '---']

    {DELIM_IEEE}
    [Internal Technical Body]
    
    {DELIM_END}
    """

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            }),
            timeout=90
        )
        
        raw = response.json()['choices'][0]['message']['content']
        
        def extract(text, start, end):
            try:
                # Extract and strip redundant separators
                content = text.split(start)[1].split(end)[0].strip()
                return re.sub(r'---+$', '', content).strip()
            except:
                return None

        return {
            "location_name": extract(raw, DELIM_LOC, DELIM_SUMMARY) or f"Sector {lat}, {lon}",
            "research_summary": extract(raw, DELIM_SUMMARY, DELIM_IEEE) or "Synthesis failed.",
            "ieee_report_body": extract(raw, DELIM_IEEE, DELIM_END) or raw
        }
    except Exception as e:
        return {
            "location_name": f"Sector {lat}, {lon}",
            "research_summary": f"Uplink Error: {str(e)}",
            "ieee_report_body": "N/A"
        }
