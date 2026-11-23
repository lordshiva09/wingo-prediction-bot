import logging
import datetime
import zoneinfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import load_config, save_config
from session_manager import (
    run_channel_session,
    send_custom_post,
    send_result_sticker
)

logger = logging.getLogger("AdminPanel")
IST = zoneinfo.ZoneInfo("Asia/Kolkata")

# Admin waiting state tracking: user_id -> "waiting_for_prepost" | "waiting_for_postpost" | "waiting_for_winsticker" | "waiting_for_losssticker"
_admin_waiting_state = {}
_temp_sticker_cache = {}
_temp_post_cache = {}

def is_admin(user_id: int, config: dict) -> bool:
    admin_ids = config.get("admin_ids", [])
    if not admin_ids:
        config["admin_ids"] = [user_id]
        save_config(config)
        return True
    return user_id in admin_ids

def find_channel(channels: list, channel_id: str):
    target = str(channel_id).strip().lower()
    for ch in channels:
        if str(ch.get("channel_id")).strip().lower() == target:
            return ch
    return None

def extract_message_data(message) -> dict:
    """Extracts text, photo, or sticker data from a message object."""
    if message.photo:
        return {
            "type": "photo",
            "file_id": message.photo[-1].file_id,
            "caption": message.caption or "",
            "text": None
        }
    elif message.sticker:
        return {
            "type": "sticker",
            "file_id": message.sticker.file_id,
            "caption": None,
            "text": None
        }
    else:
        return {
            "type": "text",
            "file_id": None,
            "caption": None,
            "text": message.text or message.caption or ""
        }


