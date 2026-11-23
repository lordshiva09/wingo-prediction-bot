import asyncio
import random
import logging
from typing import Set
from pattern_engine import format_prediction_message
from config import save_config, load_config

logger = logging.getLogger("SessionManager")

_active_sessions: Set[str] = set()

DEFAULT_WIN_STICKER = "CAACAgIAAxUAAWsCbGral9rywpD9GM1ir-76tYZEAAIbAAPANk8Tfb2Kg8tETWo9BA"
DEFAULT_LOSS_STICKER = "CAACAgIAAxUAAWsCbGo0r89aZy9vpey3_xIr1IqaAAIOAAPANk8TI1cURIdu1mU9BA"

def get_effective_channel_settings(channel_cfg: dict, config: dict) -> dict:
    """
    Resolves per-channel settings with fallback to global settings.
    Allows customizing each channel independently!
    """
    session_cfg = config.get("session_settings", {})
    rounds_count = int(channel_cfg.get("rounds_per_session") or session_cfg.get("rounds_per_session", 6))
    round_wait = int(channel_cfg.get("interval_seconds") or session_cfg.get("round_wait_seconds", 30))
    next_delay = int(channel_cfg.get("next_round_delay") or session_cfg.get("next_round_delay", 5))
    
    # Win rate: per-channel override or global (default 0.80)
    ch_wr = channel_cfg.get("win_rate")
    win_rate = float(ch_wr) if ch_wr is not None else float(session_cfg.get("win_rate", 0.80))

    # Stickers: per-channel override or global
    ch_stk = channel_cfg.get("stickers") or {}
    glob_stk = config.get("stickers") or {}
    stickers_cfg = {
        "win_sticker_id": ch_stk.get("win_sticker_id") or glob_stk.get("win_sticker_id") or DEFAULT_WIN_STICKER,
        "loss_sticker_id": ch_stk.get("loss_sticker_id") or glob_stk.get("loss_sticker_id") or DEFAULT_LOSS_STICKER
    }

    # Pre & Post posts: per-channel override or global
    pre_post = channel_cfg.get("pre_post") or config.get("pre_post", {})
    post_post = channel_cfg.get("post_post") or config.get("post_post", {})

    return {
        "rounds_count": rounds_count,
        "round_wait": round_wait,
        "next_delay": next_delay,
        "win_rate": win_rate,
        "stickers": stickers_cfg,
        "pre_post": pre_post,
        "post_post": post_post
    }


def format_scorecard_message(channel_cfg: dict, wins: int, losses: int, total: int) -> str:
    """Formats the automatic Session Final Profit Scorecard."""
    accuracy = (wins / total * 100) if total > 0 else 0
    game_title = channel_cfg.get("game_title", "WINGO 30 SEC")

    scorecard = (
        f"📊━━━━━━━━━━━━━━━━━━━━📊\n"
        f"   🏆 𝗦𝗘𝗦𝗦𝗜𝗢𝗡 𝗙𝗜𝗡𝗔𝗟 𝗥𝗘𝗣𝗢𝗥𝗧 🏆\n"
        f"📊━━━━━━━━━━━━━━━━━━━━📊\n\n"
        f"🎮 **Game**          : `{game_title}`\n"
        f"🎯 **Total Rounds**  : `{total}`\n"
        f"✅ **Passed (WIN)**  : `{wins} Rounds`\n"
        f"❌ **Failed (LOSS)** : `{losses} Rounds`\n"
        f"🔥 **Accuracy Rate** : `{accuracy:.1f}% Win Rate`\n"
        f"💰 **Status**        : `Massive Profit Booked 🤑`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💸 **MUST SEND YOUR WINNING PROOFS** 💸\n"
        f"🔔 Turn Notifications ON for Next Session!"
    )
    return scorecard


async def send_custom_post(bot, chat_id: str, post_data: dict):
    """Sends a configured text, photo, or sticker post to a channel."""
    if not post_data:
        return

    post_type = post_data.get("type", "text")
    try:
        if post_type == "photo" and post_data.get("file_id"):
            await bot.send_photo(
                chat_id=chat_id,
                photo=post_data["file_id"],
                caption=post_data.get("caption") or "",
                parse_mode="Markdown"
            )
        elif post_type == "sticker" and post_data.get("file_id"):
            await bot.send_sticker(
                chat_id=chat_id,
                sticker=post_data["file_id"]
            )
        else:
            text = post_data.get("text", "")
            if text:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="Markdown"
                )
    except Exception as e:
        logger.error(f"Error sending custom post to {chat_id}: {e}")


