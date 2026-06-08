import requests
import pandas as pd
import streamlit as st
from datetime import date

st.set_page_config(page_title="Activity Tracker", layout="wide")
st.title("Activity Tracker")

current = requests.get("http://backend:8000/get-provider").json()["provider"]
provider = st.selectbox("AI Provider", ["ollama", "groq", "gemini"], index=["ollama", "groq", "gemini"].index(current)) 
if provider != current:
    requests.post(f"http://backend:8000/set-provider?provider={provider}")

show_all = st.checkbox("Show all time")
if not show_all:
    selected_date = st.date_input("Filter by Date", value=date.today())
    response = requests.get(f"http://backend:8000/sessions/summary?date={selected_date}")
else:
    response = requests.get("http://backend:8000/sessions/summary")

def convert_time(timeSpent):
    if timeSpent < 60:
        return f"{timeSpent:.0f}s"
    elif timeSpent < 3600:
        return f"{timeSpent / 60:.1f} mins"
    return f"{timeSpent / 3600:.1f} hrs"

def clean_sessions(sessions):
    return [{"title": s["title"], "url": s["url"], "reason": s["reason"], "timeSpent": convert_time(s["totalTime"])} for s in sessions]

session_list = response.json()

productive = [s for s in session_list if s["label"] == "productive"]
unproductive = [s for s in session_list if s["label"] == "unproductive"]

productive_time = sum(s["totalTime"] for s in productive)
unproductive_time = sum(s["totalTime"] for s in unproductive)

col1, col2 = st.columns(2)
col1.metric("Productive Time", convert_time(productive_time))
col2.metric("Unproductive Time", convert_time(unproductive_time))

productive_sorted = sorted(productive, key=lambda x: x["totalTime"], reverse=True)
unproductive_sorted = sorted(unproductive, key=lambda x: x["totalTime"], reverse=True)

def show_sessions_table(title, sessions):
    st.subheader(title)
    show_all = st.checkbox(f"Show all {title.lower()}", key=title)
    if show_all:
        st.table(clean_sessions(sessions))
    else:
        st.table(clean_sessions(sessions[:5]))

show_sessions_table("Productive Sessions", productive_sorted)
show_sessions_table("Unproductive Sessions", unproductive_sorted)

chart_data = pd.DataFrame({
    "Category": ["Productive", "Unproductive"],
    "Time (mins)": [round(productive_time / 60, 1), round(unproductive_time / 60, 1)]
}).set_index("Category")

st.subheader("Productive vs Unproductive")
st.bar_chart(chart_data)