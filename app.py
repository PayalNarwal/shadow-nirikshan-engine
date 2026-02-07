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

WATER_COST_PER_UNIT = 0.05
ELECTRIC_COST_PER_UNIT = 8.0

if "admin_feedback" not in st.session_state:
    st.session_state.admin_feedback = {}

if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = False

# ============================================================
# Attach Admin Review Column
# ============================================================

def attach_admin_review(df):
    if df is None or df.empty:
        return df

    df = df.copy()

    def make_id(r):
        return f"{r['timestamp']}_{r['building']}_{r['resource']}"

    df["anomaly_id"] = df.apply(make_id, axis=1)

    df["admin_review"] = df["anomaly_id"].map(
        lambda x: st.session_state.admin_feedback.get(x, "Unreviewed")
    )

    return df


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


if "show_feedback_panel" not in st.session_state:
    st.session_state.show_feedback_panel = False

if st.sidebar.button("🧾 Admin Feedback"):
    st.session_state.show_feedback_panel = (
        not st.session_state.show_feedback_panel
    )


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


# Silence Comparison Graph of past 24 hours
import altair as alt

st.subheader("📊 Baseline vs Current Window Usage (All Buildings)")

if st.session_state.anomaly_history:

    current_df = st.session_state.anomaly_history[-1].copy()

    # aggregate current window usage
    current_agg = (
        current_df
        .groupby(["building", "resource", "is_silence"])["usage"]
        .sum()
        .reset_index()
        .rename(columns={"usage": "current_window_usage"})
    )

    # choose baseline
    if baseline_mode == "ML":
        baseline_df = st.session_state.baseline_ml_df.copy()
    else:
        baseline_df = st.session_state.baseline_mean_df.copy()

    compare_df = baseline_df.merge(
        current_agg,
        on=["building", "resource"],
        how="left"
    ).fillna({
        "current_window_usage": 0,
        "is_silence": False
    })

    compare_df["label"] = (
        compare_df["building"] + "-" + compare_df["resource"]
    )

    # ---------- build plot dataset ----------

    base_part = compare_df[[
        "label", "baseline_usage"
    ]].rename(columns={"baseline_usage": "usage"})
    base_part["type"] = "baseline"
    base_part["status"] = "baseline"

    curr_part = compare_df[[
        "label", "current_window_usage", "is_silence"
    ]].rename(columns={"current_window_usage": "usage"})
    curr_part["type"] = "current"
    curr_part["status"] = curr_part["is_silence"].map(
        {True: "silence", False: "normal"}
    )

    plot_long = pd.concat([
        base_part[["label","usage","type","status"]],
        curr_part[["label","usage","type","status"]]
    ])

    # ---------- color rule ----------

    color_scale = alt.Scale(
        domain=["baseline","silence","normal"],
        range=["#4c78a8", "#e45756", "#54a24b"]  # blue, red, green
    )

    chart = alt.Chart(plot_long).mark_bar().encode(
        x=alt.X("label:N", title="Building-Resource"),
        xOffset="type:N",
        y=alt.Y("usage:Q"),
        color=alt.Color("status:N", scale=color_scale, title="Bar Type")
    ).properties(height=350)

    st.altair_chart(chart, use_container_width=True)

    st.caption(
        "Baseline shown in blue. Current window usage is red for scheduled silence windows and green for normal activity windows."
    )

    # ---------- collapsible table ----------

    def color_status(val):
        if val == True:
            return "background-color:#ffd6d6"  # red tint
        else:
            return "background-color:#d6f5d6"  # green tint

    with st.expander("📋 View plotted values"):
        styled = compare_df.style.applymap(
            color_status,
            subset=["is_silence"]
        )
        st.dataframe(styled, use_container_width=True)

else:
    st.info("Run at least one cycle to view current window comparison.")


