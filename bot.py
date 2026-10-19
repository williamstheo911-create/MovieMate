import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)

# 1. Fetch credentials from Railway environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 2. TMDB search function
def search_tmdb(movie_name: str):
    url = f"https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": movie_name,
        "language": "en-US"
    }
    response = requests.get(url, params=params).json()
    results = response.get("results", [])
    if not results:
        return None
    return results[0]

# 3. YouTube trailer search function
def search_youtube_trailer(movie_title: str):
    try:
        youtube = build("youtube", "v3", developerKey=GOOGLE_API_KEY)
        query = f"{movie_title} official trailer"
        request = youtube.search().list(
            q=query,
            part="snippet",
            maxResults=1,
            type="video"
        )
        response = request.execute()
        items = response.get("items", [])
        if items:
            video_id = items[0]["id"]["videoId"]
            return f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        logging.error(f"YouTube search error: {e}")
    return None

# 4. Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome! Just send me the name of any movie, and I'll find its synopsis, poster, and trailer!"
    )

async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movie_name = update.message.text.strip()
    await update.message.reply_text(f"🔍 Searching for \"{movie_name}\"...")

    # Fetch TMDB data
    movie = search_tmdb(movie_name)
    if not movie:
        await update.message.reply_text("❌ Movie not found on TMDB. Try another title!")
        return

    title = movie.get("title", movie_name)
    release_date = movie.get("release_date", "N/A")
    year = release_date.split("-")[0] if release_date != "N/A" else "N/A"
    overview = movie.get("overview", "No description available.")
    rating = movie.get("vote_average", "N/A")
    poster_path = movie.get("poster_path")

    # Fetch YouTube trailer
    trailer_url = search_youtube_trailer(title)

    caption = (
        f"🎬 *{title}* ({year})\n"
        f"⭐ Rating: {rating}/10\n\n"
        f"{overview[:700]}{'...' if len(overview) > 700 else ''}"
    )

    # Inline button for trailer
    keyboard = []
    if trailer_url:
        keyboard.append([InlineKeyboardButton("🍿 Watch Trailer on YouTube", url=trailer_url)])
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    # Send response
    if poster_path:
        image_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
        await update.message.reply_photo(
            photo=image_url,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text=caption,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
    
    print("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
