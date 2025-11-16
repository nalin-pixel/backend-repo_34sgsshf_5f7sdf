import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import AppUser, PracticeSession, Attempt, Achievement, TutorialStep

app = FastAPI(title="Shove Trick Trainer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Shove Trainer API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# -------- Tutorial content (static for now) --------
@app.get("/api/tutorial", response_model=List[TutorialStep])
def get_tutorial():
    return [
        TutorialStep(
            step=1,
            title="Stance & Setup",
            description="Place your back foot on the tail and front foot near the bolts. Keep shoulders parallel.",
            tips=["Bend your knees", "Keep weight centered", "Look where you want the board to go"],
            angle="side",
            duration_sec=8,
            speed_label="1x"
        ),
        TutorialStep(
            step=2,
            title="Pop & Scoop",
            description="Pop the tail and scoop your back foot horizontally to initiate the shove.",
            tips=["Scoop, don't kick straight down", "Stay over the board", "Let the board rotate under you"],
            angle="rear",
            duration_sec=10,
            speed_label="0.5x"
        ),
        TutorialStep(
            step=3,
            title="Catch & Roll Away",
            description="Catch the board with your front foot, then set your back foot and roll away clean.",
            tips=["Absorb impact", "Level out mid-air", "Commit with both feet"],
            angle="front",
            duration_sec=7,
            speed_label="0.75x"
        ),
    ]

# -------- Users --------
@app.post("/api/users", status_code=201)
def create_user(user: AppUser):
    user_id = create_document("appuser", user)
    return {"id": user_id}

# -------- Practice logging & progression --------
class SessionFeedback(BaseModel):
    xp_earned: int
    streak: int
    badges_unlocked: List[str]
    milestone: Optional[str] = None

@app.post("/api/practice", response_model=SessionFeedback)
def log_practice(session: PracticeSession):
    # store practice session
    create_document("practicesession", session)

    # Simple progression logic
    xp = min(50, session.duration_min // 5 + session.attempts // 10 + (session.technique_score // 10))

    # compute current streak (sessions on consecutive days)
    docs = get_documents("practicesession", {"user_id": session.user_id})
    dates = sorted({str(d.get("performed_at") or d.get("created_at")).split("T")[0] for d in docs})
    streak = 1 if dates else 0
    if dates:
        # Walk from last backwards
        today = datetime.now(timezone.utc).date()
        # count consecutive days including today if present
        count = 0
        day = today
        date_set = {datetime.fromisoformat(dt + "T00:00:00+00:00").date() for dt in dates if dt}
        while day in date_set:
            count += 1
            day = day.fromordinal(day.toordinal() - 1)
        streak = count

    badges: List[str] = []
    milestone = None
    if session.technique_score >= 60:
        badges.append("Clean Pop")
    if session.attempts >= 50:
        badges.append("Grinder")
    if streak and streak % 7 == 0:
        milestone = f"{streak}-Day Streak!"

    # Record achievements if any
    for b in badges:
        create_document("achievement", Achievement(
            user_id=session.user_id,
            key=b.lower().replace(" ", "-"),
            title=b,
            description=f"Unlocked by session on {datetime.now(timezone.utc).date()}",
            icon="⭐"
        ))

    return SessionFeedback(xp_earned=xp, streak=streak, badges_unlocked=badges, milestone=milestone)

# -------- Attempts feed (social) --------
@app.post("/api/attempts")
def share_attempt(attempt: Attempt):
    attempt_id = create_document("attempt", attempt)
    return {"id": attempt_id}

@app.get("/api/attempts")
def list_attempts(limit: int = 20):
    docs = get_documents("attempt", {}, limit=limit)
    # format basic shape
    for d in docs:
        d["id"] = str(d.get("_id"))
        d.pop("_id", None)
    return docs

# -------- Leaderboard (simple derived) --------
@app.get("/api/leaderboard")
def leaderboard(limit: int = 20):
    sessions = get_documents("practicesession", {})
    score = {}
    for s in sessions:
        uid = s.get("user_id")
        score[uid] = score.get(uid, 0) + int(s.get("technique_score", 0)) + int(s.get("attempts", 0) // 10)
    ranks = sorted(([uid, pts] for uid, pts in score.items()), key=lambda x: x[1], reverse=True)[:limit]
    return [{"user_id": uid, "points": pts, "rank": i + 1} for i, (uid, pts) in enumerate(ranks)]

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
