import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "dataset" / "event_logs.csv"


def detect_bottlenecks():
    # Load the event log dataset
    df = pd.read_csv(DATASET_PATH)

    # Convert timestamps into datetime format
    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"], errors="coerce"
    )

    # Remove invalid records
    df = df.dropna(
        subset=["Case_ID", "Activity", "Timestamp"]
    )

    # Sort activities by ticket and time
    df = df.sort_values(
        ["Case_ID", "Timestamp"]
    ).reset_index(drop=True)

    # Find the next activity and its timestamp for each ticket
    df["Next_Activity"] = (
        df.groupby("Case_ID")["Activity"].shift(-1)
    )

    df["Next_Timestamp"] = (
        df.groupby("Case_ID")["Timestamp"].shift(-1)
    )

    # Calculate the time until the next activity
    df["Stage_Duration_Hours"] = (
        df["Next_Timestamp"] - df["Timestamp"]
    ).dt.total_seconds() / 3600

    # Keep records that have a following activity
    stage_data = df.dropna(
        subset=["Next_Activity", "Stage_Duration_Hours"]
    ).copy()

    # Exclude negative durations if timestamps are inconsistent
    stage_data = stage_data[
        stage_data["Stage_Duration_Hours"] >= 0
    ]

    if stage_data.empty:
        print("No valid process stages found.")
        return

    # Group stage durations by the activity that starts each stage
    bottleneck_summary = (
        stage_data.groupby("Activity")
        .agg(
            Average_Time_Hours=("Stage_Duration_Hours", "mean"),
            Maximum_Time_Hours=("Stage_Duration_Hours", "max"),
            Cases_Analyzed=("Case_ID", "nunique"),
        )
        .reset_index()
        .sort_values(
            "Average_Time_Hours", ascending=False
        )
    )

    bottleneck_summary["Average_Time_Hours"] = (
        bottleneck_summary["Average_Time_Hours"].round(2)
    )

    bottleneck_summary["Maximum_Time_Hours"] = (
        bottleneck_summary["Maximum_Time_Hours"].round(2)
    )

    print("\n===== BOTTLENECK ANALYSIS =====")
    print(bottleneck_summary.to_string(index=False))

    slowest_stage = bottleneck_summary.iloc[0]

    print("\n===== POTENTIAL BOTTLENECK =====")
    print("Activity:", slowest_stage["Activity"])
    print(
        "Average Time:",
        slowest_stage["Average_Time_Hours"],
        "hours",
    )


if __name__ == "__main__":
    detect_bottlenecks()