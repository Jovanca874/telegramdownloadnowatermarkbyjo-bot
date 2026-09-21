import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import yt_dlp
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

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
        "Kirimkan link dari platform apa saja:\n"
        "• 🎬 **TikTok Video / Slideshow Foto** (Tanpa Watermark)\n"
        "• 📸 **Instagram Reels / Post**\n"
        "• 🎥 **YouTube Shorts / Video**\n\n"
        "Silakan kirimkan linknya sekarang!"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        await update.message.reply_text("⚠️ Mohon kirimkan link yang valid (harus diawali http:// atau https://)")
        return

    context.user_data['media_url'] = url

    # Cek apakah ini link foto/slideshow TikTok
    if "tiktok.com" in url and "/photo/" in url:
        keyboard = [[InlineKeyboardButton("📸 Download Slideshow Foto", callback_data="download_photos")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🔗 Link Slideshow TikTok diterima!\nPilih format untuk mengunduh foto:", reply_markup=reply_markup)
    else:
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

    # Ambil direct link menggunakan yt-dlp
    direct_link = None
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            direct_link = info.get('url')
    except Exception:
        pass

    # 1. DOWNLOAD FOTO / SLIDESHOW TIKTOK
    if choice == "download_photos":
        await query.edit_message_text("⏳ Sedang mengambil foto-foto dari TikTok...")
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            # Ambil daftar gambar/foto dari metadata yt-dlp
            formats = info.get('formats', [])
            image_urls = []
            
            # Cari format gambar yang tersedia
            if 'thumbnails' in info:
                image_urls = [t['url'] for t in info['thumbnails'] if 'url' in t]
            
            # Jika ada format gambar khusus di formats
            for f in formats:
                if f.get('ext') in ['jpg', 'jpeg', 'png', 'webp']:
                    image_urls.append(f['url'])

            # Filter duplikat
            image_urls = list(dict.fromkeys(image_urls))

            if not image_urls:
                # Alternatif: coba ekstrak langsung dari entries jika ada
                if 'entries' in info:
                    for entry in info['entries']:
                        if 'thumbnails' in entry:
                            image_urls.extend([t['url'] for t in entry['thumbnails'] if 'url' in t])

            if not image_urls:
                await query.edit_message_text("❌ Gagal menemukan foto pada link tersebut. Pastikan link publik.")
                return

            await query.edit_message_text(f"📤 Mengirim {len(image_urls)} foto ke Anda...")
            
            # Kirim foto sebagai album ke Telegram (maksimal 10 foto per album)
            media_group = [InputMediaPhoto(media=img_url) for img_url in image_urls[:10]]
            await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media_group)
            
        except Exception as e:
            logger.error(f"Error Photos: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Terjadi kesalahan saat mendownload foto: {e}")

    # 2. DOWNLOAD VIDEO
    elif choice == "download_video":
        await query.edit_message_text("⏳ Sedang memproses dan mendownload video...")
        output_filename = f"media_{user_id}.mp4"
        ydl_opts = {'format': 'best', 'outtmpl': output_filename, 'quiet': True, 'no_warnings': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            if not os.path.exists(output_filename):
                await query.edit_message_text("❌ Gagal mendownload video. Pastikan link aktif.")
                return

            await query.edit_message_text("📤 Mengirim video dan link unduhan ke Anda...")
            caption_text = "✅ Berhasil mendownload video tanpa watermark!"
            if direct_link:
                caption_text += f"\n\n🔗 **Direct Link:** [Klik Disini]({direct_link})"

            with open(output_filename, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=video_file,
                    caption=caption_text,
                    parse_mode="Markdown"
                )
            os.remove(output_filename)
        except Exception as e:
            logger.error(f"Error Video: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Terjadi kesalahan: {e}")
            if os.path.exists(output_filename):
                os.remove(output_filename)

    # 3. DOWNLOAD AUDIO (MP3)
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

            await query.edit_message_text("📤 Mengirim audio dan link unduhan ke Anda...")
            caption_text = "🎵 Berhasil mendownload audio (MP3)!"
            if direct_link:
                caption_text += f"\n\n🔗 **Direct Link:** [Klik Disini]({direct_link})"

            with open(audio_filename, 'rb') as audio_file:
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=audio_file,
                    caption=caption_text,
                    parse_mode="Markdown"
                )
            os.remove(audio_filename)
        except Exception as e:
            logger.error(f"Error Audio: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Terjadi kesalahan: {e}")
            if os.path.exists(audio_filename):
                os.remove(audio_filename)

def main():
    if not TOKEN:
        print("❌ Error: TELEGRAM_TOKEN belum diatur di file .env!")
        return
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_link))
    application.add_handler(CallbackQueryHandler(button_callback))
    print("🤖 Universal Downloader Bot (Video, Audio & Photos) sedang berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()