async def send_result_sticker(bot, chat_id: str, is_win: bool, round_num: int, stickers_cfg: dict):
    """Sends either the WIN or LOSS sticker directly to the channel."""
    sticker_id = None
    if isinstance(stickers_cfg, dict):
        sticker_id = stickers_cfg.get("win_sticker_id") if is_win else stickers_cfg.get("loss_sticker_id")

    if not sticker_id:
        sticker_id = DEFAULT_WIN_STICKER if is_win else DEFAULT_LOSS_STICKER

    sent = False
    try:
        await bot.send_sticker(chat_id=chat_id, sticker=sticker_id)
        sent = True
        logger.info(f"Sticker {sticker_id} successfully sent to {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send sticker {sticker_id}: {e}. Retrying with default sticker...")
        fallback_stk = DEFAULT_WIN_STICKER if is_win else DEFAULT_LOSS_STICKER
        try:
            await bot.send_sticker(chat_id=chat_id, sticker=fallback_stk)
            sent = True
        except Exception as e2:
            logger.error(f"Even default sticker failed: {e2}")

    if not sent:
        if is_win:
            text = f"✅✅ **WINNER WINNER** 🎯\n🎯 Round {round_num} PASSED! 💚🤑"
        else:
            text = f"❌ **LOSS** (Round {round_num})\n👉 Recover in next round with 3X Fund! ❤️"
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")


async def run_channel_session(bot, channel_cfg: dict, config: dict):
    """
    Executes a complete prediction session for a single channel:
    - Custom rounds per channel (default 6)
    - Custom win rate per channel (default 80%)
    - Win / Loss Sticker
    - Automatic Session Profit Scorecard
    - Post-session announcement at the end
    """
    channel_id = str(channel_cfg.get("channel_id"))
    if channel_id in _active_sessions:
        logger.warning(f"Session already running for {channel_id}, skipping duplicate trigger.")
        return

    _active_sessions.add(channel_id)

    # Resolve channel-specific effective settings
    eff = get_effective_channel_settings(channel_cfg, config)
    rounds_count = eff["rounds_count"]
    round_wait = eff["round_wait"]
    next_delay = eff["next_delay"]
    win_rate = eff["win_rate"]
    stickers_cfg = eff["stickers"]
    post_post = eff["post_post"]

    logger.info(f"Starting {rounds_count}-round session for {channel_id} (Win rate: {win_rate*100:.1f}%)")

    wins_count = 0
    losses_count = 0

    try:
        for r_idx in range(1, rounds_count + 1):
            # Reload fresh settings before each round
            live_cfg = load_config()
            eff_live = get_effective_channel_settings(channel_cfg, live_cfg)
            stickers_cfg = eff_live["stickers"]

            # 1. Format and send prediction message
            pred_text, round_sent = format_prediction_message(channel_cfg)
            await bot.send_message(chat_id=channel_cfg["channel_id"], text=pred_text)
            save_config(config)
            logger.info(f"[{channel_id}] Round {r_idx}/{rounds_count} (Period #{round_sent}) prediction sent.")

            # 2. Wait for round duration (e.g. 30 seconds for Wingo 30s)
            await asyncio.sleep(round_wait)

            # 3. Determine Win / Loss
            is_win = random.random() < win_rate
            if is_win:
                wins_count += 1
            else:
                losses_count += 1

            # 4. Send Result Sticker
            await send_result_sticker(bot, channel_cfg["channel_id"], is_win, round_sent, stickers_cfg)
            outcome = "WIN ✅" if is_win else "LOSS ❌"
            logger.info(f"[{channel_id}] Round {round_sent} Result: {outcome} sticker sent.")

            # 5. Delay before next round prediction (if not last round)
            if r_idx < rounds_count:
                await asyncio.sleep(next_delay)

        # 6. Session Finished -> Send Automatic Session Profit Scorecard!
        await asyncio.sleep(2)
        scorecard_text = format_scorecard_message(channel_cfg, wins_count, losses_count, rounds_count)
        await bot.send_message(chat_id=channel_cfg["channel_id"], text=scorecard_text, parse_mode="Markdown")
        logger.info(f"[{channel_id}] Scorecard posted: {wins_count} Wins, {losses_count} Losses ({wins_count/rounds_count*100:.1f}%)")

        # 7. Send End Announcement Post (Sticker or Custom Message)
        await asyncio.sleep(2)
        live_cfg = load_config()
        eff_live = get_effective_channel_settings(channel_cfg, live_cfg)
        await send_custom_post(bot, channel_cfg["channel_id"], eff_live["post_post"])
        logger.info(f"[{channel_id}] Full {rounds_count}-round session completed successfully!")

    except Exception as e:
        logger.error(f"Error during session execution for {channel_id}: {e}")
        admin_ids = config.get("admin_ids", [])
        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=f"⚠️ **Channel Message Error:**\nChannel `{channel_id}` me prediction bhejne me error aaya:\n`{e}`\n\nKripya check karein ki bot channel me Admin hai aur 'Post Messages' permission on hai.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
    finally:
        _active_sessions.discard(channel_id)


async def broadcast_pre_session(bot, config: dict):
    """Sends the 30-minute pre-announcement post to each channel using its effective pre_post."""
    channels = config.get("channels", [])
    logger.info("Broadcasting pre-session post to all active channels...")

    for ch in channels:
        if ch.get("is_active", True):
            eff = get_effective_channel_settings(ch, config)
            await send_custom_post(bot, ch["channel_id"], eff["pre_post"])


async def broadcast_session(bot, config: dict):
    """Triggers the session in all active channels simultaneously."""
    channels = config.get("channels", [])
    logger.info("Triggering scheduled session for all active channels...")

    tasks = []
    for ch in channels:
        if ch.get("is_active", True):
            task = asyncio.create_task(run_channel_session(bot, ch, config))
            tasks.append(task)

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
