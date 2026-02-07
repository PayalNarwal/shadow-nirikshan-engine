"""
ML-based baseline computation using silence-window data.

Trains a regression model once on silence records and produces
baseline_usage per (building, resource). Output schema matches the
original baseline function so downstream anomaly logic remains unchanged.
"""

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder


def compute_silence_baseline_ml(usage_df: pd.DataFrame) -> pd.DataFrame:
    """
    Train ML regressor on silence rows and return baseline per
    building-resource pair.
    """

    # --------------------------------------------------
    # Filter silence rows
    # --------------------------------------------------
    silence_df = usage_df[usage_df["is_silence"] == True].copy()

    if silence_df.empty:
        return pd.DataFrame(
            columns=["building", "resource", "baseline_usage"]
        )

    # --------------------------------------------------
    # Feature engineering from timestamp
    # --------------------------------------------------
    silence_df["hour"] = silence_df["timestamp"].dt.hour
    silence_df["dayofweek"] = silence_df["timestamp"].dt.dayofweek

    # --------------------------------------------------
    # Encode categorical columns
    # --------------------------------------------------
    building_enc = LabelEncoder()
    resource_enc = LabelEncoder()

    silence_df["building_enc"] = building_enc.fit_transform(
        silence_df["building"]
    )
    silence_df["resource_enc"] = resource_enc.fit_transform(
        silence_df["resource"]
    )

    # --------------------------------------------------
    # Prepare training data
    # --------------------------------------------------
    feature_cols = [
        "hour",
        "dayofweek",
        "building_enc",
        "resource_enc"
    ]

    X = silence_df[feature_cols]
    y = silence_df["usage"]

    # --------------------------------------------------
    # Train ONE global model
    # --------------------------------------------------
    model = RandomForestRegressor(
        n_estimators=80,
        max_depth=6,
        random_state=42
    )

    model.fit(X, y)

    # --------------------------------------------------
    # Build baseline per building-resource
    # using median time context
    # --------------------------------------------------
    baseline_rows = []

    for (building, resource), group in silence_df.groupby(
        ["building", "resource"]
    ):

        hour_med = int(group["hour"].median())
        dow_med = int(group["dayofweek"].median())

        b_code = building_enc.transform([building])[0]
        r_code = resource_enc.transform([resource])[0]

        pred_input = pd.DataFrame([{
            "hour": hour_med,
            "dayofweek": dow_med,
            "building_enc": b_code,
            "resource_enc": r_code
        }])

        pred_usage = float(model.predict(pred_input)[0])

        baseline_rows.append({
            "building": building,
            "resource": resource,
            "baseline_usage": pred_usage
        })

    baseline_df = pd.DataFrame(baseline_rows)

    return baseline_df
