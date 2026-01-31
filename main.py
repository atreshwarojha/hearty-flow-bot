from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8335740705:AAFeYZinoZ3rN-_l1rW7y4DUsyWJzhvhcLI"

# In-memory storage
users = {}
waiting_males = []
waiting_females = []
active_chats = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["👦 Male", "👧 Female"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Hello 👋\n\nWelcome to Lonely Talks Bot 💙\n\nPlease select your gender:",
        reply_markup=reply_markup
    )

async def handle_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text not in ["👦 Male", "👧 Female"]:
        await update.message.reply_text("Please choose using buttons 🙂")
        return

    gender = "male" if "Male" in text else "female"

    users[user_id] = {
        "gender": gender,
        "status": "idle"
    }

    await update.message.reply_text(
        "✅ Gender saved.\n\nTap below to find a chat partner.",
        reply_markup=ReplyKeyboardMarkup(
            [["🔍 Find a chat partner"]],
            resize_keyboard=True
        )
    )

async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text("Please use /start first.")
        return

    gender = users[user_id]["gender"]

    if users[user_id]["status"] == "chatting":
        await update.message.reply_text("You are already in a chat.")
        return

    if gender == "male":
        if waiting_females:
            partner_id = waiting_females.pop(0)
            await start_chat(user_id, partner_id, context)
        else:
            waiting_males.append(user_id)
            users[user_id]["status"] = "waiting"
            await update.message.reply_text("⏳ Waiting for a female partner...")
    else:
        if waiting_males:
            partner_id = waiting_males.pop(0)
            await start_chat(partner_id, user_id, context)
        else:
            waiting_females.append(user_id)
            users[user_id]["status"] = "waiting"
            await update.message.reply_text("⏳ Waiting for a male partner...")

async def start_chat(user1, user2, context):
    users[user1]["status"] = "chatting"
    users[user2]["status"] = "chatting"

    active_chats[user1] = user2
    active_chats[user2] = user1

    await context.bot.send_message(
        chat_id=user1,
        text="💬 You are now connected!\nSay hi 👋"
    )
    await context.bot.send_message(
        chat_id=user2,
        text="💬 You are now connected!\nSay hi 👋"
    )

async def relay_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(chat_id=partner_id, text=text)

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("^(👦 Male|👧 Female)$"), handle_gender))
app.add_handler(MessageHandler(filters.Regex("^🔍 Find a chat partner$"), find_match))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_messages))

app.run_polling()
