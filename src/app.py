"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import json
import secrets
import time
from typing import Optional
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")
teacher_sessions = {}
teacher_credentials_path = current_dir / "teachers.json"
session_duration = 8 * 60 * 60


class LoginRequest(BaseModel):
    username: str
    password: str


def get_authenticated_teacher(
    teacher_session: Optional[str] = Cookie(default=None),
):
    session = teacher_sessions.get(teacher_session or "")
    if session is None or session[1] <= time.monotonic():
        teacher_sessions.pop(teacher_session or "", None)
        raise HTTPException(status_code=401, detail="Teacher login required")
    return session[0]


@app.post("/auth/login")
def login(credentials: LoginRequest, request: Request, response: Response):
    try:
        with teacher_credentials_path.open(encoding="utf-8") as credentials_file:
            teacher_credentials = json.load(credentials_file)
    except FileNotFoundError:
        teacher_credentials = {}
    except (OSError, json.JSONDecodeError):
        raise HTTPException(
            status_code=503, detail="Teacher login is not configured correctly"
        )

    if not isinstance(teacher_credentials, dict):
        raise HTTPException(
            status_code=503, detail="Teacher login is not configured correctly"
        )

    password = teacher_credentials.get(credentials.username)
    if not isinstance(password, str) or not secrets.compare_digest(
        password, credentials.password
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_token = secrets.token_urlsafe(32)
    teacher_sessions[session_token] = (
        credentials.username,
        time.monotonic() + session_duration,
    )
    response.set_cookie(
        key="teacher_session",
        value=session_token,
        max_age=session_duration,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
    )
    return {"message": "Teacher login successful", "username": credentials.username}


@app.get("/auth/session")
def get_teacher_session(
    username: str = Depends(get_authenticated_teacher),
):
    return {"username": username}


@app.post("/auth/logout")
def logout(
    response: Response,
    teacher_session: Optional[str] = Cookie(default=None),
):
    teacher_sessions.pop(teacher_session or "", None)
    response.delete_cookie(key="teacher_session", httponly=True, samesite="lax")
    return {"message": "Teacher logout successful"}

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    username: str = Depends(get_authenticated_teacher),
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    username: str = Depends(get_authenticated_teacher),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
