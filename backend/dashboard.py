import requests
import pandas as pd
import altair as alt
import streamlit as st
from datetime import date

st.set_page_config(page_title="Activity Tracker", layout="wide")
st.title("Activity Tracker")

@st.cache_data(ttl=30)
def fetch_sessions(selected_date=None):
    if selected_date:
        return requests.get(f"http://backend:8000/sessions/summary?date={selected_date}").json()
    return requests.get("http://backend:8000/sessions/summary").json()

@st.cache_data(ttl=30)
def fetch_active_hours(selected_date=None):
    if selected_date:
        return requests.get(f"http://backend:8000/sessions/hourly?date={selected_date}").json()
    return requests.get("http://backend:8000/sessions/hourly").json()

def format_hour(h):
    if h == 0:
        return "12 AM"
    if 0 < h < 12:
        return f"{h} AM"
    if 12 < h < 24:
        return f"{h - 12} PM"
    return "12 PM"
    
tab1, tab2 = st.tabs(["Dashboard", "Rules"])

with tab1:
    show_all = st.checkbox("Show all time")
    if not show_all:
        selected_date = st.date_input("Filter by Date", value=date.today())
        session_list = fetch_sessions(selected_date)
        hourly_list = fetch_active_hours(selected_date)
    else:
        session_list = fetch_sessions()
        hourly_list = fetch_active_hours()
    hourly_dict = {int(r["hour"]): r["totalTime"] for r in hourly_list}

    def convert_time(timeSpent):
        if timeSpent < 60:
            return f"{timeSpent:.0f}s"
        elif timeSpent < 3600:
            return f"{timeSpent / 60:.1f} mins"
        return f"{timeSpent / 3600:.1f} hrs"

    def clean_sessions(sessions):
        return [{"title": s["title"], "url": s["url"], "reason": s["reason"], "timeSpent": convert_time(s["totalTime"])} for s in sessions]

    productive = [s for s in session_list if s["label"] and s["label"].lower() == "productive"]
    unproductive = [s for s in session_list if s["label"] and s["label"].lower() == "unproductive"]
    neutral = [s for s in session_list if s["label"] and s["label"].lower() == "neutral"]
    unclassified = [s for s in session_list if not s["label"]]

    productive_time = sum(s["totalTime"] for s in productive)
    unproductive_time = sum(s["totalTime"] for s in unproductive)
    neutral_time = sum(s["totalTime"] for s in neutral)
    unclassified_time = sum(s["totalTime"] for s in unclassified)

    sorted_session_list = sorted(session_list, key=lambda x: x["totalTime"], reverse=True)[:10]
    top_sites_data = pd.DataFrame({
        "Site": [s["url"] for s in sorted_session_list],
        "Time (mins)": [round(s["totalTime"] / 60, 1) for s in sorted_session_list]
    }).set_index("Site")

    chart = alt.Chart(top_sites_data.reset_index()).mark_bar().encode(
        x="Time (mins):Q",
        y=alt.Y("Site:N", sort="-x")
    )
    st.subheader("Top Sites by Time")
    st.altair_chart(chart, use_container_width=True)

    hours = list(range(24))
    hour_labels = [format_hour(h) for h in hours]
    times = [round(hourly_dict.get(h, 0) / 3600, 1) for h in hours]

    hourly_data = pd.DataFrame({
        "Hour": hour_labels,
        "Time (hrs)": times
    })

    st.subheader("Activity by Hour")
    chart = alt.Chart(hourly_data).mark_bar().encode(
        x=alt.X("Hour:N", sort=None),
        y="Time (hrs):Q"
    )
    st.altair_chart(chart, use_container_width=True)

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

    data = pd.DataFrame({
        "Category": ["Productive", "Unproductive", "Neutral", "Unclassified"],
        "Time (mins)": [round(productive_time / 60, 1), round(unproductive_time / 60, 1),
                        round(neutral_time / 60, 1), round(unclassified_time / 60, 1)]
    })
    
    chart_data = alt.Chart(data).mark_arc().encode(
        theta="Time (mins):Q",
        color=alt.Color("Category:N", scale=alt.Scale(
            domain=["Productive", "Unproductive", "Neutral", "Unclassified"],
            range=["#22c55e", "#ef4444", "#94a3b8", "#cbd5e1"]
        ))
    )
    st.subheader("Time Distribution")
    st.altair_chart(chart_data, use_container_width=True)

with tab2:
    st.subheader("Custom Rules")
    domain = st.text_input("URL/Domain")
    label = st.selectbox("Labels", ["productive", "unproductive", "neutral"])

    if st.button("Add Rule"):
        if not domain:
            st.warning("Please enter a domain")
        else:
            response = requests.post("http://backend:8000/rules", json={"domain": domain, "label": label})
            result = response.json()
            if result["status"] == "created":
                st.success("Rule added!")
            elif result["status"] == "already exists":
                st.warning("Rule already exists for this domain!")
            else:
                st.error("Something went wrong")

    st.divider()

    rules = requests.get("http://backend:8000/rules").json()

    for rule in rules:
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        col1.write(rule["domain"])
        col2.write(rule["label"])
        col3.write("Active" if rule["is_active"] else "Paused")

        if col4.button("Delete", key=f"del_{rule['id']}"):
            requests.delete(f"http://backend:8000/rules/{rule['id']}")
            st.rerun()
        if col4.button("Toggle", key=f"tog_{rule['id']}"):
            requests.patch(f"http://backend:8000/rules/{rule['id']}")
            st.rerun()
            