# --- COMMAND HANDLERS ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()

    if not is_admin(user_id, config):
        await update.message.reply_text("⛔ Aap is bot ke admin nahi hain.")
        return

    welcome_text = (
        "🤖 **WINGO 30 SEC Prediction Master Admin Panel**\n\n"
        "⚡ **Session Timing:** Subah 11:00 AM aur Raat 11:00 PM\n"
        "📢 **Pre-Post:** 30 minute pehle (10:30 AM & 10:30 PM)\n"
        "🎯 **Session:** 6 Rounds (80% Win Rate / 20% Loss Rate)\n"
        "🏁 **Post-Post:** 6th Round ke baad automatically send hoga\n\n"
        "📌 **Quick Admin Actions:**\n"
        "• `/setprepost` - 30 min pehle wala post set karein\n"
        "• `/setpostpost` - Session end hone ke baad wala post set karein\n"
        "• `/status` - Bot live status aur upcoming schedule dekhein\n"
        "• `/settimes` - Session ke timing change karein (e.g. /settimes 11:00 16:00 23:00)\n"
        "• `/preview` - Saved posts aur stickers ka preview dekhein\n"
        "• `/startsession` - Abhi 6-round session start karein\n"
        "• `/help` - Sabhi commands ki list\n"
    )

    keyboard = [
        [
            InlineKeyboardButton("🚀 Start Session Now", callback_data="btn_start_session"),
            InlineKeyboardButton("📢 Send Pre-Post Now", callback_data="btn_send_prepost")
        ],
        [
            InlineKeyboardButton("📊 Status & Schedule", callback_data="btn_status"),
            InlineKeyboardButton("👀 Preview Saved Posts", callback_data="btn_preview")
        ],
        [
            InlineKeyboardButton("📋 Channels List", callback_data="btn_list_channels"),
            InlineKeyboardButton("⏸️ Pause All", callback_data="btn_pause_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"👤 Aapka Telegram User ID: `{user_id}`", parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    now_ist = datetime.datetime.now(IST)
    jobs = context.job_queue.jobs() if context.job_queue else []

    lines = [
        "🤖 **WINGO Prediction Bot Live Status**\n",
        f"🕒 **Bot Server Time (IST):** `{now_ist.strftime('%d-%b-%Y %I:%M:%S %p')}`",
        "🟢 **Status:** ONLINE & ACTIVE\n"
    ]

    channels = config.get("channels", [])
    active_ch = [c for c in channels if c.get("is_active", True)]
    lines.append(f"📢 **Active Channels ({len(active_ch)}):**")
    for c in active_ch:
        lines.append(f"• `{c.get('name')}` (`{c.get('channel_id')}`) | Round: `{c.get('current_round')}`")

    lines.append("\n⏰ **Daily Scheduled Sessions:**")
    session_times = config.get("session_settings", {}).get("session_times", ["11:00", "23:00"])
    for t in session_times:
        try:
            h, m = map(int, t.split(":"))
            lines.append(f"• 🎯 Session: `{datetime.time(h, m).strftime('%I:%M %p')}` (Pre-post: 30 min pehle)")
        except Exception:
            lines.append(f"• 🎯 Session: `{t}`")

    lines.append("\n⏳ **Next Scheduled Triggers:**")
    if jobs:
        valid_jobs = [j for j in jobs if j.next_t]
        valid_jobs.sort(key=lambda x: x.next_t)
        for j in valid_jobs[:6]:
            next_run_str = j.next_t.astimezone(IST).strftime("%d-%b %I:%M %p")
            lines.append(f"• `{j.name}`: **{next_run_str}**")
    else:
        lines.append("• No jobs currently queued.")

    stickers = config.get("stickers", {})
    win_stk = "✅ Custom Set" if stickers.get("win_sticker_id") else "⚠️ Default"
    loss_stk = "✅ Custom Set" if stickers.get("loss_sticker_id") else "⚠️ Default"
    lines.append(f"\n🎨 **Stickers:** WIN: {win_stk} | LOSS: {loss_stk}")

    keyboard = [
        [
            InlineKeyboardButton("🚀 Start Session Now", callback_data="btn_start_session"),
            InlineKeyboardButton("🔄 Refresh Status", callback_data="btn_status")
        ]
    ]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def set_times_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "⚠️ Format: `/settimes <HH:MM> <HH:MM> ...`\n\n"
            "Example: `/settimes 11:00 16:00 23:00`\n"
            "*(24-hour format me dalein: 11:00 = 11 AM, 16:00 = 4 PM, 23:00 = 11 PM)*",
            parse_mode="Markdown"
        )
        return

    new_times = []
    for arg in args:
        t_clean = arg.replace(",", " ").strip()
        for t in t_clean.split():
            try:
                parts = t.split(":")
                h, m = int(parts[0]), int(parts[1])
                if 0 <= h < 24 and 0 <= m < 60:
                    new_times.append(f"{h:02d}:{m:02d}")
                else:
                    await update.message.reply_text(f"⚠️ Invalid time: `{t}`. Hours 0-23 and Minutes 0-59 hone chahiye.")
                    return
            except Exception:
                await update.message.reply_text(f"⚠️ Invalid format: `{t}`. Format HH:MM hona chahiye.")
                return

    if not new_times:
        await update.message.reply_text("⚠️ Koi valid time nahi mila.")
        return

    new_times = sorted(list(set(new_times)))
    config.setdefault("session_settings", {})["session_times"] = new_times
    save_config(config)

    # Reschedule jobs
    from bot import schedule_all_daily_jobs
    schedule_all_daily_jobs(context.job_queue, config)

    formatted_times = ", ".join(new_times)
    await update.message.reply_text(
        f"✅ **Daily Session Timings update ho gayi hain!**\n\n"
        f"⏰ **New Times:** `{formatted_times}` (IST)\n"
        f"📢 Har session se **30 minutes pehle** automatically announcement post channel me jayega.\n\n"
        f"Check karne ke liye `/status` command dalein.",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    help_text = (
        "📖 **Admin Commands Guide**\n\n"
        "1️⃣ **Custom Posts & Stickers:**\n"
        "• `/setprepost` - 30 minute pehle bhejne wala post set karein (Photo/Text/Forward)\n"
        "• `/setpostpost` - Session khatam hone ke baad wala post set karein\n"
        "• `/setwinsticker` - Win sticker set karein (reply karke ya send karke)\n"
        "• `/setlosssticker` - Loss sticker set karein (reply karke ya send karke)\n"
        "• `/preview` - Check karein ki kaisa post aur sticker save hai\n\n"
        "2️⃣ **Session Controls:**\n"
        "• `/startsession [channel_id]` - 6 rounds ka session abhi start karein\n"
        "• `/sendprepost [channel_id]` - Pre-session post turant test bhejein\n"
        "• `/sendpostpost [channel_id]` - End-session post turant test bhejein\n\n"
        "3️⃣ **Channel Management:**\n"
        "• `/channels` - Configured channels list\n"
        "• `/addchannel <channel_id> <starting_round> [name]` - Naya channel jodein\n"
        "• `/delchannel <channel_id>` - Channel remove karein\n"
        "• `/setround <channel_id> <number>` - Round number reset/update karein\n"
        "• `/pause <channel_id>` / `/resume <channel_id>`\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def preview_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    await update.message.reply_text("🔍 **1. Pre-Session Post (30 Min Pehle Jayega):**", parse_mode="Markdown")
    await send_custom_post(context.bot, user_id, config.get("pre_post"))

    await update.message.reply_text("🔍 **2. Post-Session Post (Session Khatam Hone Ke Baad Jayega):**", parse_mode="Markdown")
    await send_custom_post(context.bot, user_id, config.get("post_post"))

    stickers = config.get("stickers", {})
    win_stk = stickers.get("win_sticker_id")
    loss_stk = stickers.get("loss_sticker_id")

    await update.message.reply_text("🔍 **3. WIN Sticker (80% Chance):**", parse_mode="Markdown")
    if win_stk:
        try:
            await context.bot.send_sticker(chat_id=user_id, sticker=win_stk)
        except Exception:
            await update.message.reply_text("⚠️ Win sticker ID invalid hai.")
    else:
        await update.message.reply_text("*(Default text fallback set hai, abhi sticker save nahi kiya)*")

    await update.message.reply_text("🔍 **4. LOSS Sticker (20% Chance):**", parse_mode="Markdown")
    if loss_stk:
        try:
            await context.bot.send_sticker(chat_id=user_id, sticker=loss_stk)
        except Exception:
            await update.message.reply_text("⚠️ Loss sticker ID invalid hai.")
    else:
        await update.message.reply_text("*(Default text fallback set hai, abhi sticker save nahi kiya)*")


async def set_prepost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    # Check if admin replied to a message
    reply = update.message.reply_to_message
    if reply:
        data = extract_message_data(reply)
        config["pre_post"] = data
        save_config(config)
        await update.message.reply_text("✅ Replied message ko **PRE-SESSION POST** set kar diya gaya hai! (10:30 AM & 10:30 PM par jayega)", parse_mode="Markdown")
        return

    _admin_waiting_state[user_id] = "waiting_for_prepost"
    await update.message.reply_text(
        "📩 **Pre-Session Post Setup Mode ON:**\n\n"
        "Ab aap jo bhi message (Text, Photo with caption, ya Forwarded message) yahan bhejenge, "
        "wo prediction shuru hone ke **30 minutes pehle** automatically channel me jayega.\n\n"
        "*(Cancel karne ke liye /cancel likhein)*",
        parse_mode="Markdown"
    )


async def set_postpost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    reply = update.message.reply_to_message
    if reply:
        data = extract_message_data(reply)
        config["post_post"] = data
        save_config(config)
        await update.message.reply_text("✅ Replied message ko **POST-SESSION POST** set kar diya gaya hai! (Session ke baad jayega)", parse_mode="Markdown")
        return

    _admin_waiting_state[user_id] = "waiting_for_postpost"
    await update.message.reply_text(
        "📩 **Post-Session Post Setup Mode ON:**\n\n"
        "Ab aap jo bhi message bhejenge, wo 6 rounds poore hone ke baad automatically channel me send hoga.\n\n"
        "*(Cancel karne ke liye /cancel likhein)*",
        parse_mode="Markdown"
    )


async def set_winsticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    reply = update.message.reply_to_message
    if reply and reply.sticker:
        config["stickers"]["win_sticker_id"] = reply.sticker.file_id
        save_config(config)
        await update.message.reply_text("✅ WIN Sticker successfully save ho gaya! (80% Win rate)", parse_mode="Markdown")
        return

    _admin_waiting_state[user_id] = "waiting_for_winsticker"
    await update.message.reply_text("🎯 Kripya apna **WIN Sticker** yahan bhejein jise aap channel me bhejna chahte hain.\n*(Cancel ke liye /cancel)*")


async def set_losssticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    reply = update.message.reply_to_message
    if reply and reply.sticker:
        config["stickers"]["loss_sticker_id"] = reply.sticker.file_id
        save_config(config)
        await update.message.reply_text("✅ LOSS Sticker successfully save ho gaya! (20% Loss rate)", parse_mode="Markdown")
        return

    _admin_waiting_state[user_id] = "waiting_for_losssticker"
    await update.message.reply_text("❌ Kripya apna **LOSS Sticker** yahan bhejein jise aap channel me bhejna chahte hain.\n*(Cancel ke liye /cancel)*")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in _admin_waiting_state:
        del _admin_waiting_state[user_id]
        await update.message.reply_text("🚫 Setup mode cancel kar diya gaya.")
    else:
        await update.message.reply_text("Koi active action nahi tha.")


# --- ADMIN MESSAGE COLLECTOR (WHEN IN WAITING STATE) ---

async def admin_message_collector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    msg = update.message
    state = _admin_waiting_state.get(user_id)

    # If admin sends a sticker directly without command
    if msg.sticker and not state:
        _temp_sticker_cache[user_id] = msg.sticker.file_id
        keyboard = [
            [
                InlineKeyboardButton("💚 Set as WIN Sticker (80%)", callback_data="set_sticker_win"),
                InlineKeyboardButton("❤️ Set as LOSS Sticker (20%)", callback_data="set_sticker_loss")
            ]
        ]
        await msg.reply_text(
            "🎯 **Aapne Sticker bheja hai!**\nIse prediction result ke liye kaun sa sticker banana chahte hain?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    # If admin sends a photo or text post directly without command
    if (msg.photo or msg.text) and not state:
        _temp_post_cache[user_id] = extract_message_data(msg)
        keyboard = [
            [
                InlineKeyboardButton("📢 Pre-Post (30 min pehle)", callback_data="set_post_pre"),
                InlineKeyboardButton("🏁 End-Post (Session ke baad)", callback_data="set_post_end")
            ]
        ]
        await msg.reply_text(
            "📸 **Aapne Post bheja hai!**\nIse kahan lagana chahte hain?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if not state:
        return

    if state == "waiting_for_prepost":
        data = extract_message_data(msg)
        config["pre_post"] = data
        save_config(config)
        del _admin_waiting_state[user_id]
        await msg.reply_text("✅ **Pre-Session Post** successfully set ho gaya!\nYeh post har session se **30 minutes pehle** automatically channels me post hoga. 🚀", parse_mode="Markdown")

    elif state == "waiting_for_postpost":
        data = extract_message_data(msg)
        config["post_post"] = data
        save_config(config)
        del _admin_waiting_state[user_id]
        await msg.reply_text("✅ **Post-Session Post** successfully set ho gaya!\nYeh post 6 rounds poore hone ke baad channel me send hoga. 🎉", parse_mode="Markdown")

    elif state == "waiting_for_winsticker":
        if msg.sticker:
            config["stickers"]["win_sticker_id"] = msg.sticker.file_id
            save_config(config)
            del _admin_waiting_state[user_id]
            await msg.reply_text("✅ **WIN Sticker** save ho gaya! (80% Win rate applied) 💚", parse_mode="Markdown")
        else:
            await msg.reply_text("⚠️ Kripya valid Telegram sticker bhejein. (/cancel to abort)")

    elif state == "waiting_for_losssticker":
        if msg.sticker:
            config["stickers"]["loss_sticker_id"] = msg.sticker.file_id
            save_config(config)
            del _admin_waiting_state[user_id]
            await msg.reply_text("✅ **LOSS Sticker** save ho gaya! (20% Loss rate applied) ❤️", parse_mode="Markdown")
        else:
            await msg.reply_text("⚠️ Kripya valid Telegram sticker bhejein. (/cancel to abort)")


# --- SESSION TRIGGER COMMANDS ---

async def start_session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    channels = [c for c in config.get("channels", []) if c.get("is_active", True)]
    if not channels:
        await update.message.reply_text("⚠️ Koi active channel nahi mila. `/channels` check karein ya `/addchannel` karein.")
        return

    if context.args:
        ch_id = context.args[0].strip()
        matched = find_channel(channels, ch_id)
        if matched:
            target_list = [matched]
        else:
            await update.message.reply_text(f"❌ Channel `{ch_id}` list me nahi mila.")
            return
    else:
        target_list = channels

    for ch in target_list:
        await update.message.reply_text(f"🚀 Channel `{ch['channel_id']}` ({ch.get('name', 'VIP')}) me 6-round session START ho raha hai...", parse_mode="Markdown")
        context.application.create_task(run_channel_session(context.bot, ch, config))


async def send_prepost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    channels = config.get("channels", [])
    if not channels:
        await update.message.reply_text("⚠️ Koi channel configure nahi hai.")
        return

    target_ch = channels[0]
    if context.args:
        ch = find_channel(channels, context.args[0])
        if ch:
            target_ch = ch

    await send_custom_post(context.bot, target_ch["channel_id"], config.get("pre_post"))
    await update.message.reply_text(f"📢 Pre-session post `{target_ch['channel_id']}` me bhej diya gaya!", parse_mode="Markdown")


async def send_postpost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    channels = config.get("channels", [])
    if not channels:
        await update.message.reply_text("⚠️ Koi channel configure nahi hai.")
        return

    target_ch = channels[0]
    if context.args:
        ch = find_channel(channels, context.args[0])
        if ch:
            target_ch = ch

    await send_custom_post(context.bot, target_ch["channel_id"], config.get("post_post"))
    await update.message.reply_text(f"🏁 End-session post `{target_ch['channel_id']}` me bhej diya gaya!", parse_mode="Markdown")


# --- CHANNEL MANAGEMENT ---

async def channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    channels = config.get("channels", [])
    if not channels:
        await update.message.reply_text("Koi channel configure nahi hai. `/addchannel` se naya channel jodein.")
        return

    lines = ["📋 **Configured Channels List:**\n"]
    keyboard = []

    for i, ch in enumerate(channels):
        status = "🟢 ACTIVE" if ch.get("is_active", True) else "🔴 PAUSED"
        wr = f"{float(ch.get('win_rate', 0.8))*100:.0f}%" if ch.get("win_rate") is not None else "80% (Global)"
        lines.append(
            f"**{i+1}. {ch.get('name', 'Channel')}**\n"
            f"• ID: `{ch.get('channel_id')}` | Status: {status}\n"
            f"• Game: `{ch.get('game_title', 'WINGO 30 SEC')}`\n"
            f"• Current Round: `{ch.get('current_round', 559)}`\n"
            f"• Win Rate: `{wr}`\n"
        )
        # Add button to customize this specific channel
        btn_text = f"⚙️ Customize: {ch.get('name', 'Channel')[:18]}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"manage_ch_{i}")])

    keyboard.append([InlineKeyboardButton("➕ Add New Channel", callback_data="btn_help_addchannel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=reply_markup)


async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "⚠️ Format: `/addchannel <channel_id> [starting_round] [name]`\n"
            "Example: `/addchannel @my_channel 559 VIP Group`",
            parse_mode="Markdown"
        )
        return

    channel_id = args[0].strip()
    round_num = 559
    if len(args) >= 2:
        try:
            round_num = int(args[1])
        except ValueError:
            round_num = 559

    name = " ".join(args[2:]) if len(args) >= 3 else f"Channel ({channel_id})"

    channels = config.get("channels", [])
    existing = find_channel(channels, channel_id)

    if existing:
        existing["current_round"] = round_num
        existing["name"] = name
        existing["is_active"] = True
    else:
        new_ch = {
            "channel_id": channel_id,
            "name": name,
            "game_title": "WINGO 30 SEC",
            "interval_seconds": 30,
            "current_round": round_num,
            "pattern_mode": "smart",
            "is_active": True
        }
        channels.append(new_ch)

    config["channels"] = channels
    save_config(config)

    await update.message.reply_text(
        f"✅ Channel successfully add ho gaya!\n\n"
        f"• **Channel:** `{channel_id}`\n"
        f"• **Round Start:** {round_num}\n"
        f"• **Daily Schedule:** 11:00 AM & 11:00 PM (30 min pehle post) 🚀",
        parse_mode="Markdown"
    )


async def del_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Format: `/delchannel <channel_id>`", parse_mode="Markdown")
        return

    channel_id = context.args[0].strip()
    channels = config.get("channels", [])
    ch = find_channel(channels, channel_id)

    if not ch:
        await update.message.reply_text(f"❌ Channel `{channel_id}` nahi mila.", parse_mode="Markdown")
        return

    channels = [c for c in channels if str(c.get("channel_id")).strip().lower() != channel_id.lower()]
    config["channels"] = channels
    save_config(config)
    await update.message.reply_text(f"🗑️ Channel `{channel_id}` remove kar diya gaya.", parse_mode="Markdown")


async def set_round_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Format: `/setround <channel_id> <round_number>`", parse_mode="Markdown")
        return

    channel_id = context.args[0].strip()
    try:
        new_round = int(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ Round number valid digit hona chahiye.")
        return

    ch = find_channel(config.get("channels", []), channel_id)
    if not ch:
        await update.message.reply_text(f"❌ Channel `{channel_id}` nahi mila.", parse_mode="Markdown")
        return

    ch["current_round"] = new_round
    save_config(config)
    await update.message.reply_text(f"🎯 Channel `{ch.get('name')}` ka round number set kar diya gaya: **{new_round}**", parse_mode="Markdown")


async def set_winrate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Format: `/setwinrate <channel_id> <percentage>`\nExample: `/setwinrate -1003808999105 85` (for 85% Win rate)", parse_mode="Markdown")
        return

    channel_id = context.args[0].strip()
    try:
        pct = float(context.args[1].replace("%", "").strip())
        if not (10 <= pct <= 100):
            await update.message.reply_text("⚠️ Win rate 10% se 100% ke beech hona chahiye.")
            return
        rate = pct / 100.0
    except ValueError:
        await update.message.reply_text("⚠️ Percentage number me dalein (e.g. 80, 85, 90).")
        return

    ch = find_channel(config.get("channels", []), channel_id)
    if not ch:
        await update.message.reply_text(f"❌ Channel `{channel_id}` nahi mila.", parse_mode="Markdown")
        return

    ch["win_rate"] = rate
    save_config(config)
    await update.message.reply_text(f"🎲 Channel `{ch.get('name')}` ka Win Rate set ho gaya: **{pct:.0f}%**!", parse_mode="Markdown")


async def set_gametitle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Format: `/setgametitle <channel_id> <title>`\nExample: `/setgametitle -1003808999105 WINGO 1 MIN`", parse_mode="Markdown")
        return

    channel_id = context.args[0].strip()
    new_title = " ".join(context.args[1:]).strip()

    ch = find_channel(config.get("channels", []), channel_id)
    if not ch:
        await update.message.reply_text(f"❌ Channel `{channel_id}` nahi mila.", parse_mode="Markdown")
        return

    ch["game_title"] = new_title
    save_config(config)
    await update.message.reply_text(f"🎮 Channel `{ch.get('name')}` ka Game Title update ho gaya: **{new_title}**!", parse_mode="Markdown")


async def render_channel_menu(query, ch_idx: int, config: dict):
    channels = config.get("channels", [])
    if ch_idx >= len(channels):
        await query.edit_message_text("❌ Channel nahi mila.")
        return
    ch = channels[ch_idx]
    status = "🟢 ACTIVE" if ch.get("is_active", True) else "🔴 PAUSED"
    wr = f"{float(ch.get('win_rate', 0.8))*100:.0f}%" if ch.get("win_rate") is not None else "80% (Global Default)"
    custom_pre = "✅ Custom Set" if ch.get("pre_post") else "🌐 Global Default"
    custom_end = "✅ Custom Set" if ch.get("post_post") else "🌐 Global Default"
    custom_stk = "✅ Custom Set" if ch.get("stickers") else "🌐 Global Default"

    text = (
        f"⚙️ **Channel Settings:** `{ch.get('name')}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"• **Channel ID:** `{ch.get('channel_id')}`\n"
        f"• **Status:** {status}\n"
        f"• **Game Title:** `{ch.get('game_title', 'WINGO 30 SEC')}`\n"
        f"• **Current Round:** `{ch.get('current_round', 559)}`\n"
        f"• **Win Rate:** `{wr}`\n"
        f"• **Pre-Post (30m):** {custom_pre}\n"
        f"• **End-Post:** {custom_end}\n"
        f"• **Stickers:** {custom_stk}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 *Neeche button se is channel ko customize karein:*"
    )

    toggle_btn_text = "⏸️ Pause Channel" if ch.get("is_active", True) else "▶️ Resume Channel"
    keyboard = [
        [
            InlineKeyboardButton("🎯 Set Round", callback_data=f"ch_action_round_{ch_idx}"),
            InlineKeyboardButton("🎲 Set Win Rate", callback_data=f"ch_action_winrate_{ch_idx}")
        ],
        [
            InlineKeyboardButton("🎮 Game Title", callback_data=f"ch_action_game_{ch_idx}"),
            InlineKeyboardButton("🚀 Run Session Now", callback_data=f"ch_action_run_{ch_idx}")
        ],
        [
            InlineKeyboardButton(toggle_btn_text, callback_data=f"ch_action_toggle_{ch_idx}"),
            InlineKeyboardButton("🔙 Back to Channels", callback_data="btn_list_channels")
        ]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Format: `/setround <channel_id> <round_number>`", parse_mode="Markdown")
        return

    channel_id = context.args[0].strip()
    try:
        new_round = int(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ Round number valid digit hona chahiye.")
        return

    ch = find_channel(config.get("channels", []), channel_id)
    if not ch:
        await update.message.reply_text(f"❌ Channel `{channel_id}` nahi mila.", parse_mode="Markdown")
        return

    ch["current_round"] = new_round
    save_config(config)
    await update.message.reply_text(f"🎯 Channel `{channel_id}` ka round number set kar diya gaya: **{new_round}**", parse_mode="Markdown")


async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Format: `/pause <channel_id>`", parse_mode="Markdown")
        return

    ch = find_channel(config.get("channels", []), context.args[0].strip())
    if not ch:
        await update.message.reply_text("❌ Channel nahi mila.")
        return

    ch["is_active"] = False
    save_config(config)
    await update.message.reply_text(f"⏸️ Channel `{ch['channel_id']}` pause kar diya gaya hai.")


async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Format: `/resume <channel_id>`", parse_mode="Markdown")
        return

    ch = find_channel(config.get("channels", []), context.args[0].strip())
    if not ch:
        await update.message.reply_text("❌ Channel nahi mila.")
        return

    ch["is_active"] = True
    save_config(config)
    await update.message.reply_text(f"▶️ Channel `{ch['channel_id']}` resume kar diya gaya hai.")


# --- BUTTON CALLBACK HANDLER ---

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    config = load_config()
    if not is_admin(user_id, config):
        await query.edit_message_text("⛔ Unauthorized.")
        return

    data = query.data

    if data == "btn_start_session":
        channels = [c for c in config.get("channels", []) if c.get("is_active", True)]
        if not channels:
            await query.message.reply_text("Pehle `/addchannel` karein.")
            return
        for ch in channels:
            await query.message.reply_text(f"🚀 Channel `{ch['channel_id']}` ({ch.get('name', 'VIP')}) me 6-round session START kiya ja raha hai...", parse_mode="Markdown")
            context.application.create_task(run_channel_session(context.bot, ch, config))

    elif data == "btn_send_prepost":
        channels = [c for c in config.get("channels", []) if c.get("is_active", True)]
        if not channels:
            await query.message.reply_text("Pehle channel add karein.")
            return
        for ch in channels:
            await send_custom_post(context.bot, ch["channel_id"], config.get("pre_post"))
            await query.message.reply_text(f"📢 Pre-session post `{ch['channel_id']}` me bhej diya gaya!", parse_mode="Markdown")

    elif data == "btn_preview":
        await preview_command(update, context)

    elif data == "btn_status":
        await status_command(update, context)

    elif data == "btn_list_channels":
        await channels_command(update, context)

    elif data == "btn_pause_all":
        for ch in config.get("channels", []):
            ch["is_active"] = False
        save_config(config)
        await query.message.reply_text("⏸️ Sabhi channels pause kar diye gaye hain.")

    elif data == "btn_resume_all":
        for ch in config.get("channels", []):
            ch["is_active"] = True
        save_config(config)
        await query.message.reply_text("▶️ Sabhi channels resume kar diye gaye hain.")

    elif data == "set_sticker_win":
        stk_id = _temp_sticker_cache.get(user_id)
        if stk_id:
            config["stickers"]["win_sticker_id"] = stk_id
            save_config(config)
            await query.edit_message_text("✅ Yeh sticker **WIN Sticker (80% Win Rate)** ke roop me save ho gaya! 💚")
        else:
            await query.edit_message_text("⚠️ Sticker cache expire ho gaya. Dubara sticker bhejein.")

    elif data == "set_sticker_loss":
        stk_id = _temp_sticker_cache.get(user_id)
        if stk_id:
            config["stickers"]["loss_sticker_id"] = stk_id
            save_config(config)
            await query.edit_message_text("✅ Yeh sticker **LOSS Sticker (20% Loss Rate)** ke roop me save ho gaya! ❤️")
        else:
            await query.edit_message_text("⚠️ Sticker cache expire ho gaya. Dubara sticker bhejein.")

    elif data == "set_post_pre":
        post_data = _temp_post_cache.get(user_id)
        if post_data:
            config["pre_post"] = post_data
            save_config(config)
            await query.edit_message_text("✅ Yeh post **Pre-Session Announcement (30 min pehle)** set ho gaya! 📢")
        else:
            await query.edit_message_text("⚠️ Post cache expire ho gaya. Dubara post bhejein.")

    elif data == "set_post_end":
        post_data = _temp_post_cache.get(user_id)
        if post_data:
            config["post_post"] = post_data
            save_config(config)
            await query.edit_message_text("✅ Yeh post **End-Session Announcement (Session ke baad)** set ho gaya! 🏁")
        else:
            await query.edit_message_text("⚠️ Post cache expire ho gaya. Dubara post bhejein.")

    # --- PER-CHANNEL ACTIONS ---
    elif data.startswith("manage_ch_"):
        ch_idx = int(data.split("_")[2])
        await render_channel_menu(query, ch_idx, config)

    elif data.startswith("ch_action_toggle_"):
        ch_idx = int(data.split("_")[3])
        channels = config.get("channels", [])
        if ch_idx < len(channels):
            channels[ch_idx]["is_active"] = not channels[ch_idx].get("is_active", True)
            save_config(config)
            await render_channel_menu(query, ch_idx, config)

    elif data.startswith("ch_action_run_"):
        ch_idx = int(data.split("_")[3])
        channels = config.get("channels", [])
        if ch_idx < len(channels):
            target_ch = channels[ch_idx]
            await query.message.reply_text(f"🚀 Channel `{target_ch.get('name')}` ({target_ch.get('channel_id')}) me session START ho gaya!", parse_mode="Markdown")
            context.application.create_task(run_channel_session(context.bot, target_ch, config))

    elif data.startswith("ch_action_round_"):
        ch_idx = int(data.split("_")[3])
        ch = config.get("channels", [])[ch_idx]
        await query.message.reply_text(
            f"🎯 **Round Number Badlna:**\n\n"
            f"Command likhein:\n`/setround {ch.get('channel_id')} <new_round>`\n\n"
            f"Example: `/setround {ch.get('channel_id')} 655`",
            parse_mode="Markdown"
        )

    elif data.startswith("ch_action_winrate_"):
        ch_idx = int(data.split("_")[3])
        ch = config.get("channels", [])[ch_idx]
        keyboard = [
            [
                InlineKeyboardButton("70%", callback_data=f"ch_set_wr_{ch_idx}_70"),
                InlineKeyboardButton("75%", callback_data=f"ch_set_wr_{ch_idx}_75"),
                InlineKeyboardButton("80%", callback_data=f"ch_set_wr_{ch_idx}_80"),
                InlineKeyboardButton("85%", callback_data=f"ch_set_wr_{ch_idx}_85"),
                InlineKeyboardButton("90%", callback_data=f"ch_set_wr_{ch_idx}_90")
            ],
            [
                InlineKeyboardButton("🔙 Back to Channel", callback_data=f"manage_ch_{ch_idx}")
            ]
        ]
        await query.edit_message_text(
            f"🎲 **Select Win Rate for:** `{ch.get('name')}`\n"
            f"Kripya niche diye options me se choose karein ya command se set karein:\n"
            f"`/setwinrate {ch.get('channel_id')} 85`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("ch_set_wr_"):
        parts = data.split("_")
        ch_idx = int(parts[3])
        pct = int(parts[4])
        channels = config.get("channels", [])
        if ch_idx < len(channels):
            channels[ch_idx]["win_rate"] = pct / 100.0
            save_config(config)
            await query.answer(f"Win Rate set to {pct}%!")
            await render_channel_menu(query, ch_idx, config)

    elif data.startswith("ch_action_game_"):
        ch_idx = int(data.split("_")[3])
        ch = config.get("channels", [])[ch_idx]
        await query.message.reply_text(
            f"🎮 **Game Title Badlna:**\n\n"
            f"Command likhein:\n`/setgametitle {ch.get('channel_id')} <title>`\n\n"
            f"Example:\n`/setgametitle {ch.get('channel_id')} WINGO 1 MIN`",
            parse_mode="Markdown"
        )
