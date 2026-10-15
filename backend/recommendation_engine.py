import pandas as pd
from pathlib import Path

# Load dataset
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "dataset" / "event_logs.csv"

df = pd.read_csv(DATASET_PATH)
df["Timestamp"] = pd.to_datetime(df["Timestamp"])

# Sort events by ticket and time
df = df.sort_values(["Case_ID", "Timestamp"])

# Calculate duration between consecutive activities
df["Next_Activity"] = df.groupby("Case_ID")["Activity"].shift(-1)
df["Next_Timestamp"] = df.groupby("Case_ID")["Timestamp"].shift(-1)

df["Duration_Hours"] = (
    df["Next_Timestamp"] - df["Timestamp"]
).dt.total_seconds() / 3600

# Remove rows without a next activity
stage_data = df.dropna(subset=["Next_Activity"]).copy()

# Calculate average duration for each activity
stage_summary = (
    stage_data.groupby("Activity")["Duration_Hours"]
    .mean()
    .sort_values(ascending=False)
)

print("\n===== AI PROCESS RECOMMENDATIONS =====")

for activity, duration in stage_summary.items():
    print(f"\nActivity: {activity}")
    print(f"Average Duration: {duration:.2f} hours")

    if duration >= 5:
        print("Recommendation: Investigate workload, resource availability, and task complexity.")
        print("Suggested Action: Review this stage and identify opportunities to reduce delays.")

    elif duration >= 2:
        print("Recommendation: Monitor this stage for possible delays.")
        print("Suggested Action: Review task allocation and team coordination.")

    else:
        print("Recommendation: Processing time is relatively low in this dataset.")
        print("Suggested Action: Continue monitoring this stage.")

print("\n===== TOP PRIORITY FOR INVESTIGATION =====")

if not stage_summary.empty:
    slowest_stage = stage_summary.idxmax()
    slowest_duration = stage_summary.max()

    print(f"Activity: {slowest_stage}")
    print(f"Average Duration: {slowest_duration:.2f} hours")
    print("Action: Investigate why this stage takes longer than other stages.")

print("\nRecommendations generated successfully!")