import streamlit as st
import pandas as pd

from pipeline.ingestion import load_usage_logs, load_schedule
from pipeline.silence_detection import mark_silence_windows
from pipeline.baseline import compute_silence_baseline
from pipeline.anomaly import detect_shadow_waste
from pipeline.decision import generate_decision


st.set_page_config(
    page_title="Shadow Nirikshan Engine",
    layout="wide"
)

st.title("🌑 Shadow Nirikshan Engine")
st.subheader("Detecting Invisible Resource Waste During Inactivity")

st.markdown(
    """
    Shadow Nirikshan Engine is a **scheduled decision-support system**  
    that detects *water and electricity waste* occurring during **periods of inactivity**.
    """
)

st.divider()

# Sidebar
st.sidebar.header("Demo Controls")
use_demo_data = st.sidebar.checkbox("Use demo data", value=True)
run_analysis = st.sidebar.button("▶ Run Analysis Cycle")

# Data loading
if use_demo_data:
    usage_path = "data/demo/usage_logs.csv"
    schedule_path = "data/demo/schedule.csv"
    historical_path = "data/demo/historical_logs.csv"
else:
    usage_file = st.sidebar.file_uploader("Upload usage logs CSV")
    schedule_file = st.sidebar.file_uploader("Upload schedule CSV")
    historical_file = st.sidebar.file_uploader("Upload historical logs CSV")

    if not (usage_file and schedule_file and historical_file):
        st.info("Please upload all required CSV files.")
        st.stop()

    usage_path = usage_file
    schedule_path = schedule_file
    historical_path = historical_file


# Run analysis
if run_analysis:
    st.subheader("🔍 Analysis Results")

    # Load data
    schedule = load_schedule(schedule_path)

    historical = load_usage_logs(historical_path)
    historical = mark_silence_windows(historical, schedule)
    baseline = compute_silence_baseline(historical)

    current = load_usage_logs(usage_path)
    current = mark_silence_windows(current, schedule)
    result = detect_shadow_waste(current, baseline)

    decisions = []
    for _, row in result.iterrows():
        if row["is_anomaly"]:
            decisions.append(generate_decision(row))

    if not decisions:
        st.success("No shadow waste detected in this cycle.")
    else:
        st.warning(f"{len(decisions)} shadow waste issue(s) detected.")

        decision_df = pd.DataFrame(decisions)
        st.dataframe(decision_df, use_container_width=True)

        st.markdown(
            """
            ### 🧠 What this means
            - These issues occurred **when no activity was expected**
            - Each row is an **actionable recommendation**, not just an alert
            - This analysis represents **one scheduled cycle (e.g., 30 minutes)**
            """
        )
