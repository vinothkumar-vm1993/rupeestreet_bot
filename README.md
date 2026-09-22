# RUPEESTREET // TELEGRAM OPERATIONS BOT

Smart, safe stock market intelligence and disciplined capital protection assistant for Indian Financial Markets on Telegram.

---

## Quick Setup Guide (எளிய அமைவு முறை)

### 1. Telegram Bot Token பெறுவது எப்படி:
1. Telegram-ல் **@BotFather** கணக்கைத் திறக்கவும்.
2. `/newbot` என்று அனுப்பவும்.
3. உங்கள் போட்டின் பெயர் (Name) மற்றும் யூசர்நேம் (Username, e.g., `RupeeStreet_Bot`) கொடுக்கவும்.
4. BotFather உங்களுக்கு ஒரு **HTTP API Token** தருவார் (Example: `7123456789:AAH...`).

### 2. Token-ஐ Configure செய்வது:
`/home/vinoth/Project/titan_alpha_telegram_bot/.env` கோப்பைத் திறந்து உங்கள் Token-ஐ உள்ளிடவும்:

```bash
TELEGRAM_BOT_TOKEN=உங்கள்_BOT_TOKEN_இங்கு_போடவும்
AUTHORIZED_USER_IDS=   # (Optional) உங்கள் Telegram User ID (@userinfobot மூலம் பெறலாம்)
```

### 3. போட்டை இயக்குவது எப்படி (Run the Bot):

```bash
cd /home/vinoth/Project/titan_alpha_telegram_bot
./start_bot.sh
```

அல்லது Background-ல் 24/7 இயங்க:
```bash
nohup ./start_bot.sh > bot.log 2>&1 &
```

---

## கிடைக்கக்கூடிய கட்டளைகள் (Commands List)

| Command | விளக்கம் (Description) |
| :--- | :--- |
| `/start` அல்லது `/help` | முதன்மை மெனு மற்றும் Interactive Buttons |
| `/regime` | சந்தை நிலை (Market Regime), Nifty, Bank Nifty, India VIX |
| `/research <SYMBOL>` | பங்கின் முழுமையான ஆய்வு அறிக்கை (எ.கா: `/research HDFCBANK`) |
| `/risk` | ரிஸ்க் கமிட்டியின் விதிகள் மற்றும் வரம்புகள் |
| `/portfolio` | போர்ட்ஃபோலியோ இருப்பு, செக்டார் வரம்பு & 10% Cash Buffer |
| `/watchlist` | கண்காணிக்கப்படும் நிறுவனங்களின் பட்டியல் |
| `/track <SYMBOL>` | உங்கள் முதலீட்டு நிலை & Stop Loss கண்காணிப்பு |
| `/alert <MESSAGE>` | அவசர ரிஸ்க் எச்சரிக்கை அனுப்புதல் |

---

## Operating Principles
* **Capital Preservation** takes precedence over return generation.
* **Strict Gating Rules:** Risk Score > 70 Reject, Governance < 50 Reject.
* **Hard Stop Losses:** Non-negotiable daily close rule.
