import pandas as pd
from datetime import timedelta

from pipeline.scheduler import get_time_window
from pipeline.ingestion import load_schedule
from pipeline.silence_detection import mark_silence_windows
from pipeline.baseline import compute_silence_baseline
from pipeline.anomaly import detect_shadow_waste
from pipeline.decision import generate_decision

# Load full usage dataset
usage_df = pd.read_csv("data/usage_logs_full.csv")
usage_df["timestamp"] = pd.to_datetime(usage_df["timestamp"])

# Load schedule
schedule = load_schedule("data/demo/schedule.csv")

# Initialize scheduler time
current_time = usage_df["timestamp"].min() + timedelta(minutes=30)
end_time = usage_df["timestamp"].max()

# History stores
anomaly_history = []
decision_history = []

print("\n=== Starting Scheduled Simulation ===\n")

while current_time <= end_time:

    print(f"⏱️  Running cycle at {current_time}")

    # 1️⃣ Extract window
    window_df = get_time_window(
        usage_df,
        current_time,
        window_minutes=30
    )

    if window_df.empty:
        current_time += timedelta(minutes=30)
        continue

    # 2️⃣ Silence detection
    window_df = mark_silence_windows(window_df, schedule)

    # 3️⃣ Baseline from historical data
    historical_df = usage_df[usage_df["timestamp"] < current_time]
    historical_df = mark_silence_windows(historical_df, schedule)
    baseline = compute_silence_baseline(historical_df)

    # print(f"\n--- Current Time: {current_time} ---")
    # print("Historical DF sample:")
    # print(historical_df.head())
    # print("Baseline computed:")
    # print(baseline)

    # 4️⃣ Anomaly detection
    result = detect_shadow_waste(window_df, baseline)

    # print("\n[Anomaly Detection Output]")
    # print(result)

    # Store anomalies
    # and result["is_anomaly"]= True
    anomaly_history.append(result.assign(run_time=current_time))

    # 5️⃣ Generate decisions
    for _, row in result.iterrows():
        if row["is_anomaly"]:
            decision = generate_decision(row)
            decision["run_time"] = current_time
            print("\n[Generated Decision]")
            print("=" * 80)
            print(f"🏢 Building           : {decision['building']}")
            print(f"💧 Resource           : {decision['resource']}")

            decision_history.append(decision)

    current_time += timedelta(minutes=30)

print("\n=== Simulation Complete ===")
print(f"Total cycles run: {len(anomaly_history)}")
print(f"Total decisions generated: {len(decision_history)}")

# =========================
# STEP 6: Normalize H
# istory
# =========================

# Combine anomaly history into a single DataFrame
if anomaly_history:
    anomaly_history_df = pd.concat(anomaly_history, ignore_index=True)
else:
    anomaly_history_df = pd.DataFrame()

# Convert decision history into DataFrame
if decision_history:
    decision_history_df = pd.DataFrame(decision_history)
else:
    decision_history_df = pd.DataFrame()

print("\n=== Normalized History ===")
print("\n[Anomaly History Sample]")
print(anomaly_history_df.head())

print("\n[Decision History Sample]")
print(decision_history_df.head())

