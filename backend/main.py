
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime
import pandas as pd
import mysql.connector
import os

from dotenv import load_dotenv
from delay_predictor import predict_delay

# Load database settings from backend/.env
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

app = FastAPI(
    title="AI Process Intelligence Platform",
    description="API for IT support ticket process analysis",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = BACKEND_DIR.parent
DATASET_PATH = BASE_DIR / "dataset" / "event_logs.csv"


# ---------------------------------------------
# MySQL Connection
# ---------------------------------------------

def get_db_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv(
                "MYSQL_DATABASE", "process_intelligence"
            ),
            connection_timeout=5
        )
    except mysql.connector.Error as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "MySQL connection failed. Check that MySQL is running "
                "and backend/.env has the correct settings."
            )
        ) from exc


# ---------------------------------------------
# Dataset
# ---------------------------------------------

def load_data():
    if not DATASET_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="Dataset file event_logs.csv was not found."
        )

    df = pd.read_csv(DATASET_PATH)

    required_columns = [
        "Case_ID", "Priority", "Status", "Activity",
        "Timestamp", "Department"
    ]

    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Dataset is missing columns: {missing}"
        )

    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"], errors="coerce"
    )
    df = df.dropna(subset=["Case_ID", "Timestamp"])

    return df


# ---------------------------------------------
# Home
# ---------------------------------------------

@app.get("/")
def home():
    return {
        "message": "AI Process Intelligence Platform is running!",
        "status": "success",
        "database": "MySQL connection configured"
    }


@app.get("/database-status")
def database_status():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        database_name = cursor.fetchone()[0]

        return {
            "status": "success",
            "database_connected": True,
            "database_name": database_name
        }
    except mysql.connector.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not verify database connection."
        ) from exc
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# ---------------------------------------------
# Existing CSV-based Tickets API
# ---------------------------------------------

@app.get("/tickets")
def get_tickets():
    df = load_data()

    tickets = df.groupby("Case_ID").agg(
        Priority=("Priority", "first"),
        Status=("Status", "last"),
        Total_Activities=("Activity", "count"),
        Start_Time=("Timestamp", "min"),
        End_Time=("Timestamp", "max")
    ).reset_index()

    tickets["Processing_Hours"] = (
        tickets["End_Time"] - tickets["Start_Time"]
    ).dt.total_seconds() / 3600

    tickets = tickets.fillna("")
    tickets["Start_Time"] = tickets["Start_Time"].astype(str)
    tickets["End_Time"] = tickets["End_Time"].astype(str)

    return tickets.to_dict(orient="records")


# ---------------------------------------------
# Existing Process Analysis API
# ---------------------------------------------

@app.get("/process-analysis")
def process_analysis():
    df = load_data()

    total_tickets = int(df["Case_ID"].nunique())
    total_activities = int(len(df))
    total_departments = int(df["Department"].nunique())

    ticket_times = df.groupby("Case_ID")["Timestamp"].agg(
        ["min", "max"]
    )

    processing_hours = (
        (ticket_times["max"] - ticket_times["min"])
        .dt.total_seconds() / 3600
    )

    average_processing_hours = (
        round(float(processing_hours.mean()), 2)
        if not processing_hours.empty else 0
    )

    return {
        "total_tickets": total_tickets,
        "total_activities": total_activities,
        "total_departments": total_departments,
        "average_processing_hours": average_processing_hours
    }


# ---------------------------------------------
# Existing Bottleneck Detection API
# ---------------------------------------------

