import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import argparse
import datetime
import notifier

def main():
    parser = argparse.ArgumentParser(description="Send Daily Timetable Reminder to Mobile Phone")
    parser.add_argument("--day", type=str, default=None, help="Target day (Monday, Tuesday, etc.). Defaults to today.")
    parser.add_argument("--channel", type=str, default=None, help="Override channel (simulation, callmebot_whatsapp, ntfy_push, twilio_whatsapp, twilio_sms, telegram)")
    parser.add_argument("--dry-run", action="store_true", help="Print the message preview without sending")

    args = parser.parse_args()
    
    target_day = args.day or datetime.datetime.now().strftime("%A")
    config = notifier.load_config()
    active_channel = args.channel or config.get("active_channel", "simulation")
    recipient = config.get("mobile_number", "Not configured")
    
    message = notifier.format_daily_reminder(target_day)
    
    print("=" * 60)
    print(f"🔔 CAMPUSBELL - DAILY TIMETABLE MOBILE DISPATCHER")
    print(f"📅 Target Day: {target_day}")
    print(f"📱 Recipient Mobile: {recipient}")
    print(f"📡 Channel: {active_channel}")
    print("=" * 60)
    print("\n--- MESSAGE PREVIEW ---")
    print(message)
    print("-----------------------\n")
    
    if args.dry_run:
        print("ℹ️ Dry-run mode enabled. No network notification sent.")
        return

    print("🚀 Sending reminder to mobile...")
    result = notifier.dispatch_notification(
        message=message,
        message_type="cli_send",
        override_channel=active_channel
    )
    
    if result.get("success"):
        print(f"✅ Success: {result.get('message', 'Reminder sent successfully!')}")
    else:
        print(f"❌ Failed to deliver: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
