import os
import json
import urllib.parse
import datetime
import csv
import io
import re
import requests
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TIMETABLE_FILE = os.path.join(BASE_DIR, "timetable_data.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOGS_FILE = os.path.join(BASE_DIR, "reminder_logs.json")
MARKS_FILE = os.path.join(BASE_DIR, "marks_data.json")


def load_timetable() -> List[Dict[str, Any]]:
    if not os.path.exists(TIMETABLE_FILE):
        return []
    with open(TIMETABLE_FILE, "r", encoding="utf-8") as f:
        timetable = json.load(f)

    # Repair spreadsheet imports that used blank cells for repeated days.
    current_day = ""
    repaired = []
    for item in timetable:
        normalized = dict(item)
        if normalized.get("day", "").strip():
            current_day = normalized["day"].strip().capitalize()
        elif current_day:
            normalized["day"] = current_day
        repaired.append(normalized)
    return repaired


def save_timetable(data: List[Dict[str, Any]]) -> None:
    with open(TIMETABLE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_marks() -> Dict[str, Any]:
    if not os.path.exists(MARKS_FILE):
        return {"semesters": []}
    try:
        with open(MARKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"semesters": data.get("semesters", [])}
    except Exception:
        return {"semesters": []}


def save_marks(data: Dict[str, Any]) -> None:
    semesters = data.get("semesters", [])
    if not isinstance(semesters, list):
        raise ValueError("semesters must be a list")
    with open(MARKS_FILE, "w", encoding="utf-8") as f:
        json.dump({"semesters": semesters}, f, indent=2)


def parse_csv_timetable(raw_content: str) -> List[Dict[str, Any]]:
    """Parses raw CSV or TSV content into standard timetable session dictionaries."""
    cleaned_content = raw_content.strip()
    if not cleaned_content:
        return []
    
    f = io.StringIO(cleaned_content)
    # Auto-detect delimiter (comma for CSV, tab for TSV)
    try:
        sample = f.read(2048)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample)
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ',' if ',' in cleaned_content else '\t'
        
    reader = csv.DictReader(f, delimiter=delimiter)
    timetable = []
    
    current_day = "Monday"
    for idx, row in enumerate(reader):
        norm_row = {
            re.sub(r"[^a-z0-9]", "", str(k).strip().lower()): (v or "").strip()
            for k, v in row.items() if k
        }

        # Spreadsheet exports usually leave repeated day cells blank.
        day = norm_row.get("day") or current_day
        current_day = day.capitalize()

        raw_time = norm_row.get("time") or norm_row.get("starttime") or norm_row.get("start_time")
        start_time, end_time = _parse_time_range(raw_time)
        start24 = norm_row.get("start24") or norm_row.get("start_24")

        if not start24:
            start24 = _time_to_24(start_time) or "08:00"

        subject = norm_row.get("subject") or norm_row.get("course") or "Untitled Course"
        raw_type = norm_row.get("classtype") or norm_row.get("classname") or norm_row.get("type") or "Theory"
        slots = norm_row.get("slots") or norm_row.get("slot") or ""
        class_type = _normalize_class_type(raw_type, slots)
        venue = norm_row.get("venue") or norm_row.get("room") or "TBD"

        if not end_time:
            duration = 100 if re.search(r"\bL\d+\b", slots, re.IGNORECASE) else 50
            end24 = _add_minutes(start24, duration)
            end_time = _format_time(end24)
        else:
            end24 = _time_to_24(end_time) or _add_minutes(start24, 50)
        
        item = {
            "id": f"text_{idx+1}",
            "day": current_day,
            "startTime": start_time,
            "endTime": end_time,
            "start24": start24,
            "end24": end24,
            "subject": subject,
            "classType": class_type,
            "venue": venue
        }
        timetable.append(item)
    return timetable


def _time_to_24(value: str) -> Optional[str]:
    """Convert common 12/24-hour timetable values to HH:MM."""
    if not value:
        return None
    cleaned = value.strip().upper().replace(".", "")
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?", cleaned)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or "00")
    meridiem = match.group(3)
    if meridiem == "PM" and hour < 12:
        hour += 12
    elif meridiem == "AM" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _parse_time_range(value: str) -> tuple[str, str]:
    """Return display start/end values when a cell contains a time range."""
    if not value:
        return "08:00 AM", ""
    parts = re.split(r"\s+(?:-|to)\s+", value.strip(), maxsplit=1, flags=re.IGNORECASE)
    return parts[0].strip(), parts[1].strip() if len(parts) == 2 else ""


def _add_minutes(start24: str, minutes: int) -> str:
    start = datetime.datetime.strptime(start24, "%H:%M")
    return (start + datetime.timedelta(minutes=minutes)).strftime("%H:%M")


def _format_time(value24: str) -> str:
    return datetime.datetime.strptime(value24, "%H:%M").strftime("%I:%M %p")


def _normalize_class_type(raw_type: str, slots: str) -> str:
    """Map common timetable abbreviations to the UI's Lab/Theory values."""
    value = raw_type.strip().lower()
    if value in {"lab", "labs", "lo", "ela"} or re.search(r"\bL\d+\b", slots, re.IGNORECASE):
        return "Lab"
    return "Theory"


def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_FILE):
        return {
            "mobile_number": "",
            "active_channel": "simulation",
            "daily_reminder_enabled": True,
            "daily_reminder_time": "07:30",
            "pre_class_reminder_enabled": True,
            "pre_class_reminder_minutes": 15,
            "timezone": "Asia/Kolkata",
            "callmebot": {"phone": "", "api_key": ""},
            "ntfy": {"topic": "timetable_reminders_campus", "server": "https://ntfy.sh"},
            "twilio": {"account_sid": "", "auth_token": "", "phone_number": "", "whatsapp_sender": "whatsapp:+14155238886"},
            "telegram": {"bot_token": "", "chat_id": ""}
        }
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: Dict[str, Any]) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def get_logs() -> List[Dict[str, Any]]:
    if not os.path.exists(LOGS_FILE):
        return []
    try:
        with open(LOGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def log_event(status: str, channel: str, recipient: str, message_type: str, preview: str, error: Optional[str] = None):
    logs = get_logs()
    entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "channel": channel,
        "recipient": recipient,
        "type": message_type,
        "preview": preview[:160] + ("..." if len(preview) > 160 else ""),
        "full_message": preview,
        "error": error
    }
    logs.insert(0, entry)
    logs = logs[:100]
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


