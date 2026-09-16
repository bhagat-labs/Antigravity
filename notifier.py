import os
import json
import urllib.parse
import datetime
import requests
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TIMETABLE_FILE = os.path.join(BASE_DIR, "timetable_data.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOGS_FILE = os.path.join(BASE_DIR, "reminder_logs.json")


def load_timetable() -> List[Dict[str, Any]]:
    if not os.path.exists(TIMETABLE_FILE):
        return []
    with open(TIMETABLE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_timetable(data: List[Dict[str, Any]]) -> None:
    with open(TIMETABLE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


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
    # keep last 100 entries
    logs = logs[:100]
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


def club_continuous_labs(classes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not classes:
        return []
    
    # Sort chronologically by start24
    sorted_classes = sorted(classes, key=lambda x: x.get("start24", "00:00"))
    clubbed = []
    i = 0
    while i < len(sorted_classes):
        curr = dict(sorted_classes[i])
        is_curr_lab = curr.get("classType", "").strip().lower() == "lab"
        
        # Check if next class is continuous lab of the same subject & venue
        if is_curr_lab and (i + 1) < len(sorted_classes):
            nxt = sorted_classes[i + 1]
            is_nxt_lab = nxt.get("classType", "").strip().lower() == "lab"
            same_subject = curr.get("subject", "").strip().lower() == nxt.get("subject", "").strip().lower()
            same_venue = curr.get("venue", "").strip() == nxt.get("venue", "").strip()
            continuous_time = (curr.get("end24") == nxt.get("start24") or curr.get("endTime") == nxt.get("startTime"))
            
            if is_nxt_lab and same_subject and same_venue and continuous_time:
                # Merge 2 continuous lab periods into one combined block
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
        
        # Single period (or non-lab)
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


# --- Sender Drivers ---

def send_via_callmebot(phone: str, api_key: str, message: str) -> Dict[str, Any]:
    if not phone or not api_key:
        raise ValueError("CallMeBot requires phone number and API key.")
    
    # Strip any leading '+' or spaces
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
    
    # HTTP headers in Python's http.client require ASCII/latin-1. Strip non-ASCII from header:
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


# --- Central Notification Dispatcher ---

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
