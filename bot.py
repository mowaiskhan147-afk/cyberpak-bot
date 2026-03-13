import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import requests
import urllib.parse
import os
import threading
import time
import json

# ==========================================
# 👑 PRO DATABASE BOT BY OWAIS & LIAQAT 👑
# ==========================================

BOT_TOKEN  = "8788981804:AAFqqCZUWXQt2cfU1lF8HdyyfufGvcNgKss"
API_URL    = "https://kingowais-pak-api.vercel.app/api/search"
API_KEY    = "KINGOWAIS_OWNER"
ADMIN_ID   = 7962481764

# ── Upstash Redis REST ─────────────────────────────────────────────────────
UPSTASH_URL   = "https://precise-coyote-67987.upstash.io"
UPSTASH_TOKEN = "gQAAAAAAAQmTAAIncDI0YTVhNjYwOGJjMzk0NTIxYTYyYTA3MzM5YWY4ZmEyOHAyNjc5ODc"

def redis_set(key, value):
    try:
        r = requests.post(
            f"{UPSTASH_URL}/set/{key}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            json=value,
            timeout=5
        )
        return r.json()
    except Exception as e:
        print(f"Redis SET error: {e}")

def redis_get(key):
    try:
        r = requests.get(
            f"{UPSTASH_URL}/get/{key}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            timeout=5
        )
        data = r.json()
        if data.get("result") is not None:
            return json.loads(data["result"])
    except Exception as e:
        print(f"Redis GET error: {e}")
    return None

# ── Config load/save ───────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "channels": ["@wp_trick", "@SoloHunter3"],
    "welcome_msg": "Send me any Pakistani Number (e.g., <code>03xxxxxxxxx</code>) or 13-digit CNIC to fetch details from the mainframe.",
    "bot_active": True,
    "maintenance_msg": "🔧 Bot is under maintenance. Please wait...",
    "footer": "👑 Database by Owais &amp; Liaqat"
}

def load_config():
    data = redis_get("bot_config")
    if data and isinstance(data, dict):
        print("✅ Config loaded from Upstash Redis")
        return data
    print("⚠️ Using default config")
    return DEFAULT_CONFIG.copy()

def save_config():
    redis_set("bot_config", json.dumps(config))
    print("✅ Config saved to Upstash Redis")

config = load_config()

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
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook set: {WEBHOOK_URL}")
    except Exception as e:
        print(f"❌ Webhook failed: {e}")

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

def get_unjoined_channels(user_id):
    unjoined = []
    for ch in config["channels"]:
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
        markup.add(InlineKeyboardButton(f"📢 Join @{name}", url=f"https://t.me/{name}"))
    ch_list = "\n".join([f"• {ch}" for ch in unjoined])
    bot.send_message(chat_id,
        f"<b>🚫 ACCESS DENIED!</b>\n\nPehle yeh channels join karo:\n{ch_list}\n\n"
        f"<i>⚠️ Channel chhoda to access kho jaoge!</i>",
        reply_markup=markup
    )

def is_admin(user_id):
    return user_id == ADMIN_ID

def admin_panel_markup():
    markup = InlineKeyboardMarkup(row_width=2)
    toggle_text = "🔴 Bot OFF" if config["bot_active"] else "🟢 Bot ON"
    markup.add(
        InlineKeyboardButton("📢 Channels", callback_data="admin_channels"),
        InlineKeyboardButton("✏️ Welcome Msg", callback_data="admin_welcome"),
        InlineKeyboardButton(toggle_text, callback_data="admin_toggle"),
        InlineKeyboardButton("🔧 Maintenance Msg", callback_data="admin_maintenance"),
        InlineKeyboardButton("👣 Footer", callback_data="admin_footer"),
        InlineKeyboardButton("📊 Bot Status", callback_data="admin_status"),
    )
    return markup

def admin_panel_text():
    status   = "🟢 ACTIVE" if config["bot_active"] else "🔴 MAINTENANCE"
    channels = "\n".join(config["channels"]) if config["channels"] else "None"
    return (
        f"<b>👑 ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Status: {status}\n"
        f"Channels:\n{channels}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Button dabao kuch update karne ke liye</i>"
    )

pending_action = {}

