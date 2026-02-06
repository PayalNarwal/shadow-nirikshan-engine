import pandas as pd

THRESHOLDS = {
    "water": 1.5,
    "electricity": 1.3
}


def detect_shadow_waste(
    usage_df: pd.DataFrame,
    baseline_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Detects anomalies during silence periods.
    Adds 'is_anomaly' column.
    """

    df = usage_df.copy()
    df["is_anomaly"] = False

    # Merge baseline into usage
    merged = df.merge(
        baseline_df,
        on=["building", "resource"],
        how="left"
    )

    for idx, row in merged.iterrows():
        if not row["is_silence"]:
            continue

        baseline = row.get("baseline_usage")
        if pd.isna(baseline):
            continue  # No baseline learned yet

        threshold = THRESHOLDS.get(row["resource"], 1.5)

        if row["usage"] > baseline * threshold:
            merged.at[idx, "is_anomaly"] = True
            # print(f"Anomaly detected: {row['building']} - {row['resource']} | Usage: {row['usage']} vs Baseline: {baseline:.2f}")

    return merged