def club_continuous_labs(classes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not classes:
        return []
    
    sorted_classes = sorted(classes, key=lambda x: x.get("start24", "00:00"))
    clubbed = []
    i = 0
    while i < len(sorted_classes):
        curr = dict(sorted_classes[i])
        is_curr_lab = curr.get("classType", "").strip().lower() == "lab"
        
        if is_curr_lab and (i + 1) < len(sorted_classes):
            nxt = sorted_classes[i + 1]
            is_nxt_lab = nxt.get("classType", "").strip().lower() == "lab"
            same_subject = curr.get("subject", "").strip().lower() == nxt.get("subject", "").strip().lower()
            same_venue = curr.get("venue", "").strip() == nxt.get("venue", "").strip()
            continuous_time = (curr.get("end24") == nxt.get("start24") or curr.get("endTime") == nxt.get("startTime"))
            
            if is_nxt_lab and same_subject and same_venue and continuous_time:
                base_subj = curr.get("subject", "").strip()
                lab_title = base_subj if base_subj.lower().endswith("lab") else f"{base_subj} Lab"
                merged = {
                    "id": f"{curr.get('id')}_{nxt.get('id')}",
                    "day": curr.get("day"),
                    "startTime": curr.get("startTime"),
                    "endTime": nxt.get("endTime"),
                    "start24": curr.get("start24"),
                    "end24": nxt.get("end24"),
                    "subject": lab_title,
                    "originalSubject": base_subj,
                    "classType": "Lab",
                    "venue": curr.get("venue"),
                    "isClubbed": True,
                    "periodsCount": 2
                }
                clubbed.append(merged)
                i += 2
                continue
        
        base_subj = curr.get("subject", "").strip()
        if is_curr_lab and not base_subj.lower().endswith("lab"):
            curr["subject"] = f"{base_subj} Lab"
            curr["originalSubject"] = base_subj
        clubbed.append(curr)
        i += 1
        
    return clubbed


def get_classes_for_day(day_name: str, club_labs: bool = True) -> List[Dict[str, Any]]:
    timetable = load_timetable()
    classes = [c for c in timetable if c.get("day", "").strip().lower() == day_name.strip().lower()]
    classes.sort(key=lambda x: x.get("start24", "00:00"))
    if club_labs:
        return club_continuous_labs(classes)
    return classes


def format_daily_reminder(day_name: str, classes: Optional[List[Dict[str, Any]]] = None) -> str:
    if classes is None:
        classes = get_classes_for_day(day_name, club_labs=True)
    
    today_date_str = datetime.datetime.now().strftime("%d %b %Y")
    
    if not classes:
        return (
            f"🎓 *DAILY TIMETABLE REMINDER*\n"
            f"📅 *{day_name}, {today_date_str}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✨ No classes scheduled for today!\n"
            f"Enjoy your day off, recharge, and catch up on personal projects! 🎉"
        )
    
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    lines = [
        f"🎓 *DAILY CLASS TIMETABLE*",
        f"📅 *{day_name} • {today_date_str}*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"Good morning! You have *{len(classes)} session{'s' if len(classes) != 1 else ''}* scheduled today:\n"
    ]
    
    for idx, c in enumerate(classes):
        num = number_emojis[idx] if idx < len(number_emojis) else f"#{idx+1}"
        is_lab = c.get("classType", "").lower() == "lab"
        
        if is_lab:
            type_tag = "🔬 Lab"
            if c.get("isClubbed"):
                type_tag = "🔬 2-Period Lab"
            lines.append(f"{num} ⏰ *{c['startTime']} – {c['endTime']}*")
            lines.append(f"   🔬 *{c['subject']}* ({type_tag})")
        else:
            lines.append(f"{num} ⏰ *{c['startTime']} – {c['endTime']}*")
            lines.append(f"   📚 *{c['subject']}* (📝 Theory)")
            
        lines.append(f"   📍 *Venue:* {c['venue']}")
        lines.append("")
        
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 *Tip:* Check your labs/materials before heading out.")
    lines.append("Have an inspiring and productive day! 🚀")
    
    return "\n".join(lines)


def format_class_reminder(class_item: Dict[str, Any], minutes_before: int = 15) -> str:
    class_type_tag = "🔬 Lab" if class_item.get("classType", "").lower() == "lab" else "📝 Theory"
    return (
        f"🔔 *UPCOMING CLASS ALERT ({minutes_before} mins)*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ Time: *{class_item['startTime']} – {class_item['endTime']}*\n"
        f"📚 Subject: *{class_item['subject']}* ({class_type_tag})\n"
        f"📍 Venue: *{class_item['venue']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Head to {class_item['venue']} now so you arrive on time! 🏃‍♂️💨"
    )


def send_via_callmebot(phone: str, api_key: str, message: str) -> Dict[str, Any]:
    if not phone or not api_key:
        raise ValueError("CallMeBot requires phone number and API key.")
    
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    encoded_text = urllib.parse.quote(message.encode("utf-8"))
    url = f"https://api.callmebot.com/whatsapp.php?phone={clean_phone}&text={encoded_text}&apikey={api_key}"
    
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200 and "Error" not in resp.text:
        return {"success": True, "message": "WhatsApp delivered via CallMeBot", "response": resp.text}
    else:
        raise RuntimeError(f"CallMeBot Error: {resp.text or resp.status_code}")


def send_via_ntfy(topic: str, server: str, message: str, title: str = "CampusBell Timetable Reminder") -> Dict[str, Any]:
    if not topic:
        raise ValueError("ntfy requires a topic name.")
    
    server_url = server.rstrip("/") if server else "https://ntfy.sh"
    post_url = f"{server_url}/{topic}"
    
    safe_title = "".join(ch for ch in title if ord(ch) < 128).strip() or "CampusBell Timetable"
    headers = {
        "Title": safe_title,
        "Tags": "mortar_board,calendar,books",
        "Priority": "high"
    }
    
    resp = requests.post(post_url, data=message.encode("utf-8"), headers=headers, timeout=15)
    if resp.status_code in [200, 201]:
        return {"success": True, "message": f"Mobile push notification sent to ntfy topic: {topic}"}
    else:
        raise RuntimeError(f"ntfy error ({resp.status_code}): {resp.text}")


def send_via_twilio(to_number: str, message: str, account_sid: str, auth_token: str, from_number: str, is_whatsapp: bool = False) -> Dict[str, Any]:
    if not account_sid or not auth_token:
        raise ValueError("Twilio requires Account SID and Auth Token.")
    
    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        
        target_to = f"whatsapp:{to_number}" if is_whatsapp and not to_number.startswith("whatsapp:") else to_number
        target_from = from_number
        if is_whatsapp and not target_from.startswith("whatsapp:"):
            target_from = f"whatsapp:{target_from}"
            
        msg = client.messages.create(
            body=message,
            from_=target_from,
            to=target_to
        )
        return {"success": True, "message": f"Twilio message sent with SID: {msg.sid}"}
    except Exception as e:
        raise RuntimeError(f"Twilio delivery failed: {str(e)}")


def send_via_telegram(bot_token: str, chat_id: str, message: str) -> Dict[str, Any]:
    if not bot_token or not chat_id:
        raise ValueError("Telegram requires Bot Token and Chat ID.")
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    resp = requests.post(url, json=payload, timeout=15)
    data = resp.json()
    if data.get("ok"):
        return {"success": True, "message": "Telegram message delivered"}
    else:
        raise RuntimeError(f"Telegram error: {data.get('description', 'Unknown error')}")


def dispatch_notification(
    message: str,
    message_type: str = "daily",
    override_channel: Optional[str] = None
) -> Dict[str, Any]:
    config = load_config()
    channel = override_channel or config.get("active_channel", "simulation")
    recipient = config.get("mobile_number", "")
    
    try:
        if channel == "simulation":
            result = {
                "success": True,
                "message": f"[Simulation Mode] Reminder rendered successfully for {recipient or 'phone number'}",
                "simulated": True
            }
        elif channel == "callmebot_whatsapp":
            cb_cfg = config.get("callmebot", {})
            phone = cb_cfg.get("phone") or recipient
            api_key = cb_cfg.get("api_key")
            result = send_via_callmebot(phone, api_key, message)
        elif channel == "ntfy_push":
            ntfy_cfg = config.get("ntfy", {})
            topic = ntfy_cfg.get("topic")
            server = ntfy_cfg.get("server", "https://ntfy.sh")
            result = send_via_ntfy(topic, server, message, title="CampusBell Timetable Reminder")
        elif channel == "twilio_whatsapp":
            tw_cfg = config.get("twilio", {})
            to_num = recipient
            sid = tw_cfg.get("account_sid")
            token = tw_cfg.get("auth_token")
            sender = tw_cfg.get("whatsapp_sender", "whatsapp:+14155238886")
            result = send_via_twilio(to_num, message, sid, token, sender, is_whatsapp=True)
        elif channel == "twilio_sms":
            tw_cfg = config.get("twilio", {})
            to_num = recipient
            sid = tw_cfg.get("account_sid")
            token = tw_cfg.get("auth_token")
            sender = tw_cfg.get("phone_number")
            result = send_via_twilio(to_num, message, sid, token, sender, is_whatsapp=False)
        elif channel == "telegram":
            tg_cfg = config.get("telegram", {})
            bot_token = tg_cfg.get("bot_token")
            chat_id = tg_cfg.get("chat_id")
            result = send_via_telegram(bot_token, chat_id, message)
        else:
            raise ValueError(f"Unknown notification channel: {channel}")
        
        log_event("SUCCESS", channel, recipient or "N/A", message_type, message)
        return result
    except Exception as e:
        err_msg = str(e)
        log_event("FAILED", channel, recipient or "N/A", message_type, message, error=err_msg)
        return {"success": False, "error": err_msg}