@bot.message_handler(commands=["admin"])
def admin_cmd(message):
    if message.chat.type != "private": return
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ You are not admin!")
        return
    bot.send_message(message.chat.id, admin_panel_text(), reply_markup=admin_panel_markup())

@bot.message_handler(commands=["start"])
def start_msg(message):
    if message.chat.type in ["group", "supergroup", "channel"]: return
    if is_admin(message.from_user.id):
        bot.reply_to(message,
            "<b>👑 Welcome Admin Owais!</b>\n\n"
            "Use /admin to open Admin Panel.\n"
            "Or send any number/CNIC to search."
        )
        return
    unjoined = get_unjoined_channels(message.from_user.id)
    if unjoined:
        send_join_alert(message.chat.id, unjoined)
        return
    bot.reply_to(message,
        f"<b>🛡️ WELCOME TO PRO DATABASE BOT</b>\n\n"
        f"Access Granted! ✅\n"
        f"{config['welcome_msg']}\n\n"
        f"<i>⚡ Powered by Owais &amp; Liaqat</i>"
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_") and is_admin(c.from_user.id))
def admin_callbacks(call):
    data = call.data

    if data == "admin_status":
        status   = "🟢 ACTIVE" if config["bot_active"] else "🔴 MAINTENANCE"
        channels = "\n".join(config["channels"]) if config["channels"] else "None"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,
            f"<b>📊 BOT STATUS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Status: {status}\n"
            f"Channels: {channels}\n"
            f"Welcome: {config['welcome_msg'][:60]}...\n"
            f"Footer: {config['footer']}\n"
            f"Maintenance: {config['maintenance_msg'][:60]}...\n"
        )

    elif data == "admin_toggle":
        config["bot_active"] = not config["bot_active"]
        save_config()
        status = "🟢 ACTIVE" if config["bot_active"] else "🔴 MAINTENANCE"
        bot.answer_callback_query(call.id, f"Bot is now {status}")
        try:
            bot.edit_message_text(admin_panel_text(), call.message.chat.id, call.message.message_id, reply_markup=admin_panel_markup())
        except: pass

    elif data == "admin_channels":
        bot.answer_callback_query(call.id)
        channels = "\n".join(config["channels"]) if config["channels"] else "None"
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("➕ Add Channel", callback_data="admin_ch_add"),
            InlineKeyboardButton("➖ Remove Channel", callback_data="admin_ch_remove"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_back")
        )
        bot.send_message(call.message.chat.id,
            f"<b>📢 CHANNELS</b>\n━━━━━━━━━━━━━━━━━━━\n{channels}\n━━━━━━━━━━━━━━━━━━━",
            reply_markup=markup
        )

    elif data == "admin_ch_add":
        bot.answer_callback_query(call.id)
        pending_action[call.from_user.id] = "add_channel"
        bot.send_message(call.message.chat.id, "Channel username bhejo (e.g. <code>@mychannel</code>):")

    elif data == "admin_ch_remove":
        bot.answer_callback_query(call.id)
        if not config["channels"]:
            bot.send_message(call.message.chat.id, "Koi channel nahi hai!")
            return
        markup = InlineKeyboardMarkup()
        for ch in config["channels"]:
            markup.add(InlineKeyboardButton(f"❌ {ch}", callback_data=f"rmch_{ch}"))
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="admin_channels"))
        bot.send_message(call.message.chat.id, "Konsa channel remove karna hai?", reply_markup=markup)

    elif data == "admin_welcome":
        bot.answer_callback_query(call.id)
        pending_action[call.from_user.id] = "set_welcome"
        bot.send_message(call.message.chat.id,
            f"<b>Current:</b>\n{config['welcome_msg']}\n\nNaya welcome message bhejo:")

    elif data == "admin_maintenance":
        bot.answer_callback_query(call.id)
        pending_action[call.from_user.id] = "set_maintenance"
        bot.send_message(call.message.chat.id,
            f"<b>Current:</b>\n{config['maintenance_msg']}\n\nNaya maintenance message bhejo:")

    elif data == "admin_footer":
        bot.answer_callback_query(call.id)
        pending_action[call.from_user.id] = "set_footer"
        bot.send_message(call.message.chat.id,
            f"<b>Current:</b>\n{config['footer']}\n\nNaya footer bhejo:")

    elif data == "admin_back":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, admin_panel_text(), reply_markup=admin_panel_markup())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rmch_") and is_admin(c.from_user.id))