# ============================================================
# Results & Analytics
# ============================================================
st.header("🏛️ Shadow Waste Results")
with st.expander("📊 Collapsable Results", expanded=False):

    if not st.session_state.decision_history:
        st.info("Run one or more cycles to view results.")
        st.stop()

    if not st.session_state.anomaly_history:
        st.info("Run one or more cycles to view results.")
        st.stop()

    decision_df = pd.DataFrame(st.session_state.decision_history)
    # ---------------- Raw Anomaly Table (with Admin Review) ----------------

    st.subheader("🚨 Detected Anomalies (With Admin Review)")

    anomaly_all = pd.concat(st.session_state.anomaly_history)
    anomaly_all = anomaly_all[anomaly_all["is_anomaly"] == True]

    anomaly_all = attach_admin_review(anomaly_all)

    def highlight_false_alarm(row):
        if row["admin_review"] == "False Alarm":
            return ["background-color: #ffcccc"] * len(row)
        return [""] * len(row)

    anomaly_all_display = anomaly_all.reset_index(drop=True)

    st.dataframe(
        anomaly_all_display.style.apply(highlight_false_alarm, axis=1),
        use_container_width=True
    )





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
    # st.subheader("📋 All Shadow Waste Decisions")
    # st.dataframe(decision_df, use_container_width=True)


    # ---------------- Graphs ----------------
    st.subheader("🏢 Anomalies by Building")

    if "building" in decision_df.columns:

        building_chart = (
            decision_df
            .groupby("building")
            .size()
            .reset_index(name="count")
        )

        pie_building = alt.Chart(building_chart).mark_arc().encode(
            theta="count:Q",
            color="building:N",
            tooltip=["building", "count"]
        )

        st.altair_chart(pie_building, use_container_width=True)

    else:
        st.info("No building-level anomaly data available yet.")



    st.subheader("💧⚡ Anomalies by Resource")

    if "resource" in decision_df.columns:

        resource_chart = (
            decision_df
            .groupby("resource")
            .size()
            .reset_index(name="count")
        )

        pie_resource = alt.Chart(resource_chart).mark_arc().encode(
            theta="count:Q",
            color="resource:N",
            tooltip=["resource", "count"]
        )

        st.altair_chart(pie_resource, use_container_width=True)

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

            anomaly_all["waste_cost"] = anomaly_all.apply(
                lambda r: r["excess_usage"] * (
                    WATER_COST_PER_UNIT
                    if r["resource"] == "water"
                    else ELECTRIC_COST_PER_UNIT
                ),
                axis=1
            )


            staff_summary = (
                anomaly_all
                .groupby(
                    [
                        "staff_name",
                        "staff_role",
                        "staff_phone",
                        "building",
                        "resource"
                    ]
                )
                .agg(
                    anomaly_count=("usage", "count"),
                    total_excess_usage=("excess_usage", "sum"),
                    total_cost=("waste_cost", "sum")
                )
                .reset_index()
                .sort_values("total_cost", ascending=False)
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

# ============================================================
# Admin Feedback Panel
# ============================================================
st.divider()
st.header("🧾 Admin Anomaly Feedback")
st.info("Admins can mark anomalies as true waste or false alarms to validate system decisions.")


if st.session_state.show_feedback_panel:

    if not st.session_state.anomaly_history:
        st.info("Run anomaly cycles first.")
    else:

        anomaly_all = pd.concat(st.session_state.anomaly_history)

        anomaly_rows = anomaly_all[
            anomaly_all["is_anomaly"] == True
        ].copy()

        if anomaly_rows.empty:
            st.success("No anomalies detected.")
        else:

            feedback_updates = {}

            for idx, row in anomaly_rows.iterrows():

                anomaly_id = (
                    f"{row['timestamp']}_"
                    f"{row['building']}_"
                    f"{row['resource']}"
                )

                label = st.selectbox(
                    f"{row['timestamp']} | {row['building']} | {row['resource']}",
                    ["Unreviewed", "True Waste", "False Alarm"],
                    key=f"fb_{anomaly_id}"
                )

                feedback_updates[anomaly_id] = label

            if st.button("💾 Save Feedback"):

                st.session_state.admin_feedback.update(feedback_updates)
                st.session_state.feedback_submitted = True

                st.success("Feedback saved. Table updated.")
                st.rerun()
