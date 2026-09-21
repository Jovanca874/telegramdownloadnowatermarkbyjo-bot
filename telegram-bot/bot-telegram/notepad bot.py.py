import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import yt_dlp
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("8863981826:AAEFJdaKWYioqCWpWeRF2SfdhcA5NmVhAt0")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_message = (
        f"Halo {user_name}! 👋\n\n"
        "Saya adalah **Universal Media Downloader Bot** (Unlimited! 🚀)\n\n"
        "Kirimkan link video dari platform apa saja:\n"
        "• 🎵 **TikTok** (Tanpa Watermark & Username)\n"
        "• 📸 **Instagram Reels / Post**\n"
        "• 🎬 **YouTube Shorts / Video**\n"
        "• 📘 **Facebook Reels / Video**\n"
        "• 🐦 **Twitter / X**\n\n"
        "Silakan kirimkan linknya sekarang."
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        await update.message.reply_text("⚠️ Mohon kirimkan link yang valid (harus diawali http:// atau https://)")
        return

    context.user_data['media_url'] = url
    keyboard = [
        [
            InlineKeyboardButton("🎬 Download Video (MP4)", callback_data="download_video"),
            InlineKeyboardButton("🎵 Download Audio (MP3)", callback_data="download_audio")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔗 Link berhasil diterima!\nPilih format yang ingin Anda unduh:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = context.user_data.get('media_url')
    if not url:
        await query.edit_message_text("❌ Sesi kedaluwarsa atau link tidak ditemukan. Silakan kirim ulang link Anda.")
        return

    choice = query.data
    user_id = update.effective_user.id

    if choice == "download_video":
        await query.edit_message_text("⏳ Sedang memproses dan mendownload video...")
        output_filename = f"media_{user_id}.mp4"
        ydl_opts = {'format': 'best', 'outtmpl': output_filename, 'quiet': True, 'no_warnings': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            if not os.path.exists(output_filename):
                await query.edit_message_text("❌ Gagal mendownload video. Pastikan link aktif.")
                return
            await query.edit_message_text("📤 Mengirim video ke Anda...")
            with open(output_filename, 'rb') as video_file:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=video_file, caption="✅ Berhasil mendownload video!")
            os.remove(output_filename)
        except Exception as e:
            logger.error(f"Error Video: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Terjadi kesalahan: {e}")
            if os.path.exists(output_filename):
                os.remove(output_filename)

    elif choice == "download_audio":
        await query.edit_message_text("⏳ Sedang mengekstrak audio (MP3)...")
        output_tmpl = f"media_{user_id}.%(ext)s"
        audio_filename = f"media_{user_id}.mp3"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_tmpl,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'quiet': True,
            'no_warnings': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            if not os.path.exists(audio_filename):
                await query.edit_message_text("❌ Gagal mengekstrak audio.")
                return
            await query.edit_message_text("📤 Mengirim audio ke Anda...")
            with open(audio_filename, 'rb') as audio_file:
                await context.bot.send_audio(chat_id=update.effective_chat.id, audio=audio_file, caption="🎵 Berhasil mendownload audio (MP3)!")
            os.remove(audio_filename)
        except Exception as e:
            logger.error(f"Error Audio: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Terjadi kesalahan: {e}")
            if os.path.exists(audio_filename):
                os.remove(audio_filename)

def main():
    if not TOKEN:
        print("❌ Error: 8863981826:AAEFJdaKWYioqCWpWeRF2SfdhcA5NmVhAt0 belum diatur di file .env!")
        return
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_link))
    application.add_handler(CallbackQueryHandler(button_callback))
    print("🤖 Universal Downloader Bot (All Platforms, Unlimited) sedang berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()
