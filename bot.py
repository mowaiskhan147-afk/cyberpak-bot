import os
import sys
import logging
from io import BytesIO
from typing import Dict, List
from uuid import uuid4

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_data: Dict[int, dict] = {}
NUMBERS_PER_PAGE = 10

# Variables
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", "10000"))
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL") 

# --- Helper functions ---
def extract_numbers_from_text(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]

def process_numbers(raw_numbers: List[str]) -> dict:
    total = len(raw_numbers)
    unique = list(dict.fromkeys(raw_numbers))
    return {"total": total, "unique": unique, "duplicates": total - len(unique)}

def format_number_for_display(number: str) -> str:
    return f"+{number}"

def get_page_data(numbers: List[str], page: int, per_page: int = NUMBERS_PER_PAGE):
    start = (page - 1) * per_page
    end = start + per_page
    return numbers[start:end], max(1, (len(numbers) + per_page - 1) // per_page)

def build_pagination_keyboard(user_id: int, page: int, total_pages: int, search_active: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"page:{user_id}:{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"page:{user_id}:{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton("🔍 Search", callback_data=f"search:{user_id}"),
        InlineKeyboardButton("📋 Copy Page", callback_data=f"copy_page:{user_id}:{page}"),
    ])
    buttons.append([
        InlineKeyboardButton("📁 Copy All", callback_data=f"copy_all:{user_id}"),
        InlineKeyboardButton("⬇️ Download", callback_data=f"download:{user_id}"),
    ])
    buttons.append([InlineKeyboardButton("🔄 Upload Another", callback_data=f"upload_another:{user_id}")])
    
    if search_active:
        buttons.append([InlineKeyboardButton("❌ Clear Search", callback_data=f"clear_search:{user_id}")])
    return InlineKeyboardMarkup(buttons)

async def send_numbers_page(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int = None, message_id: int = None):
    data = user_data.get(user_id)
    if not data:
        msg = "Session expired. Please send a file again."
        if message_id:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg)
        else:
            await context.bot.send_message(chat_id=chat_id or update.effective_chat.id, text=msg)
        return
        
    numbers_to_show = data["filtered_numbers"] if data["search_active"] else data["unique_numbers"]
    current_page = data["current_page"]
    page_numbers, total_pages = get_page_data(numbers_to_show, current_page)

    if not numbers_to_show:
        text = "✨ No numbers match your search."
    else:
        text = (f"📊 *Statistics*\n• Total: {data['total']}\n• Unique: {len(data['unique_numbers'])}\n"
                f"• Duplicates removed: {data['duplicates']}\n\n*Numbers (page {current_page}/{total_pages})*:\n")
        lines = [f"{i}. `{format_number_for_display(num)}`" for i, num in enumerate(page_numbers, start=(current_page-1)*NUMBERS_PER_PAGE+1)]
        text += "\n".join(lines)

    keyboard = build_pagination_keyboard(user_id, current_page, total_pages, data["search_active"])

    if message_id:
        await context.bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await context.bot.send_message(chat_id=chat_id or update.effective_chat.id, text=text, parse_mode="Markdown", reply_markup=keyboard)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to *Number Manager Bot*!\n\nSend me a `.txt` file with numbers.", parse_mode="Markdown")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    document = update.message.document
    
    if not document.file_name.endswith(".txt"):
        await update.message.reply_text("❌ Please send a `.txt` file.")
        return
        
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()
    raw_numbers = extract_numbers_from_text(file_content.decode("utf-8"))
    
    if not raw_numbers:
        await update.message.reply_text("❌ The file contains no valid numbers.")
        return
        
    processed = process_numbers(raw_numbers)
    user_data[user_id] = {
        "total": processed["total"],
        "unique_numbers": processed["unique"],
        "duplicates": processed["duplicates"],
        "current_page": 1,
        "search_active": False,
        "filtered_numbers": processed["unique"][:],
    }
    await send_numbers_page(update, context, user_id, chat_id)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "noop": return
    
    parts = query.data.split(":")
    action, target_user = parts[0], int(parts[1])
    user_id = update.effective_user.id
    
    if target_user != user_id:
        await query.edit_message_text("❌ This button is not for you.")
        return
        
    ud = user_data.get(user_id)
    if not ud:
        await query.edit_message_text("Session expired. Please send a file again.")
        return

    chat_id, message_id = query.message.chat_id, query.message.message_id

    if action == "page":
        ud["current_page"] = int(parts[2])
        await send_numbers_page(update, context, user_id, chat_id, message_id)
    elif action == "search":
        await query.edit_message_text("🔍 Please type the **last 4 digits** to search:\nExample: `7890`", parse_mode="Markdown")
    elif action == "clear_search":
        ud.update({"search_active": False, "filtered_numbers": ud["unique_numbers"][:], "current_page": 1})
        await send_numbers_page(update, context, user_id, chat_id, message_id)
    elif action == "copy_page":
        page_numbers, _ = get_page_data(ud["filtered_numbers"] if ud["search_active"] else ud["unique_numbers"], int(parts[2]))
        formatted = "\n".join(format_number_for_display(n) for n in page_numbers)
        # Fix for copy-paste issue
        msg = "📋 *Page " + parts[2] + ":*\n```\n" + formatted + "\n```"
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
    elif action == "copy_all":
        formatted = "\n".join(format_number_for_display(n) for n in ud["unique_numbers"])
        # Fix for copy-paste issue
        msg = "📋 *All numbers:*\n```\n" + formatted + "\n```"
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
    elif action == "download":
        formatted = "\n".join(format_number_for_display(n) for n in ud["unique_numbers"])
        file_bytes = BytesIO(formatted.encode("utf-8"))
        file_bytes.name = f"numbers_{uuid4().hex[:8]}.txt"
        await context.bot.send_document(chat_id=chat_id, document=file_bytes)
    elif action == "upload_another":
        user_data.pop(user_id, None)
        await query.edit_message_text("✅ Ready for a new file. Please send me a `.txt` file.")

async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ud = user_data.get(user_id)
    if not ud: return
    
    query_text = update.message.text.strip()
    ud["filtered_numbers"] = [num for num in ud["unique_numbers"] if num.endswith(query_text)]
    ud.update({"search_active": True, "current_page": 1})
    await send_numbers_page(update, context, user_id, update.effective_chat.id)

def main():
    logger.info("Script started! Checking variables...")
    
    if not TOKEN:
        logger.error("❌ CRITICAL ERROR: BOT_TOKEN is missing!")
        sys.exit(1)

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_file))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_query))

    if RENDER_URL:
        # Link ko safe banaya
        clean_url = RENDER_URL.rstrip("/")
        full_url = clean_url + "/" + TOKEN
        logger.info("Starting bot on Render Webhook...")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=full_url
        )
    else:
        logger.error("❌ CRITICAL ERROR: RENDER_EXTERNAL_URL is missing!")
        sys.exit(1)

if __name__ == "__main__":
    main()