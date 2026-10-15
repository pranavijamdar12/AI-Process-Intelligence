import pandas as pd
from pathlib import Path

# Locate the dataset file
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "dataset" / "event_logs.csv"


def load_ticket_data():
    """Load customer support ticket event logs."""

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at: {DATASET_PATH}"
        )

    df = pd.read_csv(DATASET_PATH)

    # Convert timestamps into datetime format
    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"], errors="coerce"
    )

    # Remove rows with invalid timestamps or missing IDs
    df = df.dropna(subset=["Case_ID", "Activity", "Timestamp"])

    # Sort events by ticket and time
    df = df.sort_values(
        by=["Case_ID", "Timestamp"]
    ).reset_index(drop=True)

    return df


def analyze_tickets(df):
    """Calculate the processing time for each ticket."""

    ticket_summary = (
        df.groupby("Case_ID")
        .agg(
            Start_Time=("Timestamp", "min"),
            Last_Activity_Time=("Timestamp", "max"),
            Total_Activities=("Activity", "count"),
            Final_Status=("Status", "last"),
        )
        .reset_index()
    )

    ticket_summary["Processing_Hours"] = (
        ticket_summary["Last_Activity_Time"]
        - ticket_summary["Start_Time"]
    ).dt.total_seconds() / 3600

    return ticket_summary


if __name__ == "__main__":
    ticket_data = load_ticket_data()
    summary = analyze_tickets(ticket_data)

    print("\n===== CUSTOMER SUPPORT TICKET DATA =====")
    print(ticket_data.to_string(index=False))

    print("\n===== TICKET PROCESSING SUMMARY =====")
    print(summary.to_string(index=False))

    print("\nTotal Tickets:", ticket_data["Case_ID"].nunique())
    print("Total Activities:", len(ticket_data))

    print(
        "\nAverage Processing Time:",
        round(summary["Processing_Hours"].mean(), 2),
        "hours",
    )