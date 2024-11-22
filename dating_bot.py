import asyncio
import json
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, ConversationHandler, filters
import random
import datetime
import nest_asyncio
import logging

# Apply nest_asyncio to avoid event loop issues
nest_asyncio.apply()

# Replace this with your actual bot token
TOKEN = '7763648149:AAFRx7q_IC1-J5MKIvZokurV1sTzT5jOUIs'

# Store user data in memory (in real applications, use a database)
user_data = {}

# Path to the JSON file where user data will be saved
USER_DATA_FILE = 'user_data.json'

# Conversation states
ASK_NAME, ASK_AGE, ASK_GENDER, ASK_USERNAME = range(4)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load user data from the JSON file
def load_user_data():
    global user_data
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            user_data = json.load(f)

# Save user data to the JSON file
def save_user_data():
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(user_data, f)

# Function to start the bot and give a welcome message
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Welcome to the Sri Lankan Dating Bot! 🥰\n"
        "To register, please type /register to start the process.\n"
        "You have 5 free attempts per day to match with others. 🎉"
    )

# Start the registration process
async def register_start(update: Update, context: CallbackContext) -> int:
    user_id = update.message.chat.id
    if user_id in user_data:
        await update.message.reply_text("You are already registered! Use /match to find a match. 😉")
        return ConversationHandler.END
    await update.message.reply_text("What is your name? 😄")
    return ASK_NAME

# Ask for the user's name
async def ask_name(update: Update, context: CallbackContext) -> int:
    user_id = update.message.chat.id
    user_data[user_id] = {"name": update.message.text, "age": 0, "gender": "", "username": "", "attempts": 5, "paid": False}
    save_user_data()  # Save after updating
    await update.message.reply_text("What is your age? 🎂")
    return ASK_AGE

# Ask for the user's age
async def ask_age(update: Update, context: CallbackContext) -> int:
    user_id = update.message.chat.id
    try:
        age = int(update.message.text)
        if age < 18:
            del user_data[user_id]
            save_user_data()  # Save after deleting
            await update.message.reply_text("Sorry, you must be 18 or older to use this bot. 😢 Registration canceled.")
            return ConversationHandler.END
        user_data[user_id]["age"] = age
        save_user_data()  # Save after updating
        await update.message.reply_text(
            "What is your gender? (Please type 'Male' or 'Female') 💁‍♂️💁‍♀️",
            reply_markup=ReplyKeyboardMarkup([["Male", "Female"]], one_time_keyboard=True)
        )
        return ASK_GENDER
    except ValueError:
        await update.message.reply_text("Invalid age. Please provide a valid number for your age. 🙄")
        return ASK_AGE

# Ask for the user's gender
async def ask_gender(update: Update, context: CallbackContext) -> int:
    user_id = update.message.chat.id
    gender = update.message.text
    if gender not in ["Male", "Female"]:
        await update.message.reply_text("Invalid gender. Please type 'Male' or 'Female'. 🙅‍♂️🙅‍♀️")
        return ASK_GENDER
    user_data[user_id]["gender"] = gender
    save_user_data()  # Save after updating
    await update.message.reply_text("Please provide your Telegram username (without @): 💬")
    return ASK_USERNAME

# Ask for the user's Telegram username
async def ask_username(update: Update, context: CallbackContext) -> int:
    user_id = update.message.chat.id
    username = update.message.text
    if not username or any(u["username"] == username for u in user_data.values()):
        await update.message.reply_text("Invalid or duplicate username. Please try again. 😅")
        return ASK_USERNAME
    user_data[user_id]["username"] = username
    save_user_data()  # Save after updating
    await update.message.reply_text(
        f"Registration complete! 🎉 Welcome {user_data[user_id]['name']}.\n"
        f"You have 5 free matching attempts today. 😍",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "You can now use the /match command to find a match! ❤️\n"
        "Type /match to get started. 🌟"
    )
    return ConversationHandler.END

# Handle conversation cancellation
async def cancel(update: Update, context: CallbackContext) -> int:
    user_id = update.message.chat.id
    if user_id in user_data:
        del user_data[user_id]
        save_user_data()  # Save after deleting
    await update.message.reply_text("Registration canceled. 😞", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Matching function to match users randomly
async def match(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat.id
    if user_id not in user_data:
        await update.message.reply_text("Please register first using /register. 📝")
        return

    user_info = user_data[user_id]
    if user_info["attempts"] <= 0:
        await update.message.reply_text("You have used all your free attempts for today. 😔 Please come back tomorrow. 🌙")
        return

    eligible_users = [uid for uid in user_data if uid != user_id and user_data[uid].get("username")]
    if not eligible_users:
        await update.message.reply_text("No other users available to match with. Please try again later. 🕑")
        return

    # Match randomly
    matched_user_id = random.choice(eligible_users)
    matched_user_info = user_data[matched_user_id]

    # Inline button with deep link to the matched user's profile
    keyboard = [
        [InlineKeyboardButton(
            text=f"Chat with {matched_user_info['name']} 💌",
            url=f"https://t.me/{matched_user_info['username']}"
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Congratulations! 🎉 You've been matched with {matched_user_info['name']}.\n"
        f"Click below to start chatting with them. 💬",
        reply_markup=reply_markup
    )

    # Decrement the user's remaining attempts
    user_info["attempts"] -= 1
    save_user_data()  # Save after updating attempts
    await update.message.reply_text(f"You have {user_info['attempts']} attempts remaining today. ⏳")

# Reset daily attempts
async def reset_attempts(context: CallbackContext) -> None:
    for user_id in user_data:
        user_data[user_id]["attempts"] = 5
    save_user_data()  # Save after resetting attempts

# Main function to set up and run the bot
async def main():
    load_user_data()  # Load user data when the bot starts
    application = Application.builder().token(TOKEN).build()

    # Define conversation handler for registration
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            ASK_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_gender)],
            ASK_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_username)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("match", match))

    # Reset daily attempts at midnight
    application.job_queue.run_daily(reset_attempts, time=datetime.time(hour=0, minute=0, second=0))

    # Add error handler
    async def error_handler(update: Update, context: CallbackContext) -> None:
        logger.error(msg="Exception while handling an update:", exc_info=context.error)

    application.add_error_handler(error_handler)

    await application.run_polling()

# Run the bot
asyncio.run(main())