def remove_channel_cb(call):
    ch = call.data.replace("rmch_", "")
    if ch in config["channels"]:
        config["channels"].remove(ch)
        save_config()
        bot.answer_callback_query(call.id, f"✅ {ch} removed!")
        bot.send_message(call.message.chat.id, f"✅ <b>{ch}</b> remove ho gaya!")
    else:
        bot.answer_callback_query(call.id, "Channel nahi mila!")

@bot.message_handler(func=lambda m: True)
def fetch_data(message):
    if message.chat.type in ["group", "supergroup", "channel"]: return

    user_id = message.from_user.id

    if is_admin(user_id) and user_id in pending_action:
        action = pending_action.pop(user_id)
        text   = message.text.strip()
        if action == "add_channel":
            ch = text if text.startswith("@") else f"@{text}"
            if ch not in config["channels"]:
                config["channels"].append(ch)
                save_config()
                bot.reply_to(message, f"✅ <b>{ch}</b> add ho gaya!")
            else:
                bot.reply_to(message, f"⚠️ {ch} already hai!")
        elif action == "set_welcome":
            config["welcome_msg"] = text
            save_config()
            bot.reply_to(message, "✅ Welcome message update ho gaya!")
        elif action == "set_maintenance":
            config["maintenance_msg"] = text
            save_config()
            bot.reply_to(message, "✅ Maintenance message update ho gaya!")
        elif action == "set_footer":
            config["footer"] = text
            save_config()
            bot.reply_to(message, "✅ Footer update ho gaya!")
        return

    if not config["bot_active"] and not is_admin(user_id):
        bot.reply_to(message, config["maintenance_msg"])
        return

    if not is_admin(user_id):
        unjoined = get_unjoined_channels(user_id)
        if unjoined:
            send_join_alert(message.chat.id, unjoined)
            return

    query    = message.text.strip()
    wait_msg = bot.reply_to(message, "<b>⏳ Scanning King OwAiS Mainframe...</b>")
    params   = {"key": API_KEY, "phone": query.replace("-", "").replace(" ", "")}

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
            bot.edit_message_text("<b>⚠️ NO RECORD FOUND IN DATABASE!</b>",
                chat_id=message.chat.id, message_id=wait_msg.message_id)
            return

        def is_censored(rec):
            vals = [str(rec.get("full_name","") or ""), str(rec.get("phone","") or ""), str(rec.get("cnic","") or "")]
            real = [v for v in vals if v.strip()]
            return all(set(v.replace(" ","")) <= {"*"} for v in real) if real else True

        if all(is_censored(r) for r in records):
            bot.edit_message_text(
                "<b>⚠️ NO RECORD FOUND IN DATABASE!</b>\n\n<i>This number/CNIC has no data in our mainframe.</i>",
                chat_id=message.chat.id, message_id=wait_msg.message_id)
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

        full_msg = ""
        map_url = None
        static_url = None
        file_num = 0

        for p in persons.values():
            file_num += 1
            sims_list = sorted(p["numbers"])
            sims_text = ""
            for i, num in enumerate(sims_list, 1):
                sims_text += f"{i}. <code>{num}</code> - {detectNetwork(num)}\n"

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
                if not map_url:
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

        full_msg += f"━━━━━━━━━━━━━━━━━━━\n<i>{config['footer']}</i>"

        btn = InlineKeyboardMarkup()
        if map_url:
            btn.add(InlineKeyboardButton("🗺️ Open Map Location", url=map_url))

        if map_url and static_url:
            try:
                bot.send_photo(message.chat.id, photo=static_url, caption=full_msg, reply_markup=btn, parse_mode="HTML")
            except:
                bot.send_message(message.chat.id, full_msg, reply_markup=btn, disable_web_page_preview=True)
        else:
            bot.send_message(message.chat.id, full_msg, disable_web_page_preview=True)

    except Exception as e:
        print(f"Error: {e}")
        try:
            bot.edit_message_text("<b>❌ API ERROR:</b> Server is busy or offline.",
                chat_id=message.chat.id, message_id=wait_msg.message_id)
        except: pass

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
