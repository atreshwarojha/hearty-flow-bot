import asyncio
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    LabeledPrice
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"

# --------- GLOBAL STATE (in-memory) ----------
users = {}
waiting_males = []
waiting_females = []
active_chats = {}

FREE_CHAT_DURATION = 30 * 60   # 30 minutes
PAID_30 = 30 * 60
PAID_60 = 60 * 60

# --------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["👦 Male", "👧 Female"]]
    await update.message.reply_text(
        "Welcome 👋\n\nPlease select your gender:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=True
        )
    )

# --------- GENDER ----------
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
            [["🔍 Find a chat partner"]], resize_keyboard=True
        )
    )

# --------- MATCHING ----------
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
            await update.message.reply_text("⏳ Waiting for a female partner...")
    else:
        if waiting_males:
            partner = waiting_males.pop(0)
            await start_chat(partner, user_id, context)
        else:
            waiting_females.append(user_id)
            await update.message.reply_text("⏳ Waiting for a male partner...")

# --------- START CHAT ----------
async def start_chat(user1, user2, context):
    users[user1]["status"] = "chatting"
    users[user2]["status"] = "chatting"

    active_chats[user1] = user2
    active_chats[user2] = user1

    await context.bot.send_message(
        user1, "💬 Connected!\n⏱ Free chat started (30 minutes)"
    )
    await context.bot.send_message(
        user2, "💬 Connected!\n⏱ Free chat started (30 minutes)"
    )

    asyncio.create_task(end_chat_after_time(user1, user2, context, FREE_CHAT_DURATION))

# --------- END CHAT AFTER TIME ----------
async def end_chat_after_time(user1, user2, context, duration):
    await asyncio.sleep(duration)

    if user1 in active_chats and user2 in active_chats:
        keyboard = [
            ["⭐ 50 Stars – 30 minutes"],
            ["⭐ 90 Stars – 60 minutes"],
            ["❌ End chat"]
        ]

        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await context.bot.send_message(
            user1,
            "⏰ Session ended.\n\nContinue chatting?",
            reply_markup=markup
        )
        await context.bot.send_message(
            user2,
            "⏰ Session ended.\n\nContinue chatting?",
            reply_markup=markup
        )

        end_chat(user1, user2)

# --------- RELAY MESSAGES ----------
async def relay_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id in active_chats:
        partner = active_chats[user_id]
        await context.bot.send_message(partner, text)

# --------- END CHAT ----------
def end_chat(user1, user2):
    active_chats.pop(user1, None)
    active_chats.pop(user2, None)

    if user1 in users:
        users[user1]["status"] = "idle"
    if user2 in users:
        users[user2]["status"] = "idle"

# --------- STARS PAYMENT ----------
async def handle_paid_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if text == "⭐ 50 Stars – 30 minutes":
        prices = [LabeledPrice("30 minutes chat", 50)]
        await context.bot.send_invoice(
            chat_id=chat_id,
            title="30 Minute Chat",
            description="Continue chatting anonymously",
            payload="STARS_30",
            currency="XTR",
            prices=prices
        )

    elif text == "⭐ 90 Stars – 60 minutes":
        prices = [LabeledPrice("60 minutes chat", 90)]
        await context.bot.send_invoice(
            chat_id=chat_id,
            title="60 Minute Chat",
            description="Continue chatting anonymously",
            payload="STARS_60",
            currency="XTR",
            prices=prices
        )

    elif text == "❌ End chat":
        await update.message.reply_text(
            "Chat ended.\nYou can find a new partner anytime.",
            reply_markup=ReplyKeyboardMarkup(
                [["🔍 Find a chat partner"]],
                resize_keyboard=True
            )
        )

# --------- PAYMENT SUCCESS ----------
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload

    if user_id not in active_chats:
        await update.message.reply_text("Payment received. Waiting for a partner.")
        return

    partner = active_chats[user_id]

    if payload == "STARS_30":
        await update.message.reply_text("✅ 30 minutes added!")
        asyncio.create_task(end_chat_after_time(user_id, partner, context, PAID_30))

    elif payload == "STARS_60":
        await update.message.reply_text("✅ 60 minutes added!")
        asyncio.create_task(end_chat_after_time(user_id, partner, context, PAID_60))

# --------- APP ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("^(👦 Male|👧 Female)$"), handle_gender))
app.add_handler(MessageHandler(filters.Regex("^🔍 Find a chat partner$"), find_match))
app.add_handler(MessageHandler(filters.Regex("^(⭐ 50 Stars – 30 minutes|⭐ 90 Stars – 60 minutes|❌ End chat)$"), handle_paid_choice))
app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_messages))

if __name__ == "__main__":
    app.run_polling()
