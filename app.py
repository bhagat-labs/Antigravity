import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import notifier
from scheduler import scheduler_instance

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the scheduler on app startup
    try:
        scheduler_instance.start()
    except Exception as e:
        print(f"Failed to auto-start scheduler: {e}")
    yield
    # Shutdown scheduler on app shutdown
    try:
        scheduler_instance.stop()
    except Exception:
        pass

app = FastAPI(title="CampusBell - Daily Timetable Reminder", lifespan=lifespan)

# Mount static files
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "Frontend static file index.html is being created."})


@app.get("/api/timetable")
async def get_timetable():
    timetable = notifier.load_timetable()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    by_day = {d: [c for c in timetable if c.get("day", "").lower() == d.lower()] for d in days}
    clubbed_by_day = {d: notifier.get_classes_for_day(d, club_labs=True) for d in days}
    all_clubbed = []
    for d in days:
        all_clubbed.extend(clubbed_by_day[d])
    return {
        "timetable": timetable,
        "by_day": by_day,
        "clubbed_by_day": clubbed_by_day,
        "clubbed_timetable": all_clubbed,
        "total_classes": len(timetable),
        "total_clubbed_sessions": len(all_clubbed)
    }


@app.post("/api/timetable")
async def update_timetable(data: list = Body(...)):
    try:
        notifier.save_timetable(data)
        return {"success": True, "message": "Timetable updated successfully", "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/config")
async def get_config():
    return notifier.load_config()


@app.post("/api/config")
async def save_config(cfg: Dict[str, Any] = Body(...)):
    try:
        old_cfg = notifier.load_config()
        notifier.save_config(cfg)
        
        # If daily reminder time changed, reschedule job
        new_time = cfg.get("daily_reminder_time")
        if new_time and new_time != old_cfg.get("daily_reminder_time"):
            scheduler_instance.update_daily_time(new_time)
            
        return {"success": True, "message": "Configuration saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/status")
async def get_status():
    status = scheduler_instance.get_status()
    logs = notifier.get_logs()
    config = notifier.load_config()
    return {
        "scheduler": status,
        "active_channel": config.get("active_channel", "simulation"),
        "mobile_number": config.get("mobile_number", ""),
        "daily_reminder_time": config.get("daily_reminder_time", "07:30"),
        "recent_logs": logs[:15]
    }


class SendNowRequest(BaseModel):
    day: Optional[str] = None
    channel: Optional[str] = None

@app.post("/api/send-now")
async def send_now(payload: Optional[SendNowRequest] = None):
    try:
        target_day = payload.day if payload and payload.day else None
        target_channel = payload.channel if payload and payload.channel else None
        
        import datetime
        day_name = target_day or datetime.datetime.now().strftime("%A")
        message = notifier.format_daily_reminder(day_name)
        
        result = notifier.dispatch_notification(
            message,
            message_type="manual_send",
            override_channel=target_channel
        )
        return {
            "success": result.get("success", False),
            "result": result,
            "day": day_name,
            "preview": message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PreviewRequest(BaseModel):
    day: Optional[str] = "Monday"

@app.post("/api/preview")
async def preview_message(payload: Optional[PreviewRequest] = None):
    day = payload.day if payload and payload.day else "Monday"
    msg = notifier.format_daily_reminder(day)
    return {"day": day, "formatted_message": msg}


@app.post("/api/scheduler/toggle")
async def toggle_scheduler():
    if scheduler_instance.is_running:
        scheduler_instance.stop()
        state = False
    else:
        scheduler_instance.start()
        state = True
    return {"success": True, "is_running": state}


@app.get("/api/logs")
async def get_logs_endpoint():
    return {"logs": notifier.get_logs()}

@app.get("/api/health-ping")
def health_ping():
    return {"status": "ok", "ping": "active"}

from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "online", "message": "CampusBell manual mode ready"}

@app.get("/api/send-now")
def manual_trigger():
    # Place your notification logic/script execution here
    return {"success": True, "message": "Notification dispatched manually!"}

# This handler allows Netlify to route requests into FastAPI
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting CampusBell Timetable Reminder App on http://127.0.0.1:8000")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
