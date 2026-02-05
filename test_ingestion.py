# from pipeline.ingestion import load_usage_logs, load_schedule

# usage = load_usage_logs("data/demo/usage_logs.csv")
# schedule = load_schedule("data/demo/schedule.csv")
# print(usage)
# print("\n")
# print(schedule)

# from pipeline.ingestion import load_usage_logs, load_schedule
# from pipeline.silence_detection import mark_silence_windows
# usage = load_usage_logs("data/demo/usage_logs.csv")
# schedule = load_schedule("data/demo/schedule.csv")
# result = mark_silence_windows(usage, schedule)
# print(result)

# from pipeline.ingestion import load_usage_logs, load_schedule
# from pipeline.silence_detection import mark_silence_windows
# from pipeline.baseline import compute_silence_baseline
# # Load historical data
# historical = load_usage_logs("data/demo/historical_logs.csv")
# schedule = load_schedule("data/demo/schedule.csv")
# historical = mark_silence_windows(historical, schedule)
# baseline = compute_silence_baseline(historical)
# print(baseline)


# from pipeline.ingestion import load_usage_logs, load_schedule
# from pipeline.silence_detection import mark_silence_windows
# from pipeline.baseline import compute_silence_baseline
# from pipeline.anomaly import detect_shadow_waste
# # Load historical data
# historical = load_usage_logs("data/demo/historical_logs.csv")
# schedule = load_schedule("data/demo/schedule.csv")
# historical = mark_silence_windows(historical, schedule)
# baseline = compute_silence_baseline(historical)
# # Load current usage
# current = load_usage_logs("data/demo/usage_logs.csv")
# current = mark_silence_windows(current, schedule)
# result = detect_shadow_waste(current, baseline)
# print(result)


from pipeline.ingestion import load_usage_logs, load_schedule
from pipeline.silence_detection import mark_silence_windows
from pipeline.baseline import compute_silence_baseline
from pipeline.anomaly import detect_shadow_waste
from pipeline.decision import generate_decision

# Load schedule & baseline
schedule = load_schedule("data/demo/schedule.csv")
historical = load_usage_logs("data/demo/historical_logs.csv")
historical = mark_silence_windows(historical, schedule)
baseline = compute_silence_baseline(historical)

# Current usage
current = load_usage_logs("data/demo/usage_logs.csv")
current = mark_silence_windows(current, schedule)
result = detect_shadow_waste(current, baseline)

# Generate decisions
decisions = []
for _, row in result.iterrows():
    if row["is_anomaly"]:
        decisions.append(generate_decision(row))

def print_decision_nicely(decision):
    print("=" * 80)
    print(f"🏢 Building           : {decision['building']}")
    print(f"🔧 Resource           : {decision['resource'].capitalize()}")
    print(f"⚠️  Issue              : {decision['detected_issue']}")
    print("-" * 80)
    print(f"📊 Observed Usage     : {decision['observed_usage']}")
    print(f"📈 Normal (Silence)   : {decision['normal_silence_usage']}")
    print(f"🎯 Confidence         : {decision['confidence_percent']}%")
    print("-" * 80)
    print(f"🔍 Likely Cause       : {decision['likely_cause']}")
    print(f"🛠️  Recommended Action : {decision['recommended_action']}")
    print("=" * 80)
    print()

for d in decisions:
    print_decision_nicely(d)

