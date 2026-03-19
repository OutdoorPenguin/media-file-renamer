# notifier.py
# Sends a Slack summary message after clips are ingested
# Requires a .env file with SLACK_TOKEN set

import requests
from dotenv import load_dotenv
import os

load_dotenv("/Users/rachmcintire/PycharmProjects/Claude/.env")

# --- SETTINGS ---
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
CHANNEL = "dailies-log"

def send_slack_message(message):
    """Sends a message to a Slack channel."""
    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        json={"channel": CHANNEL, "text": message}
    )
    return response.json()

def build_summary(show, episode, shoot_date, clips, issues):
    """Builds a formatted summary message."""
    lines = [
        f"🎬 *{show}* | Ep {episode} | {shoot_date}",
        f"{len(clips)} clips ingested",
    ]

    codecs = set(c["codec"] for c in clips)
    resolutions = set(c["resolution"] for c in clips)
    fps_values = set(c["fps"] for c in clips)

    lines.append(f"Codec: {', '.join(codecs)} | Resolution: {', '.join(resolutions)} | FPS: {', '.join(str(f) for f in fps_values)}")

    if len(codecs) > 1:
        lines.append(f"⚠️ Mixed codecs: {', '.join(codecs)}")
    if len(resolutions) > 1:
        lines.append(f"⚠️ Mixed resolutions: {', '.join(resolutions)}")
    if len(fps_values) > 1:
        lines.append(f"⚠️ Mixed frame rates: {', '.join(str(f) for f in fps_values)}")
    if issues:
        lines.append(f"⚠️ {len(issues)} ingest issue(s) flagged")

    return "\n".join(lines)
