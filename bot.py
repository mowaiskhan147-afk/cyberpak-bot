import os
import json
import requests
import urllib.parse
from flask import Flask, request
import telebot

BOT_TOKEN = "8788981804:AAFqqCZUWXQt2cfU1lF8HdyyfufGvcNgKss"
API_URL = "https://cyber-pak-info2.vercel.app/search"
API_KEY = "ZEXX@_VIP"

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

def detectNetwork(num):
    if not num: return "❓ Unknown"
    n = "".join(filter(str.isdigit, num))
    if n.startswith("92"): n = n[2:]
    if n.startswith("0"):  n = n[1:]
    prefixes = {
        "30": "📶 Jazz", "31": "📶 Jazz", "32": "📶 Warid",
        "33": "📶 Ufone", "34": "📶 Telenor", "35": "📶 SCO",
        "300": "📶 Jazz", "301": "📶 Jazz", "302": "📶 Jazz",
        "303": "📶 Jazz", "304": "📶 Jazz", "305": "📶 Jazz",
        "306": "📶 Jazz", "307": "📶 Jazz", "308": "📶 Jazz",
        "309": "📶 Jazz",
        "310": "📶 Zong", "311": "📶 Zong", "312": "📶 Zong",
        "313": "📶 Zong", "314": "📶 Zong", "315": "📶 Zong",
        "316": "📶 Zong", "317": "📶 Zong", "318": "📶 Zong",
        "319": "📶 Zong",
    }
    for prefix, network in prefixes.items():
        if n.startswith(prefix):
            return network
    return "❓ Unknown"

def detect_query_type(query):
    clean = query.replace("-", "").replace(" ", "")
    if len(clean) == 13 and clean.isdigit():
        return "cnic"
    elif clean.isdigit() and len(clean) >= 10:
        return "phone"
    return "unknown"

def query_type_label(qtype):
    if qtype == "cnic":   return "🪪 CNIC Lookup"
    if qtype == "phone":  return "📱 Phone Lookup"
    return "🔍 Unknown"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Send me a Pakistani number or CNIC to get details.")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    query = message.text.strip()
    qtype = detect_query_type(query)
    if qtype == "unknown":
        bot.reply_to(message, "Invalid query. Send a phone number (e.g., 03001234567) or CNIC.")
        return

    # Send "searching" message
    wait = bot.reply_to(message, f"🔎 Searching...\nQuery: {query}\nType: {query_type_label(qtype)}")

    try:
        params = {"key": API_KEY, "phone": query.replace("-", "").replace(" ", "")}
        resp = requests.get(API_URL, params=params, timeout=15)
        data = resp.json()
        records = None
        if data.get("success"):
            d = data.get("data")
            if isinstance(d, list):
                records = d
            elif isinstance(d, dict):
                records = d.get("records", [])
        if not records:
            bot.edit_message_text("❌ No record found.", message.chat.id, wait.message_id)
            return

        # Combine results
        merged = {"name": "N/A", "cnic": "N/A", "address": "N/A", "father": "N/A", "numbers": set()}
        for rec in records:
            name    = rec.get("full_name") or rec.get("name") or "N/A"
            cnic    = rec.get("cnic") or "N/A"
            address = rec.get("address") or "N/A"
            father  = rec.get("father_name") or "N/A"
            ph      = rec.get("phone") or rec.get("mobile")
            if name != "N/A": merged["name"] = name
            if cnic != "N/A": merged["cnic"] = cnic
            if address != "N/A": merged["address"] = address
            if father != "N/A": merged["father"] = father
            if ph: merged["numbers"].add(str(ph))

        sims_list = sorted(merged["numbers"])
        sims_text = ""
        for i, num in enumerate(sims_list, 1):
            sims_text += f"  {i}) <code>{num}</code> — {detectNetwork(num)}\n"

        result = (
            f"<b>🔎 PHONE/CNIC Information</b>\n\n"
            f"👤 Name: {merged['name']}\n"
            f"🪪 CNIC: <code>{merged['cnic']}</code>\n"
            f"📍 Address: {merged['address']}\n"
            f"📱 Registered Numbers ({len(sims_list)}):\n{sims_text}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Powered by OWAiS</i>"
        )
        bot.delete_message(message.chat.id, wait.message_id)
        bot.send_message(message.chat.id, result)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {e}", message.chat.id, wait.message_id)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "🤖 Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)