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
group_games = {}

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
    group_id = update.message.chat.id
    response = requests.get(WORD_LIST_URL)
    words = [word.upper() for word in response.text.splitlines() if len(word) == WORD_LENGTH]
    target_word = random.choice(words)
    
    # Initialize game session for the group
    group_games[group_id] = {
        'target_word': target_word,
        'guessed_words': {},
        'remaining_attempts': MAX_ATTEMPTS,
    }
    
    await update.message.reply_text(
        f"New Wordle game started for the group! 🎯\n"
        f"Guess the {WORD_LENGTH}-letter word. The whole team has {MAX_ATTEMPTS} attempts."
    )

async def handle_guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_id = update.message.chat.id
    user_id = update.message.from_user.id
    guess = update.message.text.upper().strip()
    
    if group_id not in group_games:
        await update.message.reply_text("Send /play to start a new game first!")
        return
    
    game = group_games[group_id]
    
    if len(guess) != WORD_LENGTH:
        await update.message.reply_text(f"Please enter a {WORD_LENGTH}-letter word.")
        return
    if not guess.isalpha():
        await update.message.reply_text("Please enter letters only.")
        return
    
    if user_id in game['guessed_words']:
        await update.message.reply_text("You've already guessed! Wait for your turn.")
        return
    
    # Record the guess and check remaining attempts
    game['guessed_words'][user_id] = guess
    game['remaining_attempts'] -= 1
    
    feedback = generate_feedback(guess, game['target_word'])
    remaining_attempts = game['remaining_attempts']
    
    response = f"Player {update.message.from_user.first_name}'s guess: {feedback}\n"
    if guess == game['target_word']:
        response += "\n🎉 Congratulations! The word was guessed! 🎉"
        del group_games[group_id]
    elif remaining_attempts == 0:
        response += f"\nGame Over! The word was: {game['target_word']}"
        del group_games[group_id]
    else:
        response += f"\nRemaining attempts: {remaining_attempts}"

    await update.message.reply_text(response)

def generate_feedback(guess: str, target: str) -> str:
    feedback = []
    target_letters = list(target)
    
    # First pass for correct letters
    for g, t in zip(guess, target):
        if g == t:
            feedback.append("🟩")
            target_letters.remove(g)
        else:
            feedback.append(" ")
    
    # Second pass for misplaced letters
    for i, g in enumerate(guess):
        if feedback[i] == " ":
            if g in target_letters:
                feedback[i] = "🟨"
                target_letters.remove(g)
            else:
                feedback[i] = "⬛"
    
    return "".join(feedback)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Error occurred: {context.error}")
    if isinstance(context.error, telegram.error.Conflict):
        print("Another bot instance is running! Terminating...")

def main() -> None:
    # Create application instance
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", new_game))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start polling
    application.run_polling()

if __name__ == "__main__":
    main()
