import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import requests
import urllib.parse
import os
import threading
import time

# ==========================================
# 👑 PRO DATABASE BOT BY OWAIS & LIAQAT 👑
# ==========================================

BOT_TOKEN        = "8788981804:AAFqqCZUWXQt2cfU1lF8HdyyfufGvcNgKss"
API_URL          = "https://kingowais-pak-api.vercel.app/api/search"
API_KEY          = "KINGOWAIS_OWNER"
CHANNEL_USERNAME = "@wp_trick"
PORT             = int(os.environ.get("PORT", 5000))
WEBHOOK_HOST     = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
WEBHOOK_URL      = f"{WEBHOOK_HOST}/{BOT_TOKEN}"

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=False)

# ── Auto webhook set on startup ────────────────────────────────────────────
def set_webhook_auto():
    """5 second wait karo taake Flask pehle start ho, phir webhook set karo"""
    time.sleep(5)
    try:
        bot.remove_webhook()
        time.sleep(1)
        result = bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook auto-set: {WEBHOOK_URL} → {result}")
    except Exception as e:
        print(f"❌ Webhook set failed: {e}")

def detectNetwork(num):
    if not num: return "Unknown"
    n = "".join(filter(str.isdigit, num))
    if n.startswith("92"): n = n[2:]
    if n.startswith("0"):  n = n[1:]
    if n.startswith("30") or n.startswith("31"): return "Jazz"
    if n.startswith("32"): return "Warid"
    if n.startswith("33"): return "Ufone"
    if n.startswith("34"): return "Telenor"
    if n.startswith("35"): return "SCO"
    return "Unknown"

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ["creator", "administrator", "member"]
    except:
        return False

def send_join_alert(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(
        "📢 Join Channel to Use Bot",
        url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"
    ))
    bot.send_message(
        chat_id,
        "<b>🚫 ACCESS DENIED!</b>\n\n"
        "To use this premium bot, you must join our official Channel first.\n"
        "<i>⚠️ Note: If you leave the channel, you will lose access automatically.</i>",
        reply_markup=markup
    )

@bot.message_handler(commands=["start"])
def start_msg(message):
    if not is_subscribed(message.from_user.id):
        send_join_alert(message.chat.id)
        return
    bot.reply_to(
        message,
        "<b>🛡️ WELCOME TO PRO DATABASE BOT</b>\n\n"
        "Access Granted! ✅\n"
        "Send me any Pakistani Number (e.g., <code>03xxxxxxxxx</code>) "
        "or 13-digit CNIC to fetch details from the mainframe.\n\n"
        "<i>⚡ Powered by Owais &amp; Liaqat</i>"
    )

@bot.message_handler(func=lambda m: True)
def fetch_data(message):
    if not is_subscribed(message.from_user.id):
        send_join_alert(message.chat.id)
        return

    query    = message.text.strip()
    wait_msg = bot.reply_to(message, "<b>⏳ Scanning King OwAiS Mainframe...</b>")
    params   = {"key": API_KEY}

    clean = query.replace("-", "").replace(" ", "")
    # API sirf phone parameter accept karta hai — CNIC bhi phone se bhejo
    params["phone"] = clean

    try:
        res  = requests.get(API_URL, params=params, timeout=15)
        data = res.json()

        records = None
        if data.get("success"):
            d = data.get("data", {})
            if isinstance(d, dict):
                dd = d.get("data", {})
                if isinstance(dd, dict) and "records" in dd:
                    records = dd["records"]
                elif "records" in d:
                    records = d["records"]
            if records is None and "records" in data:
                records = data["records"]

        if not records:
            bot.edit_message_text(
                "<b>⚠️ NO RECORD FOUND IN DATABASE!</b>",
                chat_id=message.chat.id, message_id=wait_msg.message_id
            )
            return

        def is_censored(rec):
            vals = [str(rec.get("full_name","") or ""), str(rec.get("phone","") or ""), str(rec.get("cnic","") or "")]
            real = [v for v in vals if v.strip()]
            return all(set(v.replace(" ","")) <= {"*"} for v in real) if real else True

        if all(is_censored(r) for r in records):
            bot.edit_message_text(
                "<b>⚠️ NO RECORD FOUND IN DATABASE!</b>\n\n"
                "<i>This number/CNIC has no data in our mainframe.</i>",
                chat_id=message.chat.id, message_id=wait_msg.message_id
            )
            return

        bot.delete_message(message.chat.id, wait_msg.message_id)

        def clr(v):
            return v if v and str(v).lower() not in ("none", "n/a", "") else "N/A"

        persons = {}
        for rec in records:
            name = clr(rec.get("full_name") or rec.get("name") or "")
            cnic = clr(rec.get("cnic") or "")
            key  = (name, cnic)
            if key not in persons:
                persons[key] = {
                    "name":    name,
                    "cnic":    cnic,
                    "address": clr(rec.get("address") or ""),
                    "father":  clr(rec.get("father_name") or ""),
                    "numbers": set()
                }
            ph = rec.get("phone") or rec.get("mobile")
            if ph: persons[key]["numbers"].add(str(ph))

        for p in persons.values():
            personal = (
                f"<b>👤 PERSONAL DATA</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"NAME: {p['name']}\n"
                f"CNIC: {p['cnic']}\n"
                f"FATHER: {p['father']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
            )
            sims = "<b>📊 SIMS INFORMATION</b>\n━━━━━━━━━━━━━━━━━━━\n"
            for i, num in enumerate(sorted(p["numbers"]), 1):
                sims += f"{i}. <code>{num}</code> - {detectNetwork(num)}\n"
            sims += "━━━━━━━━━━━━━━━━━━━\n"

            footer  = "<i>👑 Database by Owais &amp; Liaqat</i>"
            address = p["address"]

            if address != "N/A":
                enc     = urllib.parse.quote(address)
                map_url = f"https://maps.google.com/maps?q={enc}"
                static  = (
                    f"https://maps.googleapis.com/maps/api/staticmap"
                    f"?center={enc}&zoom=14&size=600x300&scale=2"
                    f"&markers=color:red%7C{enc}"
                )
                location = (
                    f"<b>📍 LOCATION DATA</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"ADDRESS: {address}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                )
                caption = personal + sims + location + footer
                btn = InlineKeyboardMarkup()
                btn.add(InlineKeyboardButton(
                    "🗺️ Open Map Location",
                    url=map_url
                ))
                try:
                    bot.send_photo(
                        message.chat.id,
                        photo=static,
                        caption=caption,
                        reply_markup=btn,
                        parse_mode="HTML"
                    )
                except Exception:
                    bot.send_message(
                        message.chat.id, caption,
                        reply_markup=btn,
                        disable_web_page_preview=False
                    )
            else:
                bot.send_message(
                    message.chat.id,
                    personal + sims + footer,
                    disable_web_page_preview=True
                )

    except Exception as e:
        print(f"Error: {e}")
        try:
            bot.edit_message_text(
                "<b>❌ API ERROR:</b> Server is busy or offline.",
                chat_id=message.chat.id, message_id=wait_msg.message_id
            )
        except: pass

# ── Flask routes ───────────────────────────────────────────────────────────
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/set_webhook")
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    return f"✅ Webhook set! URL: {WEBHOOK_URL}"

@app.route("/")
def index():
    return "🤖 King OwAiS Bot is Running!"

# ── Start ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Background thread mein webhook auto-set karo
    threading.Thread(target=set_webhook_auto, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