@app.get("/bottlenecks")
def get_bottlenecks():
    df = load_data()
    df = df.sort_values(["Case_ID", "Timestamp"])

    df["Next_Timestamp"] = (
        df.groupby("Case_ID")["Timestamp"].shift(-1)
    )

    df["Duration_Hours"] = (
        (df["Next_Timestamp"] - df["Timestamp"])
        .dt.total_seconds() / 3600
    )

    stage_data = df.dropna(subset=["Duration_Hours"])

    summary = (
        stage_data.groupby("Activity")["Duration_Hours"]
        .agg(["mean", "max"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )

    summary = summary.rename(columns={
        "Activity": "activity",
        "mean": "average_duration_hours",
        "max": "maximum_duration_hours"
    })

    summary["average_duration_hours"] = (
        summary["average_duration_hours"].round(2)
    )
    summary["maximum_duration_hours"] = (
        summary["maximum_duration_hours"].round(2)
    )

    return summary.to_dict(orient="records")


# ---------------------------------------------
# Existing Recommendations API
# ---------------------------------------------

@app.get("/recommendations")
def get_recommendations():
    df = load_data()
    df = df.sort_values(["Case_ID", "Timestamp"])

    df["Next_Timestamp"] = (
        df.groupby("Case_ID")["Timestamp"].shift(-1)
    )

    df["Duration_Hours"] = (
        (df["Next_Timestamp"] - df["Timestamp"])
        .dt.total_seconds() / 3600
    )

    stage_data = df.dropna(subset=["Duration_Hours"])

    summary = (
        stage_data.groupby("Activity")["Duration_Hours"]
        .mean()
        .sort_values(ascending=False)
    )

    recommendations = []

    for activity, duration in summary.items():
        if duration >= 5:
            suggestion = (
                "Investigate workload, resource availability, "
                "and task complexity."
            )
        elif duration >= 2:
            suggestion = (
                "Monitor this stage and review task allocation "
                "and team coordination."
            )
        else:
            suggestion = (
                "Processing time is relatively low in this sample. "
                "Continue monitoring."
            )

        recommendations.append({
            "activity": activity,
            "average_duration_hours": round(float(duration), 2),
            "recommendation": suggestion
        })

    return recommendations


# ---------------------------------------------
# Existing AI Delay Prediction API
# ---------------------------------------------

class DelayPredictionRequest(BaseModel):
    priority: str = Field(min_length=1)
    department: str = Field(min_length=1)
    current_stage: str = Field(min_length=1)
    total_activities: int = Field(ge=1, le=10000)
    elapsed_hours: float = Field(ge=0, le=100000)
    assigned_workload: int = Field(ge=1, le=10000)


@app.post("/predict-delay")
def predict_ticket_delay(request: DelayPredictionRequest):
    try:
        result = predict_delay(
            priority=request.priority,
            department=request.department,
            current_stage=request.current_stage,
            total_activities=request.total_activities,
            elapsed_hours=request.elapsed_hours,
            assigned_workload=request.assigned_workload
        )

        return {
            "status": "success",
            "ticket": request.model_dump(),
            "result": result
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Delay prediction failed. Check backend logs."
        ) from exc


# ---------------------------------------------
# New MySQL Ticket APIs
# ---------------------------------------------

class DatabaseTicket(BaseModel):
    ticket_id: str = Field(min_length=1, max_length=50)
    process_name: str = Field(min_length=1, max_length=100)
    status: str = Field(min_length=1, max_length=50)
    priority: str = Field(min_length=1, max_length=30)
    completed_at: datetime | None = None
    delay_hours: float = Field(default=0, ge=0)


@app.post("/database/tickets")
def save_database_ticket(ticket: DatabaseTicket):
    connection = get_db_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        query = """
            INSERT INTO tickets
                (ticket_id, process_name, status, priority,
                 completed_at, delay_hours)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                process_name = VALUES(process_name),
                status = VALUES(status),
                priority = VALUES(priority),
                completed_at = VALUES(completed_at),
                delay_hours = VALUES(delay_hours)
        """

        values = (
            ticket.ticket_id,
            ticket.process_name,
            ticket.status,
            ticket.priority,
            ticket.completed_at,
            ticket.delay_hours
        )

        cursor.execute(query, values)
        connection.commit()

        return {
            "status": "success",
            "message": "Ticket saved to MySQL",
            "ticket_id": ticket.ticket_id
        }

    except mysql.connector.Error as exc:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save ticket to MySQL."
        ) from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


@app.get("/database/tickets")
def get_database_tickets():
    connection = get_db_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, ticket_id, process_name, status, priority,
                   created_at, completed_at, delay_hours
            FROM tickets
            ORDER BY id DESC
        """)

        rows = cursor.fetchall()

        for row in rows:
            for key in ("created_at", "completed_at"):
                if row[key] is not None:
                    row[key] = row[key].isoformat()

        return rows

    except mysql.connector.Error as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read tickets from MySQL."
        ) from exc
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

# ---------------------------------------------
# NEW Anomaly Detection API
# ---------------------------------------------

@app.get("/anomalies")
def detect_anomalies():
    df = load_data()

    # Calculate processing time for each ticket
    ticket_summary = (
        df.groupby("Case_ID")
        .agg(
            Priority=("Priority", "first"),
            Status=("Status", "last"),
            Total_Activities=("Activity", "count"),
            Start_Time=("Timestamp", "min"),
            End_Time=("Timestamp", "max")
        )
        .reset_index()
    )

    ticket_summary["Processing_Hours"] = (
        (
            ticket_summary["End_Time"]
            - ticket_summary["Start_Time"]
        ).dt.total_seconds() / 3600
    )

    # Remove invalid processing times
    ticket_summary = ticket_summary[
        ticket_summary["Processing_Hours"].notna()
        & (ticket_summary["Processing_Hours"] >= 0)
    ].copy()

    if ticket_summary.empty:
        return {
            "status": "success",
            "total_tickets_analyzed": 0,
            "anomaly_count": 0,
            "threshold_hours": None,
            "anomalies": [],
            "message": "No valid tickets available for analysis."
        }

    # Use the IQR statistical method to find unusually
    # long processing times
    q1 = float(ticket_summary["Processing_Hours"].quantile(0.25))
    q3 = float(ticket_summary["Processing_Hours"].quantile(0.75))
    iqr = q3 - q1
    threshold = q3 + (1.5 * iqr)

    # Identify tickets above the calculated threshold
    unusual_tickets = ticket_summary[
        ticket_summary["Processing_Hours"] > threshold
    ].copy()

    # Sort the most unusual tickets first
    unusual_tickets = unusual_tickets.sort_values(
        "Processing_Hours",
        ascending=False
    )

    anomalies = []

    for _, ticket in unusual_tickets.iterrows():
        anomalies.append({
            "ticket_id": str(ticket["Case_ID"]),
            "priority": str(ticket["Priority"]),
            "status": str(ticket["Status"]),
            "total_activities": int(ticket["Total_Activities"]),
            "processing_hours": round(
                float(ticket["Processing_Hours"]), 2
            ),
            "threshold_hours": round(threshold, 2),
            "reason": (
                "Processing time is unusually high "
                "compared with other tickets."
            )
        })

    return {
        "status": "success",
        "method": "IQR (Interquartile Range)",
        "total_tickets_analyzed": int(len(ticket_summary)),
        "anomaly_count": int(len(anomalies)),
        "threshold_hours": round(threshold, 2),
        "anomalies": anomalies,
        "message": (
            "Anomaly detection completed successfully."
        )
    }


# ---------------------------------------------
# NEW Root Cause Analysis API
# ---------------------------------------------

@app.get("/root-cause-analysis")
def root_cause_analysis():
    df = load_data()
    df = df.sort_values(["Case_ID", "Timestamp"]).copy()

    if df.empty:
        return {
            "status": "success",
            "total_tickets_analyzed": 0,
            "tickets_with_possible_causes": 0,
            "results": [],
            "message": "No ticket data available."
        }

    # Calculate time between consecutive activities
    df["Next_Timestamp"] = (
        df.groupby("Case_ID")["Timestamp"].shift(-1)
    )

    df["Wait_Hours"] = (
        (df["Next_Timestamp"] - df["Timestamp"])
        .dt.total_seconds() / 3600
    )

    # Ignore invalid or negative waiting times
    stage_data = df[
        df["Wait_Hours"].notna()
        & (df["Wait_Hours"] >= 0)
    ].copy()

    # Calculate the typical waiting time for each activity
    activity_medians = (
        stage_data.groupby("Activity")["Wait_Hours"]
        .median()
        .to_dict()
    )

    # Summarize each ticket
    summary = (
        df.groupby("Case_ID")
        .agg(
            Priority=("Priority", "first"),
            Status=("Status", "last"),
            Total_Activities=("Activity", "count"),
            Start_Time=("Timestamp", "min"),
            End_Time=("Timestamp", "max")
        )
        .reset_index()
    )

    summary["Processing_Hours"] = (
        (summary["End_Time"] - summary["Start_Time"])
        .dt.total_seconds() / 3600
    )

    summary = summary[
        summary["Processing_Hours"].notna()
        & (summary["Processing_Hours"] >= 0)
    ].copy()

    if summary.empty:
        return {
            "status": "success",
            "total_tickets_analyzed": 0,
            "tickets_with_possible_causes": 0,
            "results": [],
            "message": "No valid processing times found."
        }

    # Find tickets with unusually long overall processing time
    q1 = float(summary["Processing_Hours"].quantile(0.25))
    q3 = float(summary["Processing_Hours"].quantile(0.75))
    overall_threshold = q3 + (1.5 * (q3 - q1))

    # Find tickets with unusually many activities
    activity_q3 = float(
        summary["Total_Activities"].quantile(0.75)
    )
    activity_q1 = float(
        summary["Total_Activities"].quantile(0.25)
    )
    activity_threshold = (
        activity_q3 + 1.5 * (activity_q3 - activity_q1)
    )

    results = []

    for _, ticket in summary.iterrows():
        case_id = ticket["Case_ID"]

        ticket_stages = stage_data[
            stage_data["Case_ID"] == case_id
        ]

        causes = []
        evidence = []
        recommendations = []

        # Cause 1: Long overall processing time
        processing_hours = float(ticket["Processing_Hours"])

        if processing_hours > overall_threshold:
            causes.append("Unusually long overall processing time")
            evidence.append(
                f"Processing took {processing_hours:.2f} hours; "
                f"the dataset threshold is "
                f"{overall_threshold:.2f} hours."
            )
            recommendations.append(
                "Review the ticket timeline and identify "
                "where delays occurred."
            )

        # Cause 2: Long wait after a particular activity
        for _, stage in ticket_stages.iterrows():
            activity = str(stage["Activity"])
            wait_hours = float(stage["Wait_Hours"])
            typical_wait = activity_medians.get(activity, 0)

            # Require both a meaningful wait and a wait
            # longer than the activity's typical median.
            if (
                wait_hours >= 2
                and wait_hours > typical_wait * 1.5
            ):
                causes.append(
                    f"Long waiting time after: {activity}"
                )
                evidence.append(
                    f"{activity}: {wait_hours:.2f} hours "
                    f"until the next recorded activity; "
                    f"typical median is "
                    f"{typical_wait:.2f} hours."
                )
                recommendations.append(
                    f"Investigate handoffs, approvals, and "
                    f"resource availability after {activity}."
                )

        # Cause 3: Unusually many recorded activities
        activity_count = int(ticket["Total_Activities"])

        if activity_count > activity_threshold:
            causes.append("Higher-than-usual activity count")
            evidence.append(
                f"This ticket has {activity_count} activities; "
                f"the dataset threshold is "
                f"{activity_threshold:.2f}."
            )
            recommendations.append(
                "Check for repeated work, reassignments, "
                "or unnecessary process steps."
            )

        # Include only tickets with identified warning signals
        if causes:
            results.append({
                "ticket_id": str(case_id),
                "priority": str(ticket["Priority"]),
                "status": str(ticket["Status"]),
                "total_activities": activity_count,
                "processing_hours": round(processing_hours, 2),
                "possible_root_causes": list(dict.fromkeys(causes)),
                "evidence": list(dict.fromkeys(evidence)),
                "recommendations": list(
                    dict.fromkeys(recommendations)
                )
            })

    results.sort(
        key=lambda item: item["processing_hours"],
        reverse=True
    )

    return {
        "status": "success",
        "method": "Rule-based analysis using event-log statistics",
        "total_tickets_analyzed": int(len(summary)),
        "tickets_with_possible_causes": len(results),
        "results": results,
        "message": (
            "Root cause analysis completed. "
            "Identified causes are possible explanations, "
            "not confirmed facts."
        )
    }
