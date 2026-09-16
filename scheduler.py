import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import datetime
from typing import Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import notifier

class TimetableScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(daemon=True)
        self.is_running = False
        self._sent_class_reminders_today = set()
        self._last_day_reset = ""

    def start(self):
        if self.is_running:
            return
        
        config = notifier.load_config()
        rem_time = config.get("daily_reminder_time", "07:30")
        try:
            hour_str, min_str = rem_time.split(":")
            hour, minute = int(hour_str), int(min_str)
        except Exception:
            hour, minute = 7, 30

        # Daily morning briefing job
        self.scheduler.add_job(
            self._job_daily_briefing,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="daily_briefing_job",
            replace_existing=True,
            name="Daily Timetable Morning Briefing"
        )

        # Minutely check for pre-class reminders (e.g. 15 min before class)
        self.scheduler.add_job(
            self._job_check_pre_class,
            trigger="interval",
            minutes=1,
            id="pre_class_checker_job",
            replace_existing=True,
            name="Pre-Class 15-Minute Alert Checker"
        )

        self.scheduler.start()
        self.is_running = True
        print(f"✅ Scheduler started. Daily briefing set for {hour:02d}:{minute:02d}.")

    def stop(self):
        if not self.is_running:
            return
        self.scheduler.shutdown(wait=False)
        self.is_running = False
        print("🛑 Scheduler stopped.")

    def update_daily_time(self, new_time: str):
        try:
            hour_str, min_str = new_time.split(":")
            hour, minute = int(hour_str), int(min_str)
            if self.is_running:
                self.scheduler.reschedule_job(
                    "daily_briefing_job",
                    trigger=CronTrigger(hour=hour, minute=minute)
                )
            print(f"⏰ Rescheduled daily briefing to {hour:02d}:{minute:02d}")
        except Exception as e:
            print(f"Failed to reschedule daily briefing: {e}")

    def _job_daily_briefing(self):
        config = notifier.load_config()
        if not config.get("daily_reminder_enabled", True):
            print("Daily reminder is disabled in config.")
            return
        
        today_name = datetime.datetime.now().strftime("%A")
        message = notifier.format_daily_reminder(today_name)
        result = notifier.dispatch_notification(message, message_type="daily_scheduled")
        print(f"[{datetime.datetime.now()}] Daily briefing dispatched for {today_name}: {result}")

    def _job_check_pre_class(self):
        config = notifier.load_config()
        if not config.get("pre_class_reminder_enabled", True):
            return
        
        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        if self._last_day_reset != today_str:
            self._sent_class_reminders_today.clear()
            self._last_day_reset = today_str

        today_name = now.strftime("%A")
        classes = notifier.get_classes_for_day(today_name)
        minutes_before = int(config.get("pre_class_reminder_minutes", 15))

        for c in classes:
            class_id = c.get("id")
            if class_id in self._sent_class_reminders_today:
                continue

            start_24 = c.get("start24", "")
            if not start_24 or ":" not in start_24:
                continue

            try:
                ch, cm = map(int, start_24.split(":"))
                class_start_dt = now.replace(hour=ch, minute=cm, second=0, microsecond=0)
                diff_seconds = (class_start_dt - now).total_seconds()
                diff_minutes = diff_seconds / 60.0

                # If class starts in [minutes_before - 1, minutes_before + 1]
                if 0 <= diff_minutes <= (minutes_before + 1.0) and diff_minutes >= (minutes_before - 1.5):
                    message = notifier.format_class_reminder(c, minutes_before=minutes_before)
                    notifier.dispatch_notification(message, message_type=f"pre_class_{class_id}")
                    self._sent_class_reminders_today.add(class_id)
                    print(f"[{now}] Pre-class reminder sent for {c.get('subject')} ({c.get('venue')})")
            except Exception as e:
                print(f"Error checking pre-class for {c}: {e}")

    def trigger_daily_now(self, target_day: Optional[str] = None) -> Dict[str, Any]:
        today_name = target_day or datetime.datetime.now().strftime("%A")
        message = notifier.format_daily_reminder(today_name)
        return notifier.dispatch_notification(message, message_type="manual_trigger")

    def get_status(self) -> Dict[str, Any]:
        next_run_str = "None"
        if self.is_running:
            job = self.scheduler.get_job("daily_briefing_job")
            if job and job.next_run_time:
                next_run_str = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")

        today_name = datetime.datetime.now().strftime("%A")
        classes_today = notifier.get_classes_for_day(today_name)

        return {
            "is_running": self.is_running,
            "next_daily_run": next_run_str,
            "current_day": today_name,
            "classes_today_count": len(classes_today),
            "classes_today": classes_today
        }

# Global singleton
scheduler_instance = TimetableScheduler()
