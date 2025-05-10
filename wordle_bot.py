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

# Dictionary to store ongoing games per chat (group or private)
group_games = {}

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎉 Welcome to Wordle Bot – Group Edition!\n\n"
        "🟩🟨⬛ How to play:\n"
        "1. Type /play to start a game\n"
        "2. Guess a 5-letter word\n"
        "3. Work together as a team – 6 total guesses\n\n"
        "Correct = 🟩, Wrong Position = 🟨, Not in Word = ⬛\n"
        "Start guessing! 🚀"
    )

async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id

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

    group_games[chat_id] = {
        'target_word': target_word,
        'attempts': [],
        'remaining_attempts': MAX_ATTEMPTS
    }

    await update.message.reply_text(
        f"🎯 A new Wordle game has started for this group!\n"
        f"Guess a {WORD_LENGTH}-letter word.\nYou have {MAX_ATTEMPTS} total attempts as a team. Good luck!"
    )

async def handle_guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    guess = update.message.text.upper().strip()
    user_name = update.message.from_user.first_name

    if chat_id not in group_games:
        await update.message.reply_text("Send /play to start a new game first!")
        return

    if len(guess) != WORD_LENGTH:
        await update.message.reply_text(f"Please enter a {WORD_LENGTH}-letter word.")
        return
    if not guess.isalpha():
        await update.message.reply_text("Please enter letters only.")
        return

    game = group_games[chat_id]
    game['attempts'].append((user_name, guess))
    game['remaining_attempts'] -= 1

    feedback = generate_feedback(guess, game['target_word'])
    attempts_left = game['remaining_attempts']

    response = (
        f"🧠 {user_name} guessed: {guess}\n"
        f"Attempt {len(game['attempts'])}/{MAX_ATTEMPTS}:\n"
        f"{feedback}\n"
    )

    if guess == game['target_word']:
        response += f"\n🎉 {user_name} found the word! You all win! 🏆"
        del group_games[chat_id]
    elif attempts_left == 0:
        response += f"\n❌ Game Over! The word was: {game['target_word']}"
        del group_games[chat_id]
    else:
        response += f"Remaining attempts: {attempts_left}"

    await update.message.reply_text(response)

def generate_feedback(guess: str, target: str) -> str:
    feedback = ["⬛"] * len(guess)
    target_chars = list(target)

    # First pass: correct letter and position
    for i in range(len(guess)):
        if guess[i] == target[i]:
            feedback[i] = "🟩"
            target_chars[i] = None  # avoid reuse

    # Second pass: correct letter, wrong position
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
