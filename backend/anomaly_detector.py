import pandas as pd
from pathlib import Path
from sklearn.ensemble import IsolationForest

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "dataset" / "event_logs.csv"


def detect_anomalies():
    # Load ticket event data
    df = pd.read_csv(DATASET_PATH)

    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"], errors="coerce"
    )

    df = df.dropna(
        subset=["Case_ID", "Activity", "Timestamp"]
    )

    df = df.sort_values(
        ["Case_ID", "Timestamp"]
    ).reset_index(drop=True)

    # Calculate total processing time for each ticket
    ticket_summary = (
        df.groupby("Case_ID")
        .agg(
            Start_Time=("Timestamp", "min"),
            End_Time=("Timestamp", "max"),
            Total_Activities=("Activity", "count"),
            Priority=("Priority", "first"),
        )
        .reset_index()
    )

    ticket_summary["Processing_Hours"] = (
        ticket_summary["End_Time"]
        - ticket_summary["Start_Time"]
    ).dt.total_seconds() / 3600

    # Select numerical features for anomaly detection
    features = ticket_summary[
        ["Processing_Hours", "Total_Activities"]
    ]

    # Train the anomaly detection model
    model = IsolationForest(
        contamination=0.20,
        random_state=42
    )

    predictions = model.fit_predict(features)

    # -1 means anomaly; 1 means normal
    ticket_summary["Detection"] = predictions

    ticket_summary["Result"] = ticket_summary[
        "Detection"
    ].map({
        1: "Normal",
        -1: "Potential Anomaly"
    })

    print("\n===== ANOMALY DETECTION RESULTS =====")

    print(
        ticket_summary[
            [
                "Case_ID",
                "Priority",
                "Processing_Hours",
                "Total_Activities",
                "Result",
            ]
        ].to_string(index=False)
    )

    print("\n===== SUMMARY =====")

    print(
        "Total Tickets:",
        len(ticket_summary)
    )

    print(
        "Potential Anomalies:",
        (ticket_summary["Detection"] == -1).sum()
    )

    print(
        "Normal Tickets:",
        (ticket_summary["Detection"] == 1).sum()
    )


if __name__ == "__main__":
    detect_anomalies()