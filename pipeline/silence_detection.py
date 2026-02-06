from datetime import time
import pandas as pd


def is_time_in_window(check_time: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= check_time <= end
    else:
        return check_time >= start or check_time <= end


def mark_silence_windows(usage_df, schedule_df):

    usage_df = usage_df.copy()
    usage_df["is_silence"] = False

    for idx, row in usage_df.iterrows():

        building = row["building"]
        record_time = row["timestamp"].time()

        building_schedule = schedule_df[
            schedule_df["building"] == building
        ]

        is_active = False

        # ✅ check YES windows first
        for _, sched in building_schedule.iterrows():
            if sched["expected_activity"] == "YES":
                if is_time_in_window(
                    record_time,
                    sched["start_time"],
                    sched["end_time"]
                ):
                    is_active = True
                    break

        # silence only if not active
        usage_df.at[idx, "is_silence"] = not is_active

    return usage_df
