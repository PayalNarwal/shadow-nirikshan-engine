def generate_decision(row):
    """
    Generate admin-facing decision text for a detected anomaly.
    """

    building = row["building"]
    resource = row["resource"]
    usage = row["usage"]
    baseline = row["baseline_usage"]

    excess_ratio = usage / baseline if baseline else 1

    # Likely cause & action logic
    if resource == "water":
        cause = "Possible pump left ON, leakage, or tank overflow"
        action = "Inspect water pump, float valve, and tank overflow system"
    else:
        cause = "Idle electrical load or equipment left powered ON"
        action = "Check lab equipment, lighting, and auto-shutdown policies"

    confidence = min(int(excess_ratio * 50), 95)

    decision = {
        "building": building,
        "resource": resource,
        "observed_usage": round(usage, 2),
        "normal_silence_usage": round(baseline, 2),
        "confidence_percent": confidence,
        "likely_cause": cause,
        "recommended_action": action,
        "detected_issue": "Usage during inactivity",
    }

    return decision