import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "bot_token": "YOUR_BOT_TOKEN_HERE",
    "admin_ids": [],
    "channels": [
        {
            "channel_id": "@your_channel_username",
            "name": "WINGO VIP Channel",
            "game_title": "WINGO 30 SEC",
            "current_round": 559,
            "pattern_mode": "smart",
            "is_active": True
        }
    ],
    "session_settings": {
        "rounds_per_session": 6,
        "round_wait_seconds": 30,
        "next_round_delay": 5,
        "win_rate": 0.80,
        "session_times": ["11:00", "23:00"],
        "pre_post_minutes_before": 30
    },
    "pre_post": {
        "type": "text",
        "text": "🔥 **WINGO 30 SEC VIP SESSION STARTING IN 30 MINUTES!** 🔥\n\n⏰ Session Time: 11:00 AM / 11:00 PM\n🎯 Sabhi log apna fund ready rakhein!\n💰 80%+ Accuracy Guaranteed!\n\n🔔 Channel Notifications ON rakhein!",
        "file_id": None,
        "caption": None
    },
    "post_post": {
        "type": "text",
        "text": "🎉 **WINGO 30 SEC SESSION COMPLETED!** 🎉\n\n✅ 6/6 Rounds Done!\n🤑 Massive Profit Booked!\n💸 Must send your winning proofs to Admin!\n\nNext Session scheduled soon. Stay tuned! 🚀",
        "file_id": None,
        "caption": None
    },
    "stickers": {
        "win_sticker_id": "CAACAgIAAxUAAWsCbGral9rywpD9GM1ir-76tYZEAAIbAAPANk8Tfb2Kg8tETWo9BA",
        "loss_sticker_id": "CAACAgIAAxUAAWsCbGo0r89aZy9vpey3_xIr1IqaAAIOAAPANk8TI1cURIdu1mU9BA"
    }
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Ensure new keys exist if loading older config
            for key, val in DEFAULT_CONFIG.items():
                if key not in cfg:
                    cfg[key] = val

            # Check if BOT_TOKEN is set via Cloud Environment Variable
            env_token = os.environ.get("BOT_TOKEN")
            if env_token and env_token.strip():
                cfg["bot_token"] = env_token.strip()

            return cfg
    except Exception as e:
        print(f"Error loading {CONFIG_FILE}: {e}")
        return DEFAULT_CONFIG

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving {CONFIG_FILE}: {e}")
