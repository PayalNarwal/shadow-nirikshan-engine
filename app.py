import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from pipeline.baseline_ml import compute_silence_baseline_ml


from pipeline.ingestion import load_schedule
from pipeline.scheduler import get_time_window
from pipeline.silence_detection import mark_silence_windows
from pipeline.baseline import compute_silence_baseline
from pipeline.anomaly import detect_shadow_waste
from pipeline.decision import generate_decision


# ============================================================
# Page config
# ============================================================
st.set_page_config(
    page_title="Shadow Nirikshan Engine",
    layout="wide"
)

st.title("🌑 Shadow Nirikshan Engine")
st.subheader("Detecting Invisible Resource Waste During Inactivity")

st.markdown(
    """
    **Shadow Nirikshan Engine** simulates a scheduled monitoring system
    that detects *water and electricity waste* during **inactive periods**.
    """
)

st.divider()


# ============================================================
# Session State Initialization
# ============================================================
if "usage_df" not in st.session_state:
    usage_df = pd.read_csv("data/usage_logs_full.csv")
    usage_df["timestamp"] = pd.to_datetime(usage_df["timestamp"])
    st.session_state.usage_df = usage_df

    st.session_state.current_time = (
        usage_df["timestamp"].min() + timedelta(minutes=30)
    )
    st.session_state.end_time = usage_df["timestamp"].max()

if "cycle_count" not in st.session_state:
    st.session_state.cycle_count = 0

if "decision_history" not in st.session_state:
    st.session_state.decision_history = []

if "anomaly_history" not in st.session_state:
    st.session_state.anomaly_history = []


# ============================================================
# Sidebar Controls
# ============================================================
st.sidebar.header("⚙️ Simulation Controls")

run_one_cycle = st.sidebar.button("▶ Run ONE Cycle (30 min)")
run_one_day = st.sidebar.button("⏩ Run ALL Cycles (1 Day)")



st.sidebar.caption("Each cycle represents a scheduled 30-minute run")


# ============================================================
# Load Schedule
# ============================================================
schedule = load_schedule("data/demo/schedule.csv")

# ============================================================
# Train ML baseline ONCE using full historical silence data
# ============================================================

if "baseline_df" not in st.session_state:

    full_df = st.session_state.usage_df.copy()
    full_df = mark_silence_windows(full_df, schedule)

    st.session_state.baseline_df = compute_silence_baseline_ml(full_df)



# ============================================================
# Core Scheduler Function
# ============================================================
def run_single_cycle():

    usage_df = st.session_state.usage_df
    current_time = st.session_state.current_time

    if current_time > st.session_state.end_time:
        return False

    # 1️⃣ Extract time window
    window_df = get_time_window(
        usage_df,
        current_time,
        window_minutes=30
    )

    if window_df.empty:
        st.session_state.current_time += timedelta(minutes=30)
        return True

    # 2️⃣ Silence detection
    window_df = mark_silence_windows(window_df, schedule)

    # 3️⃣ Baseline from historical data
    historical_df = usage_df[usage_df["timestamp"] < current_time]
    historical_df = mark_silence_windows(historical_df, schedule)
    # baseline = compute_silence_baseline(historical_df)
    baseline = st.session_state.baseline_df


    # 4️⃣ Anomaly detection
    result = detect_shadow_waste(window_df, baseline)
    result["run_time"] = current_time

    st.session_state.anomaly_history.append(result)

    # 5️⃣ Decisions
    st.session_state.cycle_count += 1
    for _, row in result.iterrows():
        if row["is_anomaly"]:
            decision_raw = generate_decision(row)

            decision = {
                "cycle": st.session_state.cycle_count,
                "run_time": current_time,
                "building": row.get("building"),
                "resource": row.get("resource"),
                **decision_raw
            }

            st.session_state.decision_history.append(decision)
    # Advance time
    st.session_state.current_time += timedelta(minutes=30)
    return True


# ============================================================
# Button Actions
# ============================================================
if run_one_cycle:
    success = run_single_cycle()
    if success:
        st.success("✅ One scheduled cycle executed.")
    else:
        st.warning("⏹️ No more data to process.")

if run_one_day:
    start_time = st.session_state.current_time
    end_of_day = start_time + timedelta(days=1)

    progress = st.progress(0)
    steps = 0

    while st.session_state.current_time <= end_of_day:
        if not run_single_cycle():
            break
        steps += 1
        progress.progress(min(steps / 48, 1.0))  # 48 cycles per day

    st.success(f"✅ One full day simulated ({steps} cycles).")


# ============================================================
# Results & Analytics
# ============================================================
st.divider()
st.header("📊 Simulation Results")

# if not st.session_state.decision_history:
#     st.info("Run one or more cycles to view results.")
#     st.stop()

if not st.session_state.anomaly_history:
    st.info("Run one or more cycles to view results.")
    st.stop()

decision_df = pd.DataFrame(st.session_state.decision_history)


# ---------------- KPI Metrics ----------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Cycles Run", st.session_state.cycle_count)
c2.metric("Total Decisions", len(decision_df))

if not decision_df.empty:
    c3.metric("Buildings Impacted", decision_df["building"].nunique())
    c4.metric("Resources Tracked", decision_df["resource"].nunique())
else:
    c3.metric("Buildings Impacted", 0)
    c4.metric("Resources Tracked", 0)


# ---------------- Decision Table ----------------
st.subheader("📋 All Shadow Waste Decisions")
st.dataframe(decision_df, use_container_width=True)


# ---------------- Graphs ----------------
st.subheader("🏢 Anomalies by Building")
if "building" in decision_df.columns:
    building_chart = (
        decision_df
        .groupby("building")
        .size()
        .reset_index(name="count")
    )
    st.bar_chart(building_chart, x="building", y="count")
else:
    st.info("No building-level anomaly data available yet.")


st.subheader("💧⚡ Anomalies by Resource")
if "resource" in decision_df.columns:
    st.bar_chart(
        decision_df.groupby("resource").size().reset_index(name="count"),
        x="resource",
        y="count"
    )
else:
    st.info("No resource-level anomaly data available yet.")

st.subheader("⏱️ Anomalies Across Cycles")
if "cycle" in decision_df.columns:
    st.line_chart(
        decision_df.groupby("cycle").size().reset_index(name="count"),
        x="cycle",
        y="count"
    )
else:
    st.info("No cycle-level anomaly data available yet.")

st.subheader("🔥 Concentration of Shadow Waste")
if all(col in decision_df.columns for col in ["building", "resource", "detected_issue"]):
    pivot = pd.pivot_table(
        decision_df,
        index="building",
        columns="resource",
        values="detected_issue",
        aggfunc="count",
        fill_value=0
    )
else:
    pivot = pd.DataFrame({"Info": ["Run cycles to generate data"]})

st.dataframe(pivot, use_container_width=True)


st.caption(
    "All analytics are generated from simulated scheduled runs in this session."
)
