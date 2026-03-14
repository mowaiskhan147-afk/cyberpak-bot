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

UPSTASH_URL   = "https://precise-coyote-67987.upstash.io"
UPSTASH_TOKEN = "gQAAAAAAAQmTAAIncDI0YTVhNjYwOGJjMzk0NTIxYTYyYTA3MzM5YWY4ZmEyOHAyNjc5ODc"

def redis_set(key, value):
    try:
        r = requests.post(
            f"{UPSTASH_URL}/set/{key}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            json=value, timeout=5
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
def redis_sadd(set_key, member):
    try:
        requests.get(
            f"{UPSTASH_URL}/sadd/{set_key}/{member}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            timeout=5
        )
    except: pass

def redis_smembers(set_key):
    try:
        r = requests.get(
            f"{UPSTASH_URL}/smembers/{set_key}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            timeout=5
        )
        return r.json().get("result", [])
    except:
        return []

def redis_hincrby(hash_key, field, amount=1):
    try:
        requests.get(
            f"{UPSTASH_URL}/hincrby/{hash_key}/{field}/{amount}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            timeout=5
        )
    except: pass

def redis_hget(hash_key, field):
    try:
        r = requests.get(
            f"{UPSTASH_URL}/hget/{hash_key}/{field}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            timeout=5
        )
        return r.json().get("result", "0") or "0"
    except:
        return "0"

def track_user(user):
    uid = str(user.id)
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    uname = f"@{user.username}" if user.username else "No username"
    user_data = json.dumps({"id": user.id, "name": name, "username": uname, "joined": time.strftime("%Y-%m-%d %H:%M")})
    redis_sadd("bot_users", uid)
    try:
        requests.get(
            f"{UPSTASH_URL}/set/user:{uid}/{requests.utils.quote(user_data)}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            timeout=5
        )
    except: pass


DEFAULT_CONFIG = {
    "channels": ["@SoloHunter3", "@o_p_trick", "@cyberxos8"],
    "welcome_msg": "Send me any Pakistani Number (e.g., <code>03xxxxxxxxx</code>) or 13-digit CNIC to fetch details.",
    "bot_active": True,
    "maintenance_msg": "🔧 Bot is under maintenance. Please wait...",
    "footer": "👑 Made by OWAiS &amp; Liaqat"
}

def load_config():
    data = redis_get("bot_config")
    if data and isinstance(data, dict):
        return data
    return DEFAULT_CONFIG.copy()

def save_config():
    redis_set("bot_config", json.dumps(config))

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

# ── Network detector ───────────────────────────────────────────────────────
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
    # 3-digit prefix check first
    for prefix, network in prefixes.items():
        if n.startswith(prefix):
            return network
    return "❓ Unknown"

# ── Query type detector ────────────────────────────────────────────────────
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

# ── Subscription ───────────────────────────────────────────────────────────
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

# ── Admin panel ────────────────────────────────────────────────────────────
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
        InlineKeyboardButton("👥 Users List", callback_data="admin_users"),
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


@bot.message_handler(commands=["users"])
def users_cmd(message):
    if message.chat.type != "private": return
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ You are not admin!")
        return
    wait = bot.reply_to(message, "⏳ Loading users...")
    try:
        user_ids = redis_smembers("bot_users")
        total = len(user_ids)
        if total == 0:
            bot.edit_message_text("📊 No users yet!", chat_id=message.chat.id, message_id=wait.message_id)
            return
        # Build user list (max 50 recent)
        user_list = ""
        for i, uid in enumerate(user_ids[-50:], 1):
            try:
                r = requests.get(
                    f"{UPSTASH_URL}/get/user:{uid}",
                    headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
                    timeout=5
                )
                udata = r.json().get("result")
                if udata:
                    u = json.loads(udata)
                    searches = redis_hget("user_searches", uid)
                    user_list += f"{i}. {u['name']} | {u['username']} | 🔍{searches}\n"
                else:
                    user_list += f"{i}. ID: {uid}\n"
            except:
                user_list += f"{i}. ID: {uid}\n"

        msg = (
            f"<b>👥 BOT USERS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Total Users: <b>{total}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"<code>{user_list}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Showing last 50 users</i>"
        )
        bot.edit_message_text(msg, chat_id=message.chat.id, message_id=wait.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {e}", chat_id=message.chat.id, message_id=wait.message_id)

@bot.message_handler(commands=["start"])
def start_msg(message):
    if message.chat.type in ["group", "supergroup", "channel"]: return
    track_user(message.from_user)
    if is_admin(message.from_user.id):
        bot.reply_to(message,
            "<b>👑 Welcome Admin OWAiS!</b>\n\n"
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
        f"<i>⚡ Powered by OWAiS &amp; Liaqat</i>"
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_") and is_admin(c.from_user.id))
def admin_callbacks(call):
    data = call.data
    if data == "admin_status":
        status   = "🟢 ACTIVE" if config["bot_active"] else "🔴 MAINTENANCE"
        channels = "\n".join(config["channels"]) if config["channels"] else "None"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,
            f"<b>📊 BOT STATUS</b>\n━━━━━━━━━━━━━━━━━━━\n"
            f"Status: {status}\nChannels: {channels}\n"
            f"Welcome: {config['welcome_msg'][:60]}...\n"
            f"Footer: {config['footer']}\n"
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
        bot.send_message(call.message.chat.id, f"<b>Current:</b>\n{config['welcome_msg']}\n\nNaya welcome message bhejo:")
    elif data == "admin_maintenance":
        bot.answer_callback_query(call.id)
        pending_action[call.from_user.id] = "set_maintenance"
        bot.send_message(call.message.chat.id, f"<b>Current:</b>\n{config['maintenance_msg']}\n\nNaya maintenance message bhejo:")
    elif data == "admin_footer":
        bot.answer_callback_query(call.id)
        pending_action[call.from_user.id] = "set_footer"
        bot.send_message(call.message.chat.id, f"<b>Current:</b>\n{config['footer']}\n\nNaya footer bhejo:")
    elif data == "admin_users":
        bot.answer_callback_query(call.id)
        try:
            user_ids = redis_smembers("bot_users")
            total = len(user_ids)
            bot.send_message(call.message.chat.id,
                f"<b>👥 Total Users: {total}</b>\n"
                f"Use /users command for full list with details."
            )
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Error: {e}")

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

# ── Main handler ───────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True)
def fetch_data(message):
    if message.chat.type in ["group", "supergroup", "channel"]: return

    user_id = message.from_user.id

    # Admin pending actions
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

    track_user(message.from_user)
    redis_hincrby("user_searches", str(user_id))
    query  = message.text.strip()
    qtype  = detect_query_type(query)
    qlabel = query_type_label(qtype)

    # ── Searching message ─────────────────────────────────────────────────
    wait_msg = bot.reply_to(message,
        f"<b>🔎 Searching Database...</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📝 Query: <code>{query}</code>\n"
        f"📋 Type: {qlabel}\n"
        f"⏳ Please wait..."
    )

    params = {"key": API_KEY, "phone": query.replace("-", "").replace(" ", "")}

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
                f"<b>🔎 SEARCH COMPLETE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📝 Query: <code>{query}</code>\n"
                f"📋 Type: {qlabel}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ <b>NO RECORD FOUND IN DATABASE!</b>",
                chat_id=message.chat.id, message_id=wait_msg.message_id
            )
            return

        def is_censored(rec):
            vals = [str(rec.get("full_name","") or ""), str(rec.get("phone","") or ""), str(rec.get("cnic","") or "")]
            real = [v for v in vals if v.strip()]
            return all(set(v.replace(" ","")) <= {"*"} for v in real) if real else True

        if all(is_censored(r) for r in records):
            bot.edit_message_text(
                f"<b>🔎 SEARCH COMPLETE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📝 Query: <code>{query}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ <b>NO RECORD FOUND IN DATABASE!</b>",
                chat_id=message.chat.id, message_id=wait_msg.message_id
            )
            return

        bot.delete_message(message.chat.id, wait_msg.message_id)

        def clr(v):
            return v if v and str(v).lower() not in ("none", "n/a", "") else "N/A"

        # Merge ALL records into ONE — collect all numbers, best name/cnic/address
        merged = {"name": "N/A", "cnic": "N/A", "address": "N/A", "father": "N/A", "numbers": set()}
        for rec in records:
            name    = clr(rec.get("full_name") or rec.get("name") or "")
            cnic    = clr(rec.get("cnic") or "")
            address = clr(rec.get("address") or "")
            father  = clr(rec.get("father_name") or "")
            ph      = rec.get("phone") or rec.get("mobile")
            if name    != "N/A": merged["name"]    = name
            if cnic    != "N/A": merged["cnic"]    = cnic
            if address != "N/A": merged["address"] = address
            if father  != "N/A": merged["father"]  = father
            if ph: merged["numbers"].add(str(ph))

        for p in [merged]:
            sims_list = sorted(p["numbers"])
            sims_text = ""
            for i, num in enumerate(sims_list, 1):
                sims_text += f"  {i}) <code>{num}</code> — {detectNetwork(num)}\n"

            address = p["address"]

            # ── Result message ─────────────────────────────────────────
            result = (
                f"<b>🔎 PHONE/CNIC Information</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Name:</b> {p['name']}\n"
                f"🪪 <b>CNIC:</b> <code>{p['cnic']}</code>\n"
                f"📍 <b>Address:</b> {address}\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"📱 <b>Registered Numbers ({len(sims_list)}):</b>\n"
                f"{sims_text}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"<i>✨ {config['footer']}</i>\n"
                f"<i>🔗 <a href='https://t.me/SoloHunter3'>@SoloHunter3</a> | <a href='https://t.me/o_p_trick'>@o_p_trick</a></i>"
            )

            btn = InlineKeyboardMarkup()
            map_url = None
            static_url = None

            if address != "N/A":
                enc        = urllib.parse.quote(address)
                map_url    = f"https://maps.google.com/maps?q={enc}"
                static_url = (
                    f"https://maps.googleapis.com/maps/api/staticmap"
                    f"?center={enc}&zoom=14&size=600x300&scale=2"
                    f"&markers=color:red%7C{enc}"
                )
                btn.add(InlineKeyboardButton("🗺️ Open Map Location", url=map_url))

            if map_url and static_url:
                try:
                    bot.send_photo(message.chat.id, photo=static_url, caption=result, reply_markup=btn, parse_mode="HTML")
                except:
                    bot.send_message(message.chat.id, result, reply_markup=btn, disable_web_page_preview=True)
            else:
                bot.send_message(message.chat.id, result, disable_web_page_preview=True)

    except Exception as e:
        print(f"Error: {e}")
        try:
            bot.edit_message_text("<b>❌ API ERROR:</b> Server is busy or offline.",
                chat_id=message.chat.id, message_id=wait_msg.message_id)
        except: pass

# ═══════════════════════════════════════════════════
# 👑 API USER MANAGEMENT (username-based access)
# ═══════════════════════════════════════════════════

USERS_API = "https://vercel-api1-jade.vercel.app/api/users"
ADMIN_SECRET = "kingowais-secret-2025"

def call_users_api(action, **kwargs):
    """Call Vercel users API with admin secret."""
    try:
        payload = {"admin_secret": ADMIN_SECRET, "action": action, **kwargs}
        r = requests.post(USERS_API, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def call_users_api_get(username):
    """Check if username has access."""
    try:
        r = requests.get(f"{USERS_API}?username={username}", timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

# /adduser @username 30
@bot.message_handler(commands=["adduser"])
def cmd_adduser(message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "❌ Admin only!")
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ Usage: /adduser @username [days]\nExample: /adduser @owaisking 30\nDays=0 means lifetime.")
    username = parts[1].replace("@", "").strip()
    days = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 30
    result = call_users_api("add", username=username, days=days, label=username)
    if result.get("ok"):
        expiry = result.get("expires_at", "never")
        bot.reply_to(message,
            f"✅ <b>User Added!</b>\n\n"
            f"👤 Username: <code>@{username}</code>\n"
            f"📅 Days: <b>{days}</b>\n"
            f"⏰ Expires: <b>{expiry[:10] if expiry != 'never' else '♾️ Lifetime'}</b>\n\n"
            f"🔗 API Link:\n"
            f"<code>https://vercel-api1-jade.vercel.app/api/usersearch?username={username}&phone=03XXXXXXXXX</code>",
            parse_mode="HTML"
        )
    else:
        bot.reply_to(message, f"❌ Error: {result.get('error', 'Unknown')}")

# /removeuser @username
@bot.message_handler(commands=["removeuser"])
def cmd_removeuser(message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "❌ Admin only!")
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ Usage: /removeuser @username")
    username = parts[1].replace("@", "").strip()
    result = call_users_api("remove", username=username)
    if result.get("ok"):
        bot.reply_to(message, f"🗑️ <b>@{username}</b> removed successfully!", parse_mode="HTML")
    else:
        bot.reply_to(message, f"❌ Error: {result.get('error', 'Unknown')}")

# /extenduser @username 15
@bot.message_handler(commands=["extenduser"])
def cmd_extenduser(message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "❌ Admin only!")
    parts = message.text.split()
    if len(parts) < 3:
        return bot.reply_to(message, "⚠️ Usage: /extenduser @username days\nExample: /extenduser @owaisking 15")
    username = parts[1].replace("@", "").strip()
    days = int(parts[2]) if parts[2].isdigit() else 30
    result = call_users_api("extend", username=username, days=days)
    if result.get("ok"):
        bot.reply_to(message,
            f"⏩ <b>Extended!</b>\n\n"
            f"👤 @{username}\n"
            f"➕ Added: <b>{days} days</b>\n"
            f"⏰ New Expiry: <b>{result.get('new_expiry', 'N/A')[:10]}</b>",
            parse_mode="HTML"
        )
    else:
        bot.reply_to(message, f"❌ Error: {result.get('error', 'Unknown')}")

# /toggleuser @username
@bot.message_handler(commands=["toggleuser"])
def cmd_toggleuser(message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "❌ Admin only!")
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ Usage: /toggleuser @username")
    username = parts[1].replace("@", "").strip()
    result = call_users_api("toggle", username=username)
    if result.get("ok"):
        status = "🟢 Enabled" if result.get("active") else "🔴 Disabled"
        bot.reply_to(message, f"🔄 <b>@{username}</b> is now <b>{status}</b>", parse_mode="HTML")
    else:
        bot.reply_to(message, f"❌ Error: {result.get('error', 'Unknown')}")

# /apiusers — list all API users
@bot.message_handler(commands=["apiusers"])
def cmd_apiusers(message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "❌ Admin only!")
    result = call_users_api("list")
    if not result.get("ok"):
        return bot.reply_to(message, f"❌ Error: {result.get('error')}")
    users = result.get("users", [])
    if not users:
        return bot.reply_to(message, "📭 No API users registered yet.")
    lines = [f"👥 <b>API Users</b> ({len(users)} total)\n"]
    for u in users:
        status = "🟢" if u.get("active") else "🔴"
        days = u.get("days_left")
        exp = f"{days}d left" if days is not None else "♾️"
        lines.append(f"{status} @{u['username']} — <b>{exp}</b>")
    bot.reply_to(message, "\n".join(lines), parse_mode="HTML")

# /checkuser @username
@bot.message_handler(commands=["checkuser"])
def cmd_checkuser(message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "❌ Admin only!")
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "⚠️ Usage: /checkuser @username")
    username = parts[1].replace("@", "").strip()
    result = call_users_api_get(username)
    if result.get("ok"):
        days = result.get("days_left")
        exp_str = f"{days} din baqi" if days is not None else "♾️ Lifetime"
        bot.reply_to(message,
            f"✅ <b>@{username}</b>\n\n"
            f"📌 Status: 🟢 Active\n"
            f"⏰ Expiry: <b>{result.get('expires_at', 'N/A')[:10]}</b>\n"
            f"📅 Remaining: <b>{exp_str}</b>",
            parse_mode="HTML"
        )
    else:
        bot.reply_to(message, f"❌ {result.get('error', 'Not found')}")

# /apicmds — show API user management commands
@bot.message_handler(commands=["apicmds"])
def cmd_apicmds(message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "❌ Admin only!")
    bot.reply_to(message,
        "👑 <b>API User Management Commands</b>\n\n"
        "➕ /adduser @user [days] — Add user (days=0 = lifetime)\n"
        "🗑️ /removeuser @user — Remove user\n"
        "⏩ /extenduser @user [days] — Extend expiry\n"
        "🔄 /toggleuser @user — Enable/disable\n"
        "✅ /checkuser @user — Check status\n"
        "👥 /apiusers — List all users\n\n"
        "🔗 <b>API Endpoint:</b>\n"
        "<code>https://vercel-api1-jade.vercel.app/api/usersearch?username=USERNAME&phone=03XXXXXXXXX</code>",
        parse_mode="HTML"
    )

# ═══════════════════════════════════════════════════
# 🔑 DB KEY GENERATOR via bot
# ═══════════════════════════════════════════════════

DBKEYGEN_API = "https://vercel-api1-jade.vercel.app/api/dbkeygen"

# ── Parse time string: "30d", "6h", "1d12h", "2d" ─────────────────────────
def parse_time(s):
    """Returns (days, hours) from string like '30d', '6h', '1d6h', '2d12h'"""
    import re
    s = s.lower().strip()
    d = int(m.group(1)) if (m := re.search(r'(\d+)d', s)) else 0
    h = int(m.group(1)) if (m := re.search(r'(\d+)h', s)) else 0
    return d, h

# /genkey label time
# Examples:
#   /genkey owaisking 30d
#   /genkey Zoya 6h
#   /genkey noor 1d12h
#   /genkey @HiddenXnoob 7d
@bot.message_handler(commands=["genkey"])
def cmd_genkey(message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "❌ Admin only!")
    parts = message.text.split()
    if len(parts) < 3:
        return bot.reply_to(message,
            "⚠️ <b>Usage:</b> /genkey &lt;label&gt; &lt;time&gt;\n\n"
            "<b>Examples:</b>\n"
            "/genkey @owaisking 30d\n"
            "/genkey Zoya 6h\n"
            "/genkey noor 1d12h\n"
            "/genkey @HiddenXnoob 7d",
            parse_mode="HTML"
        )

    label     = parts[1].replace("@", "").strip()
    time_str  = parts[2]
    days, hrs = parse_time(time_str)

    if days == 0 and hrs == 0:
        return bot.reply_to(message,
            "⚠️ Invalid time! Use like: 30d / 6h / 1d12h"
        )

    wait = bot.reply_to(message, "⏳ Generating key...")
    try:
        r = requests.post(DBKEYGEN_API, json={
            "admin_secret": ADMIN_SECRET,
            "label":        label,
            "days":         days,
            "hours":        hrs
        }, timeout=10)
        data = r.json()
    except Exception as e:
        return bot.edit_message_text(f"❌ Error: {e}", message.chat.id, wait.message_id)

    if not data.get("key"):
        return bot.edit_message_text(
            f"❌ Failed: {data.get('error','Unknown error')}",
            message.chat.id, wait.message_id
        )

    key      = data["key"]
    expires  = data.get("expires", "N/A")
    expiry   = data.get("expiry", time_str)   # e.g. "1d 12h"
    exp_dt   = expires[:16].replace("T", " ") if expires != "N/A" else "N/A"

    bot.edit_message_text(
        f"✅ <b>Key Generated!</b>\n\n"
        f"👤 Label : <code>{label}</code>\n"
        f"🔑 Key   : <code>{key}</code>\n"
        f"⏱ Expiry: <b>{expiry}</b>\n"
        f"📅 Expires: <b>{exp_dt} UTC</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>CNIC:</b>\n"
        f"<code>https://vercel-api1-jade.vercel.app/api/dbsearch?cnic=XXXXXXXXXXXXX&apikey={key}&tguser={label}</code>\n\n"
        f"📱 <b>Phone:</b>\n"
        f"<code>https://vercel-api1-jade.vercel.app/api/dbsearch?phone=03XXXXXXXXX&apikey={key}&tguser={label}</code>",
        message.chat.id, wait.message_id,
        parse_mode="HTML"
    )

@bot.message_handler(commands=["keycmds"])
def cmd_keycmds(message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "❌ Admin only!")
    bot.reply_to(message,
        "🔑 <b>DB Key Commands</b>\n\n"
        "➕ /genkey &lt;label&gt; &lt;time&gt;\n\n"
        "<b>Time formats:</b>\n"
        "  30d  → 30 days\n"
        "  6h   → 6 hours\n"
        "  1d12h → 1 day 12 hours\n\n"
        "<b>Examples:</b>\n"
        "  /genkey @owaisking 30d\n"
        "  /genkey Zoya 6h\n"
        "  /genkey noor 1d12h\n\n"
        "📋 <b>Key format:</b> <code>KODB-XXXX-XXXX-XXXX</code>\n"
        "🔗 <b>Usage:</b>\n"
        "<code>...dbsearch?phone=03xxx&apikey=KODB-xxx&tguser=owaisking</code>",
        parse_mode="HTML"
    )

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
