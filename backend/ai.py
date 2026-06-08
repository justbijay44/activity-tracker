import os
import json
import requests

AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").lower()

def set_provider(provider: str):
    global AI_PROVIDER
    AI_PROVIDER = provider.lower()

def get_provider():
    return AI_PROVIDER

def classify_sessions(sessions):
    prompt = build_prompt(sessions)

    if AI_PROVIDER == "ollama":
        return call_ollama(prompt)
    if AI_PROVIDER == "groq":
        return call_groq(prompt)
    if AI_PROVIDER == "gemini":
        return call_gemini(prompt)
    return call_ollama(prompt)

def build_prompt(sessions):
    prompt = f"""
        You are a JSON API. You must respond with ONLY a JSON array, no other text.

        Analyze these browser sessions and classify each one:
        {sessions}

        Return ONLY this JSON format, nothing else:
        [
            {{"title": "...", "url": "...", "label": "productive|unproductive|neutral", "reason": "..."}}
        ]

        Rules:
        - YouTube is UNPRODUCTIVE unless the title contains words like: tutorial, course, how to, learn, study, lecture, explained, guide
        - Social media (Facebook, Instagram, Twitter, TikTok) is always UNPRODUCTIVE
        - Gaming content, sports recaps, vlogs, entertainment is UNPRODUCTIVE
        - Development tools (GitHub, VS Code, FastAPI, Streamlit, documentation) are PRODUCTIVE
        - Browser internal pages (chrome://, about:) are NEUTRAL
        - If timeSpent is less than 30 seconds, label NEUTRAL
        - Return ONLY JSON, no extra text, no markdown
    """
    return prompt


def call_ollama(prompt):
    host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
    for attempt in range(3):
        response = requests.post(f"{host}/api/chat", json={
            "model": "mistral:7b",
            "messages": [{"role":"user", "content": prompt}],
            "stream": False
        })
        raw = response.json()["message"]["content"].strip()
        if raw:
            break
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

def call_groq(prompt):
    api_key = os.getenv("GROQ_API_KEY")
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0
        }
    )
    result = response.json()
    raw = response.json()["choices"][0]["message"]["content"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

def call_gemini(prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
        json={"contents": [{"parts": [{"text": prompt}]}]}
    )
    raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)