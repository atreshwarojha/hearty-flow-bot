import asyncio
from telegram import Update, ReplyKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== CONFIG ==================
BOT_TOKEN = "8335740705:AAFeYZinoZ3rN-_l1rW7y4DUsyWJzhvhcLI"

FREE_CHAT_DURATION = 30 * 60
PAID_30 = 30 * 60
PAID_60 = 60 * 60

# ================== GLOBAL STATE ==================
users = {}                     # user_id -> {gender, status}
waiting_males = []
waiting_females = []
active_chats = {}              # user_id -> partner_id
paid_time_balance = {}         # user_id -> seconds
free_chat_used = set()         # user_ids who already used free chat

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["👦 Male", "👧 Female"]]
    await update.message.reply_text(
        "Welcome 👋\n\nPlease select your gender:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=True
        ),
    )

# ================== GENDER ==================
async def handle_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text not in ["👦 Male", "👧 Female"]:
        return

    gender = "male" if "Male" in text else "female"
    users[user_id] = {"gender": gender, "status": "idle"}

    await update.message.reply_text(
        "✅ Gender saved.\n\nTap below to find a chat partner.",
        reply_markup=ReplyKeyboardMarkup(
            [["🔍 Find a chat partner"]],
            resize_keyboard=True,
        ),
    )

# ================== FIND MATCH ==================
async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text("Send /start first.")
        return

    gender = users[user_id]["gender"]
    users[user_id]["status"] = "waiting"

    if gender == "male":
        if waiting_females:
            partner = waiting_females.pop(0)
            await start_chat(user_id, partner, context)
        else:
            waiting_males.append(user_id)
            await update.message.reply_text("⏳ Waiting for a female partner…")
    else:
