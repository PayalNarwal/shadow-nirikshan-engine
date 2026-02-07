import pandas as pd
from datetime import time


def in_window(t: time, start: time, end: time):
    if start <= end:
        return start <= t <= end
    else:
        return t >= start or t <= end


def load_staff_schedule(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df["start_time"] = pd.to_datetime(df["start_time"], format="%H:%M").dt.time
    df["end_time"] = pd.to_datetime(df["end_time"], format="%H:%M").dt.time
    return df


def attach_staff_info(df: pd.DataFrame, staff_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds staff_name, role, phone columns based on building + duty window.
    """

    df = df.copy()
    df["staff_name"] = None
    df["staff_role"] = None
    df["staff_phone"] = None

    for idx, row in df.iterrows():
        bld = row.get("building")
        ts = row.get("timestamp")

        if pd.isna(ts):
            continue

        t = ts.time()
        staff_rows = staff_df[staff_df["building"] == bld]

        matched = False

        for _, s in staff_rows.iterrows():
            if in_window(t, s["start_time"], s["end_time"]):
                df.at[idx, "staff_name"] = s.get("staff_name")
                df.at[idx, "staff_role"] = s.get("role")
                df.at[idx, "staff_phone"] = s.get("phone")
                matched = True
                break

        # ---- fallback if no staff matched ----
        if not matched:
            df.at[idx, "staff_name"] = "Unassigned"
            df.at[idx, "staff_role"] = "No Duty Match"
            df.at[idx, "staff_phone"] = "-"


    return df
