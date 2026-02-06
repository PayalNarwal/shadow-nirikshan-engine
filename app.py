import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from pipeline.policy_simulator import compute_policy_savings


from pipeline.baseline_ml import compute_silence_baseline_ml
from pipeline.staff_mapper import load_staff_schedule, attach_staff_info


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
st.sidebar.header("⚙️ Shadow Waste Controls")
baseline_mode = st.sidebar.radio(
    "Baseline Method",
    ["ML", "Mean"],
    index=0
)

# ---------------- RESET WHEN BASELINE MODE CHANGES ----------------

if "last_baseline_mode" not in st.session_state:
    st.session_state.last_baseline_mode = baseline_mode

if st.session_state.last_baseline_mode != baseline_mode:

    # reset simulation state
    st.session_state.cycle_count = 0
    st.session_state.decision_history = []
    st.session_state.anomaly_history = []

    usage_df = st.session_state.usage_df
    st.session_state.current_time = (
        usage_df["timestamp"].min() + timedelta(minutes=30)
    )

    st.session_state.last_baseline_mode = baseline_mode

    st.sidebar.success("Simulation reset due to baseline change")

run_one_cycle = st.sidebar.button("▶ Run ONE Cycle (30 min)")
run_one_day = st.sidebar.button("⏩ Run ALL Cycles (1 Day)")



st.sidebar.caption("Each cycle represents a scheduled 30-minute run")

# -------- Staff Responsibility Toggle --------

if "show_staff_panel" not in st.session_state:
    st.session_state.show_staff_panel = False

if st.sidebar.button("👤 Staff Responsibility"):
    st.session_state.show_staff_panel = not st.session_state.show_staff_panel


# -------- Policy Simulation Toggle --------

if "show_policy_panel" not in st.session_state:
    st.session_state.show_policy_panel = False

if st.sidebar.button("🏛️ Policy Simulation"):
    st.session_state.show_policy_panel = not st.session_state.show_policy_panel


# ============================================================
# Load Schedule
# ============================================================
schedule = load_schedule("data/demo/schedule.csv")
staff_schedule = load_staff_schedule("data/demo/staff_schedule.csv")

# ============================================================
# Train ML baseline ONCE using full historical silence data
# ============================================================

if "baseline_ml_df" not in st.session_state:

    full_df = st.session_state.usage_df.copy()
    full_df = mark_silence_windows(full_df, schedule)

    st.session_state.baseline_ml_df = compute_silence_baseline_ml(full_df)
    st.session_state.baseline_mean_df = compute_silence_baseline(full_df)

# DEBUG — compare baselines
# st.write("ML baseline", st.session_state.baseline_ml_df)
# st.write("Mean baseline", st.session_state.baseline_mean_df)




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
    if baseline_mode == "ML":
        baseline = st.session_state.baseline_ml_df
    else:
        baseline = st.session_state.baseline_mean_df



    # 4️⃣ Anomaly detection
    result = detect_shadow_waste(window_df, baseline)
    result["run_time"] = current_time

    # 🔥 Attach staff responsibility
    result = attach_staff_info(result, staff_schedule)

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

st.header("📊 Shadow Waste Results")

if not st.session_state.decision_history:
    st.info("Run one or more cycles to view simulation results.")
else:
    # everything related to simulation results
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


# ============================================================
# Staff Responsibility Panel
# ============================================================
st.divider()
st.header("👤 Staff Responsibility Mapping")
st.info("Maps detected anomalies to on-duty staff and aggregates waste impact.")

if st.session_state.show_staff_panel:

    run_staff_map = st.button("▶ Generate Staff Responsibility Report")

    if run_staff_map and not st.session_state.anomaly_history:
        st.warning("Run anomaly detection cycles first.")

    if run_staff_map and st.session_state.anomaly_history:

        anomaly_all = pd.concat(st.session_state.anomaly_history)

        # keep only real silence anomalies with baseline
        anomaly_all = anomaly_all[
            (anomaly_all["is_anomaly"] == True) &
            (anomaly_all["is_silence"] == True) &
            (~anomaly_all["baseline_usage"].isna())
        ].copy()
        st.write("Total anomaly rows:", len(anomaly_all))


        if anomaly_all.empty:
            st.info("No anomaly rows available.")
        else:
            anomaly_all["excess_usage"] = (
                anomaly_all["usage"] - anomaly_all["baseline_usage"]
            ).clip(lower=0)

            staff_summary = (
                anomaly_all
                .groupby(
                    ["staff_name", "staff_role", "staff_phone", "building"]
                )
                .agg(
                    anomaly_count=("usage", "count"),
                    total_excess_usage=("excess_usage", "sum")
                )
                .reset_index()
                .sort_values("total_excess_usage", ascending=False)
            )

            st.subheader("📋 Staff Accountability Table")
            st.dataframe(staff_summary, use_container_width=True)


