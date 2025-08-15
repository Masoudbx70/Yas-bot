import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ChatPermissions

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5872842793
GROUP_ID = -1002483971970
DATA_FILE = "data.json"

# --- بارگذاری داده‌ها از فایل ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"verified_users": [], "unverified_message_count": {}, "blacklist_users": []}

# --- ذخیره داده‌ها در فایل ---
def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "verified_users": list(verified_users),
            "unverified_message_count": unverified_message_count,
            "blacklist_users": list(blacklist_users)
        }, f, ensure_ascii=False, indent=2)

# --- داده‌های اصلی ---
data = load_data()
verified_users = set(data["verified_users"])
unverified_message_count = data["unverified_message_count"]
blacklist_users = set(data["blacklist_users"])

user_states = {}

# --- شروع ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in verified_users:
        keyboard = [[InlineKeyboardButton("احراز هویت", callback_data="verify")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "سلام این ربات برای احراز هویت شما در پروژه پویان بتن نیشابور طراحی شده و اطلاعات شما محفوظ خواهد ماند",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("✅ شما قبلاً احراز هویت کرده‌اید.")

# --- کلیک روی دکمه احراز هویت ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "verify":
        user_states[query.from_user.id] = "ASK_NAME"
        await query.message.reply_text("نام شما چیست؟")

# --- دریافت نام ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_states.get(user_id) == "ASK_NAME":
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"نام کاربر {update.effective_user.full_name} ({user_id}): {text}")
        verified_users.add(user_id)
        save_data()
        user_states.pop(user_id, None)
        await update.message.reply_text("✅ احراز هویت شما با موفقیت انجام شد.")

# --- بررسی پیام‌های گروه ---
async def group_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text.strip().lower()

    if user_id in blacklist_users:
        await update.message.delete()
        return

    if user_id not in verified_users:
        unverified_message_count[str(user_id)] = unverified_message_count.get(str(user_id), 0) + 1
        save_data()

        # هشدار به کاربر
        keyboard = [[InlineKeyboardButton("احراز هویت", url="https://t.me/hostpuyanbot?start=verify")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "شما احراز هویت در ربات انجام نداده‌اید.\nلطفا دکمه زیر را انتخاب کنید:",
            reply_markup=reply_markup
        )

        # اگر بیشتر از 3 پیام ارسال کرد → محدود شود
        if unverified_message_count[str(user_id)] >= 3:
            await context.bot.restrict_chat_member(
                chat_id=GROUP_ID,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            blacklist_users.add(user_id)
            save_data()
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"⛔ کاربر {update.effective_user.full_name} به دلیل عدم احراز هویت مسدود شد."
            )
        return

    # اگر پیام سلام بود
    if message_text in ["سلام", "salam", "سلام علیکم"]:
        await update.message.reply_text(f"سلام و عرض ادب خدمت {update.effective_user.first_name} 🌹")

# --- راه‌اندازی ربات ---
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, group_message_handler))

if __name__ == "__main__":
    app.run_polling()
