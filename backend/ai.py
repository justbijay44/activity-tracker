import json
import requests

def classify_sessions(sessions):
    prompt = f"""
        You are a productivity analyzer.

        Analyze these browser sessions and classify each one:
        {sessions}

        For each session return a JSON array where each item has:
        - "title": the tab title
        - "url": the url
        - "label": must be exactly one of: "productive", "unproductive", "neutral"
        - "reason": a short one sentence explanation of why classified it that way

        Rules:
        - YouTube is UNPRODUCTIVE unless the title contains words like: tutorial, course, how to, learn, study, lecture, explained, guide
        - Social media (Facebook, Instagram, Twitter, TikTok) is always UNPRODUCTIVE
        - Gaming content, sports recaps, vlogs, entertainment is UNPRODUCTIVE
        - Development tools (GitHub, VS Code, FastAPI, Streamlit, documentation) are PRODUCTIVE
        - Browser internal pages (chrome://, about:) are NEUTRAL
        - If timeSpent is less than 30 seconds, label NEUTRAL
        - Return ONLY JSON, no extra text, no markdown
    """

    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "qwen2.5-coder:7b",
        "prompt": prompt,
        "stream": False
    })

    result = response.json()
    raw = result["response"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(raw)
    return parsed

if __name__ == "__main__":
    test_sessions = [
        {"title": "GitHub - fixing auth bug", "url": "https://github.com", "timeSpent": 45.5},
        {"title": "Instagram", "url": "https://instagram.com", "timeSpent": 120.0}
    ]
    classify_sessions(test_sessions)