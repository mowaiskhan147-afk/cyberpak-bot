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

# ✅ Saare required channels
CHANNELS = [
    "@wp_trick",
    "@cyber_apis",
    "@SoloHunter3"
]

PORT         = int(os.environ.get("PORT", 5000))
WEBHOOK_HOST = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
WEBHOOK_URL  = f"{WEBHOOK_HOST}/{BOT_TOKEN}"

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=False)

def set_webhook_auto():
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

# ── Subscription check — saare channels ──────────────────────────────────
def get_unjoined_channels(user_id):
    """Return list of channels user ne join nahi kiye"""
    unjoined = []
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status not in ["creator", "administrator", "member"]:
                unjoined.append(ch)
        except:
            unjoined.append(ch)
    return unjoined

def send_join_alert(chat_id, unjoined):
    markup = InlineKeyboardMarkup()
    for ch in unjoined:
        name = ch.replace("@", "")
        markup.add(InlineKeyboardButton(
            f"📢 Join @{name}",
            url=f"https://t.me/{name}"
        ))
    ch_list = "\n".join([f"• {ch}" for ch in unjoined])
    bot.send_message(
        chat_id,
        f"<b>🚫 ACCESS DENIED!</b>\n\n"
        f"Pehle yeh channels join karo:\n{ch_list}\n\n"
        f"<i>⚠️ Channel chhoda to access kho jaoge!</i>",
        reply_markup=markup
    )

# ── /start ─────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def start_msg(message):
    # Groups mein ignore karo
    if message.chat.type in ["group", "supergroup", "channel"]:
        return

    unjoined = get_unjoined_channels(message.from_user.id)
    if unjoined:
        send_join_alert(message.chat.id, unjoined)
        return

    bot.reply_to(
        message,
        "<b>🛡️ WELCOME TO PRO DATABASE BOT</b>\n\n"
        "Access Granted! ✅\n"
        "Send me any Pakistani Number (e.g., <code>03xxxxxxxxx</code>) "
        "or 13-digit CNIC to fetch details from the mainframe.\n\n"
        "<i>⚡ Powered by Owais &amp; Liaqat</i>"
    )

# ── Main handler ───────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True)
def fetch_data(message):
    # Groups/channels mein bilkul kaam na kare
    if message.chat.type in ["group", "supergroup", "channel"]:
        return

    unjoined = get_unjoined_channels(message.from_user.id)
    if unjoined:
        send_join_alert(message.chat.id, unjoined)
        return

    query    = message.text.strip()
    wait_msg = bot.reply_to(message, "<b>⏳ Scanning King OwAiS Mainframe...</b>")
    params   = {"key": API_KEY, "phone": query.replace("-", "").replace(" ", "")}

    try:
        res  = requests.get(API_URL, params=params, timeout=15)
        data = res.json()

        # ── Extract records ──────────────────────────────────────────────
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

        # ── Censored check ───────────────────────────────────────────────
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

        # ── Group by person ──────────────────────────────────────────────
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

        # ── Build ONE combined message ────────────────────────────────────
        full_msg   = ""
        map_url    = None
        static_url = None
        file_num   = 0

        for p in persons.values():
            file_num += 1
            # SIMs
            sims_list = sorted(p["numbers"])
            sims_text = ""
            for i, num in enumerate(sims_list, 1):
                sims_text += f"{i}. <code>{num}</code> - {detectNetwork(num)}\n"

            # Father field mein searched query dikhao
            father_display = query if p["father"] == "N/A" else p["father"]

            block = (
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"<b>👤 FILE #{file_num} — PERSONAL DATA</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🔍 SEARCHED: <code>{query}</code>\n"
                f"👤 NAME: <b>{p['name']}</b>\n"
                f"🪪 CNIC: <code>{p['cnic']}</code>\n"
                f"👨 FATHER: {father_display}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"<b>📊 SIMS ({len(sims_list)})</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{sims_text}"
            )

            address = p["address"]
            if address != "N/A":
                enc = urllib.parse.quote(address)
                if not map_url:  # pehle person ka map use karo
                    map_url    = f"https://maps.google.com/maps?q={enc}"
                    static_url = (
                        f"https://maps.googleapis.com/maps/api/staticmap"
                        f"?center={enc}&zoom=14&size=600x300&scale=2"
                        f"&markers=color:red%7C{enc}"
                    )
                block += (
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"<b>📍 LOCATION</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"📌 {address}\n"
                )

            full_msg += block

        full_msg += f"━━━━━━━━━━━━━━━━━━━\n<i>👑 Database by Owais &amp; Liaqat</i>"

        # ── Send as ONE message ──────────────────────────────────────────
        btn = InlineKeyboardMarkup()
        if map_url:
            btn.add(InlineKeyboardButton("🗺️ Open Map Location", url=map_url))

        if map_url and static_url:
            try:
                bot.send_photo(
                    message.chat.id,
                    photo=static_url,
                    caption=full_msg,
                    reply_markup=btn,
                    parse_mode="HTML"
                )
            except Exception:
                bot.send_message(
                    message.chat.id, full_msg,
                    reply_markup=btn,
                    disable_web_page_preview=True
                )
        else:
            bot.send_message(
                message.chat.id, full_msg,
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

if __name__ == "__main__":
    threading.Thread(target=set_webhook_auto, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
