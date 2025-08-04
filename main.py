import os, re, io, sqlite3
from collections import Counter
from pathlib import Path
from contextlib import closing
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          ContextTypes, filters)
import matplotlib.pyplot as plt
from PIL import Image

TOKEN       = os.environ["TOKEN"]
PUBLIC_URL  = os.getenv("PUBLIC_URL", "")  # חובה להגדיר בדשבורד Render
DB_PATH     = Path("data/polls.db")          # יישמר על הדיסק המתמשך

TICKER_RE   = re.compile(r"\b[A-Z]{1,5}(?:\.[A-Z])?\b")  # BRK.B וכו׳

# --- storage --------------------------------------------------------------
DB_PATH.parent.mkdir(exist_ok=True)
with closing(sqlite3.connect(DB_PATH)) as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            user_id   INTEGER,
            ticker    TEXT,
            PRIMARY KEY (user_id, ticker)
        )
    """)
    conn.commit()

def save_votes(user_id: int, tickers: list[str]):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        for t in tickers:
            conn.execute("INSERT OR IGNORE INTO votes VALUES (?,?)", (user_id, t))
        conn.commit()

def reset_votes():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("DELETE FROM votes")
        conn.commit()

def load_distribution() -> Counter:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        rows = conn.execute("SELECT ticker, COUNT(*) FROM votes GROUP BY ticker").fetchall()
    return Counter({t: c for t, c in rows})

# --- bot logic ------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me any message containing ticker symbols (e.g. AAPL TSLA).\n" \
        "I'll record the votes and show the pie chart.\n" \
        "Use /summary to see current results, /clear to reset.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Send /summary", callback_data="summary")]])
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper()
    tickers = list(dict.fromkeys(TICKER_RE.findall(text)))  # unique order‑preserving
    if not tickers:
        return
    save_votes(update.effective_user.id, tickers)
    await send_pie(update, context)

async def send_pie(update_or_chat, context):
    dist = load_distribution()
    if not dist:
        return
    labels, sizes = zip(*dist.most_common())
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct="%1.0f%%", startangle=140)
    ax.axis('equal')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    if hasattr(update_or_chat, 'message'):
        chat = update_or_chat.message.chat_id
    else:
        chat = update_or_chat.chat_id
    await context.bot.send_photo(chat_id=chat, photo=buf,
                                 caption="/summary – current vote share")

async def summary_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_pie(update, context)

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_votes()
    await update.message.reply_text("✅ Votes cleared.")

# --- app init -------------------------------------------------------------
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("summary", summary_cmd))
app.add_handler(CommandHandler("clear", clear_cmd))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

if __name__ == "__main__":
    PORT = int(os.getenv("PORT", "10000"))
    if PUBLIC_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"{PUBLIC_URL}/{TOKEN}",
            drop_pending_updates=True,
            path=f"/{TOKEN}"
        )
    else:  # Fallback to polling (local dev)
        app.run_polling()