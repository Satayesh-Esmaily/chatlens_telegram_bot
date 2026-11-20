# chatlens_telegram_bot

<p align="center">
  <img src="assets/logo.png" width="160" alt="ChatLens logo">
</p>

<h1 align="center">ChatLens</h1>
<p align="center">Free Telegram bot for chat analytics, reminders and notes.</p>

## Features
- 📊 Chat analysis from exported JSON
- ⏰ Reminders
- 📝 Notes
- ⚡ Quick replies
- 🔒 Privacy-first, with `/delete_my_data`

## Setup
```bash
git clone https://github.com/Satayesh-Esmaily/lens-chat-bot.git
cd chatlens_telegram_bot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then add your BOT_TOKEN
python main.py
```

## Status
🚧 Under development