# ☁️ WINGO Telegram Bot - 24/7 Cloud Deployment Guide

Aapka bot cloud par deploy hone ke baad **PC band hone par bhi 24 ghante chalega**.

---

## 🌟 Sabse Best Option: Render.com (100% Free)

### Step 1: GitHub Par Repository Banayein
1. [GitHub.com](https://github.com/new) par jayein (apne `lordshiva09` account se login karein).
2. Repository ka naam dalein: `wingo-prediction-bot`.
3. Is repository ko **Private** ya **Public** select karein aur **Create repository** par click karein.
4. `telegram_wingo_bot` folder ke andar ki sabhi files ko is repository me push/upload kar dein.

---

### Step 2: Render Par Free Web Service Banayein
1. [dashboard.render.com](https://dashboard.render.com) par jayein aur **Sign in with GitHub** karein.
2. Dashboard par **New +** button dabayein aur **Web Service** select karein.
3. Apni GitHub repository `wingo-prediction-bot` select karke **Connect** karein.
4. Settings me yeh details bharein:
   - **Name**: `wingo-prediction-bot`
   - **Region**: `Singapore` (India ke sabse paas hai)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: `Free`
5. Neeche **Deploy Web Service** par click karein.
6. 1 minute me Render aapka bot deploy kar dega aur `Live` status show karega!

---

### Step 3: Bot Ko 24/7 Jagaye Rakhna (Free UptimeRobot)
Render ka free tier 15 minute baad sleep na ho, iske liye:
1. Render aapko ek link dega (jaise `https://wingo-prediction-bot.onrender.com`).
2. [uptimerobot.com](https://uptimerobot.com) par free account banayein.
3. **Add New Monitor** par click karein:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `Wingo Bot`
   - **URL**: Apna Render wala link paste karein
   - **Monitoring Interval**: `5 minutes`
4. **Create Monitor** dabayein.

Ab UptimeRobot aapke bot ko har 5 minute me ping karta rahega, jisse aapka bot **zindagi bhar 24/7 bina ruke chalega** chahe aapka PC aur phone band ho!
