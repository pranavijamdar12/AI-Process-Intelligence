import pandas as pd
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

DATASET_PATH = BASE_DIR / "dataset" / "event_logs.csv"

df = pd.read_csv(DATASET_PATH)
df["Timestamp"] = pd.to_datetime(df["Timestamp"])

df = df.sort_values(["Case_ID", "Timestamp"])

df["Next_Time"] = df.groupby("Case_ID")["Timestamp"].shift(-1)

df["Duration"] = (
df["Next_Time"] - df["Timestamp"]
).dt.total_seconds() / 3600

df = df.dropna(subset=["Duration"])

summary = df.groupby("Activity")["Duration"].mean()
summary = summary.sort_values(ascending=False)

print("\n===== ROOT CAUSE ANALYSIS =====")

for activity, hours in summary.items():
  print(f"\nActivity: {activity}")
print(f"Average Duration: {hours:.2f} hours")


if hours >= 12:
    print("Possible Issue: High processing time. Check team workload.")
elif hours >= 4:
    print("Possible Issue: Moderate delay. Review task assignment.")
else:
    print("Status: Processing time is relatively low.")


print("\n===== MOST DELAYED STAGE =====")

if not summary.empty:
  print("Activity:", summary.index[0])
  print("Average Duration:", round(summary.iloc[0], 2), "hours")
else:
  print("No activity data available.")
