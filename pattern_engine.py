import random
from typing import Dict, Tuple

# Channel state memory (to remember previous results for pattern recognition/trends)
_channel_states: Dict[str, dict] = {}

def get_channel_state(channel_id: str) -> dict:
    if channel_id not in _channel_states:
        _channel_states[channel_id] = {
            "last_size": "BIG",
            "last_color": "GREEN",
            "streak_count": 0,
            "current_pattern": "dragon",  # 'dragon', 'alternate', 'double'
            "pattern_step": 0
        }
    return _channel_states[channel_id]

def generate_prediction_values(state: dict, mode: str = "smart") -> Tuple[str, str, str]:
    """
    Generates next prediction size and color based on patterns.
    Returns: (size_str, color_str, color_emoji)
    e.g. ("BIGGG", "GREEN", "💚") or ("SMALLL", "RED", "❤️")
    """
    last_size = state["last_size"]
    last_color = state["last_color"]
    streak = state["streak_count"]
    pattern = state["current_pattern"]
    step = state["pattern_step"]
    
    # Decide size based on pattern
    if mode == "alternate":
        # 1-1 pattern: BIG -> SMALL -> BIG
        next_size = "SMALL" if last_size == "BIG" else "BIG"
    elif mode == "dragon":
        # Dragon streak (repeats 3-6 times then flips)
        if streak < random.randint(3, 6):
            next_size = last_size
        else:
            next_size = "SMALL" if last_size == "BIG" else "BIG"
    elif mode == "double":
        # 2-2 pattern: BIG, BIG, SMALL, SMALL
        if step % 2 == 0:
            next_size = last_size
        else:
            next_size = "SMALL" if last_size == "BIG" else "BIG"
    else:  # "smart" (dynamic mixture of trends)
        rand_val = random.random()
        # 45% chance to continue streak if streak is small (<3)
        if streak < 3 and rand_val < 0.65:
            next_size = last_size
        elif streak >= 4:
            next_size = "SMALL" if last_size == "BIG" else "BIG"
        else:
            next_size = random.choice(["BIG", "SMALL"])

    # Update streak
    if next_size == last_size:
        state["streak_count"] += 1
    else:
        state["streak_count"] = 1
        
    state["pattern_step"] += 1
    state["last_size"] = next_size

    # Choose color associated with the size
    # In Wingo:
    # BIG numbers: 5 (Green+Violet), 6 (Red), 7 (Green), 8 (Red), 9 (Green)
    # SMALL numbers: 0 (Red+Violet), 1 (Green), 2 (Red), 3 (Green), 4 (Red)
    # Green and Red are roughly 50-50 for both Big and Small
    next_color = random.choice(["GREEN", "RED"])
    state["last_color"] = next_color

    size_display = "BIGGG" if next_size == "BIG" else "SMALLL"
    emoji = "💚" if next_color == "GREEN" else "❤️"

    return size_display, next_color, emoji


def format_prediction_message(channel_cfg: dict) -> Tuple[str, int]:
    """
    Formats the message in Option 1 (VIP Luxury Gold Style):
    👑━━━━━━━━━━━━━━━━━━━━👑
       💎 𝗪𝗜𝗡𝗚𝗢 𝟯𝟬 𝗦𝗘𝗖 𝗩𝗜𝗣 💎
    👑━━━━━━━━━━━━━━━━━━━━👑

    🎯 𝗥𝗼𝘂𝗻𝗱 𝗜𝗗   ➠  `656`
    👉 𝗣𝗿𝗲𝗱𝗶𝗰𝘁𝗶𝗼𝗻  ➠  🟢 **BIGGG (GREEN 💚)**
    💰 𝗙𝘂𝗻𝗱 𝗣𝗹𝗮𝗻   ➠  `Level 1 (Use 3X Plan)`

    ━━━━━━━━━━━━━━━━━━━━━
      🤑💸 𝗠𝗨𝗦𝗧 𝗦𝗘𝗡𝗗 𝗪𝗜𝗡 𝗣𝗥𝗢𝗢𝗙 💸🤑
    """
    channel_id = str(channel_cfg.get("channel_id"))
    state = get_channel_state(channel_id)
    
    current_round = channel_cfg.get("current_round", 500)
    game_title = channel_cfg.get("game_title", "WINGO 30 SEC")
    pattern_mode = channel_cfg.get("pattern_mode", "smart")
    
    size_str, color_str, emoji = generate_prediction_values(state, pattern_mode)
    color_dot = "🟢" if color_str == "GREEN" else "🔴"
    
    message = (
        f"👑━━━━━━━━━━━━━━━━━━━━👑\n"
        f"   💎 𝗪𝗜𝗡𝗚𝗢 𝟯𝟬 𝗦𝗘𝗖 𝗩𝗜𝗣 💎\n"
        f"👑━━━━━━━━━━━━━━━━━━━━👑\n\n"
        f"🎯 𝗥𝗼𝘂𝗻𝗱 𝗜𝗗   ➠  `{current_round}`\n"
        f"👉 𝗣𝗿𝗲𝗱𝗶𝗰𝘁𝗶𝗼𝗻  ➠  {color_dot} **{size_str} ({color_str} {emoji})**\n"
        f"💰 𝗙𝘂𝗻𝗱 𝗣𝗹𝗮𝗻   ➠  `Level 1 (Use 3X Plan)`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🤑💸 𝗠𝗨𝗦𝗧 𝗦𝗘𝗡𝗗 𝗪𝗜𝗡 𝗣𝗥𝗢𝗢𝗙 💸🤑"
    )
    
    # Increment round for the next turn
    next_round = current_round + 1
    channel_cfg["current_round"] = next_round
    
    return message, current_round