# ============================================================
# Policy Simulation Panel (Right Side)
# ============================================================

st.divider()
st.header("🏛️ Policy Simulation")
st.info("Configure policy rules and simulate resource savings after anomaly detection runs.")


if st.session_state.show_policy_panel:

    enable_pump_policy = st.checkbox("Enable Pump Policy")
    enable_elec_policy = st.checkbox("Enable Electricity Policy")

    all_buildings = st.session_state.usage_df["building"].unique().tolist()

    # ---------------- Pump Policy ----------------

    if enable_pump_policy:

        st.subheader("💧 Pump Policy")

        pump_buildings = st.multiselect(
            "Pump restriction buildings",
            all_buildings
        )

        pump_start = st.time_input("Pump allowed start")
        pump_end   = st.time_input("Pump allowed end")

    else:
        pump_buildings = []
        pump_start = None
        pump_end = None

    # ---------------- Electricity Policy ----------------

    if enable_elec_policy:

        st.subheader("⚡ Electricity Policy")

        shutdown_buildings = st.multiselect(
            "Shutdown buildings",
            all_buildings
        )

        elec_start = st.time_input("Shutdown start")
        elec_end   = st.time_input("Shutdown end")

    else:
        shutdown_buildings = []
        elec_start = None
        elec_end = None

    # ---------------- Savings Window ----------------

    policy_window = st.selectbox(
        "Savings window",
        ["Last 7 days", "Last 30 days", "All"]
    )

    run_policy_sim = st.button("▶ Simulate Policy Impact")
    if run_policy_sim and not st.session_state.anomaly_history:
        st.warning("Run anomaly detection cycles first.")

    # ---------- Compute Policy Savings ----------

    if run_policy_sim and st.session_state.anomaly_history:

        anomaly_all = pd.concat(st.session_state.anomaly_history)

        now = anomaly_all["timestamp"].max()

        if policy_window == "Last 7 days":
            anomaly_all = anomaly_all[
                anomaly_all["timestamp"] >= now - pd.Timedelta(days=7)
            ]
        elif policy_window == "Last 30 days":
            anomaly_all = anomaly_all[
                anomaly_all["timestamp"] >= now - pd.Timedelta(days=30)
            ]

        if enable_pump_policy or enable_elec_policy:

            savings = compute_policy_savings(
                anomaly_all,
                pump_start, pump_end,
                shutdown_buildings,
                elec_start, elec_end,
                pump_buildings=pump_buildings
            )

        else:
            savings = {
                "water_saved": 0,
                "electric_saved": 0,
                "money_saved": 0,
                "co2_saved": 0
            }

        # ---------------- Resource-wise anomaly counts ----------------

        water_anomalies = anomaly_all[
            (anomaly_all["is_anomaly"] == True) &
            (anomaly_all["is_silence"] == True) &
            (anomaly_all["resource"] == "water")
        ].shape[0]

        electric_anomalies = anomaly_all[
            (anomaly_all["is_anomaly"] == True) &
            (anomaly_all["is_silence"] == True) &
            (anomaly_all["resource"] == "electricity")
        ].shape[0]


        st.subheader("📊 Policy Impact")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("💧 Water Saved", savings["water_saved"])
        c2.metric("⚡ Electric Saved", savings["electric_saved"])
        c3.metric("₹ Money Saved", savings["money_saved"])
        c4.metric("🌍 CO₂ Reduced (kg)", savings["co2_saved"])

        st.divider()

        c5, c6, c7 = st.columns(3)

        c5.metric("💧 Water Anomalies", water_anomalies)
        c6.metric("⚡ Electric Anomalies", electric_anomalies)
        # c7.metric("🚫 Total Silence Anomalies", preventable_events)

