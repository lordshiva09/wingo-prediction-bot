# 🤖 WINGO 30 SEC - Automated Prediction Master Bot

Ek complete automated Telegram Prediction Bot jo **Subah 11:00 AM** aur **Raat 11:00 PM** ko channels me automatic 6-rounds Wingo session run karta hai.

---

## ⚡ Key Features

1. **Daily 2 Sessions (Automated Timings):**
   - ⏰ **11:00 AM (Subah)** - 6 Rounds Prediction Session
   - ⏰ **11:00 PM (Raat)** - 6 Rounds Prediction Session

2. **Pre-Session Announcement (30 Minutes Pehle):**
   - 📢 **10:30 AM & 10:30 PM** par automatically channel me announcement post jayega.
   - Admin bot me koi bhi text, photo ya message bhej kar apna custom pre-post set kar sakta hai.

3. **6 Rounds Session Sequence:**
   - **Post 1:** Prediction Message (Format: BIGGG/SMALLL + GREEN 💚/RED ❤️)
   - Wait 30 seconds (Result calculation)
   - **Post 2:** WIN / LOSS Sticker (80% Win Rate / 20% Loss Rate)
   - Wait 5 seconds
   - *(Aise hi total 6 times repeat hoga)*
   - Har round ke sath Round Number automatically **+1** hota rahega (`559 -> 560 -> 561...`).

4. **Post-Session Ending Announcement:**
   - 6th Round ke baad automatically session ending summary post chala jayega (jisme proofs mangne ka message hota hai).

5. **In-Telegram Admin Controls:**
   - Admin bot me sticker ya photo bhej kar **Pre-Post**, **Post-Post**, **Win Sticker**, aur **Loss Sticker** set kar sakta hai.
   - Kisi bhi time `/startsession` karke manual session run kiya ja sakta hai.
   - Channels add/remove karna aur round number reset karna asaan hai.

---

## 🚀 Setup & Launch Guide

### 1. Requirements
Libraries already installed:
- `python-telegram-bot`
- `apscheduler`

### 2. Token Add Karein
[config.json](config.json) file open karein aur apna Bot Token dalein:
```json
{
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN_HERE"
}
```

### 3. Bot Run Karein
Terminal me run karein:
```powershell
cd telegram_wingo_bot
python bot.py
```

---

## 🎮 Telegram Admin Commands

Bot ko private chat me open karein aur in commands ka use karein:

### 📢 Custom Posts & Stickers Setup
- `/setprepost` - 30 minute pehle bhejne wala post set karein (Photo with caption ya Text message bhejkar).
- `/setpostpost` - Session khatam hone ke baad wala post set karein.
- `/setwinsticker` - Win sticker set karein (Sticker ko reply karke ya send karke).
- `/setlosssticker` - Loss sticker set karein (Sticker ko reply karke ya send karke).
- `/preview` - Apne sabhi saved posts aur stickers ko check karein.
- `/cancel` - Setup mode cancel karein.

### 🎯 Session & Testing Commands
- `/startsession [channel_id]` - 6 rounds ka session abhi start karein (Test ke liye).
- `/sendprepost [channel_id]` - Pre-session post turant test bhejein.
- `/sendpostpost [channel_id]` - End-session post turant test bhejein.

### 📋 Channel Management Commands
- `/channels` - Sabhi channels ki list dekhein.
- `/addchannel <channel_id> [starting_round] [name]` - Naya channel jodein (e.g. `/addchannel @vip_channel 559 VIP`).
- `/delchannel <channel_id>` - Channel remove karein.
- `/setround <channel_id> <round_number>` - Round number manually set karein (e.g. `/setround @vip_channel 560`).
- `/pause <channel_id>` / `/resume <channel_id>` - Kisi channel ko rokein ya chalu karein.
