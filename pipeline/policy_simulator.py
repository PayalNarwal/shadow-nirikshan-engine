import pandas as pd
from datetime import time


# -----------------------------
# Demo cost & carbon constants
# -----------------------------

WATER_COST_PER_UNIT = 0.05        # ₹ per liter (demo)
ELECTRIC_COST_PER_UNIT = 8.0      # ₹ per kWh (demo)

WATER_CO2_PER_UNIT = 0.0003       # kg CO2 per liter
ELECTRIC_CO2_PER_UNIT = 0.82      # kg CO2 per kWh


# -----------------------------
# Time window helper
# -----------------------------

def in_window(t: time, start: time, end: time):
    if start <= end:
        return start <= t <= end
    else:
        return t >= start or t <= end


# -----------------------------
# Policy savings calculator
# -----------------------------

# -----------------------------
# Policy savings calculator
# -----------------------------

def compute_policy_savings(
    anomaly_df: pd.DataFrame,
    pump_start: time,
    pump_end: time,
    shutdown_buildings: list,
    elec_start: time,
    elec_end: time,
    pump_buildings=None
):

    if anomaly_df.empty:
        return {
            "water_saved": 0,
            "electric_saved": 0,
            "money_saved": 0,
            "co2_saved": 0
        }

    water_saved = 0.0
    electric_saved = 0.0

    for _, row in anomaly_df.iterrows():

        # ---- Safety guards ----
        if pd.isna(row.get("baseline_usage")):
            continue

        if not row.get("is_anomaly"):
            continue

        if not row.get("is_silence"):
            continue

        ts = row.get("timestamp")
        if pd.isna(ts):
            continue

        t = ts.time()
        excess = max(row["usage"] - row["baseline_usage"], 0)

        # =========================
        # 💧 Pump Policy (optional)
        # =========================
        if (
            pump_start and pump_end and
            row["resource"] == "water" and
            (not pump_buildings or row["building"] in pump_buildings)
        ):
            if not in_window(t, pump_start, pump_end):
                water_saved += excess

        # =========================
        # ⚡ Electricity Policy (optional)
        # =========================
        if (
            elec_start and elec_end and
            row["resource"] == "electricity" and
            row["building"] in shutdown_buildings
        ):
            if in_window(t, elec_start, elec_end):
                electric_saved += excess

    money_saved = (
        water_saved * WATER_COST_PER_UNIT +
        electric_saved * ELECTRIC_COST_PER_UNIT
    )

    co2_saved = (
        water_saved * WATER_CO2_PER_UNIT +
        electric_saved * ELECTRIC_CO2_PER_UNIT
    )

    return {
        "water_saved": round(water_saved, 2),
        "electric_saved": round(electric_saved, 2),
        "money_saved": round(money_saved, 2),
        "co2_saved": round(co2_saved, 2)
    }
