import sys
import os
import time
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
import datetime
import zoneinfo
import telegram
from telegram.error import Conflict
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from config import load_config
from session_manager import broadcast_pre_session, broadcast_session
from admin_panel import (
    start_command,
    myid_command,
    help_command,
    status_command,
    set_times_command,
    set_winrate_command,
    set_gametitle_command,
    channels_command,
    add_channel_command,
    del_channel_command,
    set_round_command,
    pause_command,
    resume_command,
    preview_command,
    set_prepost_command,
    set_postpost_command,
    set_winsticker_command,
    set_losssticker_command,
    cancel_command,
    start_session_command,
    send_prepost_command,
    send_postpost_command,
    admin_message_collector,
    button_callback_handler
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("WingoPredictionBot")

# Indian Standard Time (IST) Zone
IST = zoneinfo.ZoneInfo("Asia/Kolkata")


# --- DAILY SCHEDULER CALLBACKS ---

async def daily_prepost_callback(context):
    logger.info("Executing scheduled PRE-SESSION post broadcast...")
    config = load_config()
    await broadcast_pre_session(context.bot, config)


async def daily_session_callback(context):
    logger.info("Executing scheduled 6-ROUND PREDICTION SESSION broadcast...")
    config = load_config()
    await broadcast_session(context.bot, config)


def schedule_all_daily_jobs(job_queue, config: dict):
    """Schedules pre-posts and sessions for all configured times in session_times."""
    if not job_queue:
        return

    # Remove existing daily jobs
    existing = [j for j in job_queue.jobs() if j.name and j.name.startswith("daily_")]
    for j in existing:
        j.schedule_removal()

    session_cfg = config.get("session_settings", {})
    times_list = session_cfg.get("session_times", ["11:00", "23:00"])
    offset_mins = int(session_cfg.get("pre_post_minutes_before", 30))

    logger.info(f"Scheduling daily sessions for times: {times_list} (pre-post {offset_mins}m before)")

    for t_str in times_list:
        try:
            parts = t_str.strip().split(":")
            h, m = int(parts[0]), int(parts[1])
            sess_time = datetime.time(hour=h, minute=m, tzinfo=IST)

            ref_dt = datetime.datetime(2000, 1, 1, h, m) - datetime.timedelta(minutes=offset_mins)
            pre_time = datetime.time(hour=ref_dt.hour, minute=ref_dt.minute, tzinfo=IST)

            job_queue.run_daily(
                daily_prepost_callback,
                time=pre_time,
                name=f"daily_prepost_{h:02d}_{m:02d}"
            )
            job_queue.run_daily(
                daily_session_callback,
                time=sess_time,
                name=f"daily_session_{h:02d}_{m:02d}"
            )
            logger.info(f"Scheduled Daily Session at {sess_time.strftime('%I:%M %p')} IST (Pre-post at {pre_time.strftime('%I:%M %p')} IST)")
        except Exception as e:
            logger.error(f"Error scheduling time {t_str}: {e}")


async def post_init(application):
    """Initializes daily jobs on bot launch."""
    config = load_config()
    schedule_all_daily_jobs(application.job_queue, config)


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"WINGO 30 SEC Prediction Bot is Running 24/7!")

    def log_message(self, format, *args):
        pass


def start_health_server():
    """Starts a non-blocking HTTP server for cloud platforms (Render, Railway, Koyeb)."""
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        logger.info(f"Cloud Health Check Server listening on port {port}")
    except Exception as e:
        logger.warning(f"Could not bind health check server on port {port}: {e}")


def main():
    start_health_server()
    config = load_config()
    token = config.get("bot_token", "").strip()

    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("\n" + "="*65)
        print("⚠️ ERROR: Telegram Bot Token set nahi hai!")
        print("Kripya 'config.json' file me apna bot token dalein:")
        print("Example: \"bot_token\": \"7123456789:AAHxyz...\"")
        print("="*65 + "\n")
        sys.exit(1)

    print("🚀 Initializing WINGO 30 SEC Prediction Master Bot...")
    app = (
        ApplicationBuilder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    # Admin Control Commands
    app.add_handler(CommandHandler(["start", "admin"], start_command))
    app.add_handler(CommandHandler(["status", "nextsession"], status_command))
    app.add_handler(CommandHandler(["settimes", "setschedule"], set_times_command))
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("preview", preview_command))

    # Custom Posts & Stickers Setup
    app.add_handler(CommandHandler("setprepost", set_prepost_command))
    app.add_handler(CommandHandler("setpostpost", set_postpost_command))
    app.add_handler(CommandHandler("setwinsticker", set_winsticker_command))
    app.add_handler(CommandHandler("setlosssticker", set_losssticker_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    # Session Execution & Testing
    app.add_handler(CommandHandler("startsession", start_session_command))
    app.add_handler(CommandHandler("sendprepost", send_prepost_command))
    app.add_handler(CommandHandler("sendpostpost", send_postpost_command))

    # Channel Management
    app.add_handler(CommandHandler("channels", channels_command))
    app.add_handler(CommandHandler("addchannel", add_channel_command))
    app.add_handler(CommandHandler("delchannel", del_channel_command))
    app.add_handler(CommandHandler("setround", set_round_command))
    app.add_handler(CommandHandler("setwinrate", set_winrate_command))
    app.add_handler(CommandHandler("setgametitle", set_gametitle_command))
    app.add_handler(CommandHandler("pause", pause_command))
    app.add_handler(CommandHandler("resume", resume_command))

    # Button Callbacks
    app.add_handler(CallbackQueryHandler(button_callback_handler))

    # Message Collector for saving custom text, photo, stickers
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, admin_message_collector))

    # Global Error Handler (Gracefully handles 409 Conflict during cloud rolling deploys)
    async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        err = context.error
        if isinstance(err, Conflict):
            logger.warning("Telegram 409 Conflict caught: waiting 8s for old cloud container to release connection...")
            await asyncio.sleep(8)
            return
        logger.error("Unhandled bot exception:", exc_info=err)

    app.add_error_handler(global_error_handler)

    print("✅ Bot is online and listening for commands! Press Ctrl+C to stop.")
    while True:
        try:
            app.run_polling(drop_pending_updates=True, bootstrap_retries=10)
            break
        except Conflict:
            logger.warning("409 Conflict during polling bootstrap. Sleeping 8s before retrying...")
            time.sleep(8)
        except Exception as e:
            logger.error(f"Polling error: {e}. Retrying in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    main()
