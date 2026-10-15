
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# -------------------------------------------------
# 1. Generate DEMO training data
# Replace this with historical ticket data later.
# -------------------------------------------------

def create_training_data(number_of_tickets=1000):
    rng = np.random.default_rng(42)

    priorities = rng.choice(
        ["Low", "Medium", "High"],
        size=number_of_tickets,
        p=[0.25, 0.45, 0.30],
    )

    departments = rng.choice(
        ["IT Support", "Development", "Testing"],
        size=number_of_tickets,
    )

    stages = rng.choice(
        [
            "Ticket Created",
            "Ticket Assigned",
            "Investigation Started",
            "Developer Assigned",
            "Fix Completed",
            "Testing Completed",
        ],
        size=number_of_tickets,
    )

    total_activities = rng.integers(1, 15, size=number_of_tickets)
    elapsed_hours = rng.uniform(0.5, 60, size=number_of_tickets)
    assigned_workload = rng.integers(1, 12, size=number_of_tickets)

    # Synthetic rule to create demo labels.
    # This is not a learned rule from your five real tickets.
    risk_score = (
        (elapsed_hours >= 24).astype(int)
        + (total_activities >= 8).astype(int)
        + (assigned_workload >= 7).astype(int)
        + (priorities == "High").astype(int)
        + np.isin(
            stages,
            ["Developer Assigned", "Fix Completed"],
        ).astype(int)
    )

    delayed = (risk_score >= 3).astype(int)

    return pd.DataFrame({
        "priority": priorities,
        "department": departments,
        "current_stage": stages,
        "total_activities": total_activities,
        "elapsed_hours": elapsed_hours.round(2),
        "assigned_workload": assigned_workload,
        "delayed": delayed,
    })


# -------------------------------------------------
# 2. Train the machine learning model
# -------------------------------------------------

CATEGORICAL_FEATURES = [
    "priority",
    "department",
    "current_stage",
]

NUMERICAL_FEATURES = [
    "total_activities",
    "elapsed_hours",
    "assigned_workload",
]

ALL_FEATURES = CATEGORICAL_FEATURES + NUMERICAL_FEATURES


def train_delay_model():
    data = create_training_data()

    X = data[ALL_FEATURES]
    y = data["delayed"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
            (
                "numerical",
                "passthrough",
                NUMERICAL_FEATURES,
            ),
        ]
    )

    model = Pipeline([
        ("preprocessing", preprocessing),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=150,
                random_state=42,
                class_weight="balanced",
            ),
        ),
    ])

    model.fit(X_train, y_train)

    accuracy = model.score(X_test, y_test)

    print("Delay Prediction Model trained successfully.")
    print(f"Demo test accuracy: {accuracy:.2%}")
    print("IMPORTANT: Accuracy is on synthetic demo data.")

    return model


# Train once when the module is imported.
delay_model = train_delay_model()


# -------------------------------------------------
# 3. Predict delay risk for a ticket
# -------------------------------------------------

def predict_delay(
    priority,
    department,
    current_stage,
    total_activities,
    elapsed_hours,
    assigned_workload,
):
    ticket = pd.DataFrame([{
        "priority": priority,
        "department": department,
        "current_stage": current_stage,
        "total_activities": total_activities,
        "elapsed_hours": elapsed_hours,
        "assigned_workload": assigned_workload,
    }])

    probabilities = delay_model.predict_proba(ticket[ALL_FEATURES])[0]
    classes = list(delay_model.named_steps["classifier"].classes_)

    delayed_probability = float(probabilities[classes.index(1)])

    return {
        "delay_probability": round(delayed_probability * 100, 2),
        "prediction": (
            "Delay Risk"
            if delayed_probability >= 0.5
            else "Lower Delay Risk"
        ),
        "model_type": "Random Forest Classifier",
        "training_data": "Synthetic demonstration data",
        "disclaimer": (
            "Demo prediction only. Validate with historical ticket "
            "outcomes before using for real decisions."
        ),
    }
