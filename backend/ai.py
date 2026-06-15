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
        You are a JSON API. Respond with ONLY a JSON array, no other text, no markdown.

        Classify these browser sessions:
        {json.dumps(sessions)}

        Output format:
        [{{"title": "...", "url": "...", "label": "productive|unproductive|neutral", "reason": "one sentence"}}]

        Examples:
        Input: [{{"title": "How to Make Sourdough Bread - Full Guide", "url": "youtube.com", "timeSpent": 600}}]
        Output: [{{"title": "How to Make Sourdough Bread - Full Guide", "url": "youtube.com", "label": "productive", "reason": "Educational tutorial content"}}]

        Input: [{{"title": "Funny Cat Compilation 2024", "url": "youtube.com", "timeSpent": 300}}]
        Output: [{{"title": "Funny Cat Compilation 2024", "url": "youtube.com", "label": "unproductive", "reason": "Entertainment content"}}]

        - label must be exactly one of: "productive", "unproductive", "neutral" (always lowercase)
        
        Classification rules (apply in this order):
        1. timeSpent < 30 seconds → NEUTRAL, reason: "Short visit"
        2. chrome://, about:, extensions → NEUTRAL, reason: "Browser internal page"
        3. localhost, 127.0.0.1 → PRODUCTIVE, reason: "Local development"
        4. GitHub, VS Code, FastAPI, Streamlit, claude.ai, chatgpt.com, stackoverflow.com, docs.* → PRODUCTIVE
        5. Facebook, Instagram, Twitter, TikTok, reddit.com → UNPRODUCTIVE
        6. chess.com, gaming sites, sports recap sites → UNPRODUCTIVE
        7. YouTube with title containing tutorial/course/how to/learn/study/lecture/guide → PRODUCTIVE
        8. YouTube entertainment, music, vlogs → UNPRODUCTIVE
        9. News, Wikipedia, general browsing → NEUTRAL
        10. Work/study related content → PRODUCTIVE

        Return ONLY the JSON array.
        """
    return prompt

def call_ollama(prompt):
    host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
    raw = ""
    for attempt in range(3):
        response = requests.post(f"{host}/api/chat", json={
            "model": "mistral:7b",
            "messages": [{"role":"user", "content": prompt}],
            "stream": False,
            "options": {
                "temperature": 0
            }
        })
        raw = response.json()["message"]["content"].strip()
        if raw:
            break

    if not raw:
        raise ValueError("Ollama returned empty response after 3 attempts")
    
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