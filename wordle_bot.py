import random
import os
import logging
import telegram
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Configuration
TOKEN = os.environ["TOKEN"]
WORD_LIST_URL = "https://raw.githubusercontent.com/tabatkins/wordle-list/main/words"
WORD_LENGTH = 5
MAX_ATTEMPTS = 6

# Default fallback word list (must be 5-letter words!)
DEFAULT_WORDS = ["APPLE", "BRICK", "CRANE", "DRIVE", "FRUIT", "PLANT", "SHINE", "TRUCK", "VIRUS", "WATER"]

# Dictionary to store ongoing games per user
user_games = {}

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to Wordle Bot! 🌟\n\n"
        "How to play:\n"
        "1. Send /play to start a new game\n"
        "2. Guess a 5-letter word\n"
        "3. Get feedback using emojis:\n"
        "   🟩 Correct letter & position\n"
        "   🟨 Correct letter, wrong position\n"
        "   ⬛ Letter not in word\n"
        f"You have {MAX_ATTEMPTS} attempts!\n"
        "Good luck! 🍀"
    )

async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    try:
        response = requests.get(WORD_LIST_URL)
        if response.status_code == 200:
            words = [word.upper() for word in response.text.splitlines() if len(word) == WORD_LENGTH]
        else:
            logging.warning("Word list URL returned non-200 status.")
            words = []
    except Exception as e:
        logging.error(f"Failed to fetch word list: {e}")
        words = []

    if not words:
        logging.info("Using fallback word list.")
        words = DEFAULT_WORDS

    target_word = random.choice(words)

    user_games[user_id] = {
        'target_word': target_word,
        'attempts': [],
        'remaining_attempts': MAX_ATTEMPTS
    }

    await update.message.reply_text(
        f"New Wordle game started! 🎯\n"
        f"Guess a {WORD_LENGTH}-letter word. You have {MAX_ATTEMPTS} attempts."
    )

async def handle_guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    guess = update.message.text.upper().strip()

    if user_id not in user_games:
        await update.message.reply_text("Send /play to start a new game first!")
        return

    if len(guess) != WORD_LENGTH:
        await update.message.reply_text(f"Please enter a {WORD_LENGTH}-letter word.")
        return
    if not guess.isalpha():
        await update.message.reply_text("Please enter letters only.")
        return

    game = user_games[user_id]
    game['attempts'].append(guess)
    game['remaining_attempts'] -= 1

    feedback = generate_feedback(guess, game['target_word'])
    attempts_left = game['remaining_attempts']

    response = f"Attempt {len(game['attempts'])}/{MAX_ATTEMPTS}:\n{feedback}\n"

    if guess == game['target_word']:
        response += "\n🎉 Congratulations! You won! 🎉"
        del user_games[user_id]
    elif attempts_left == 0:
        response += f"\n❌ Game Over! The word was: {game['target_word']}"
        del user_games[user_id]
    else:
        response += f"\nRemaining attempts: {attempts_left}"

    await update.message.reply_text(response)

def generate_feedback(guess: str, target: str) -> str:
    feedback = ["⬛"] * len(guess)
    target_chars = list(target)

    # First pass: correct position
    for i in range(len(guess)):
        if guess[i] == target[i]:
            feedback[i] = "🟩"
            target_chars[i] = None  # prevent reuse

    # Second pass: wrong position
    for i in range(len(guess)):
        if feedback[i] == "🟩":
            continue
        if guess[i] in target_chars:
            feedback[i] = "🟨"
            target_chars[target_chars.index(guess[i])] = None

    return "".join(feedback)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Exception while handling an update:", exc_info=context.error)

def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", new_game))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess))
    application.add_error_handler(error_handler)

    logging.info("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
