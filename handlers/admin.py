import os
from telegram import Update
from telegram.ext import ContextTypes
from services.formatter import transfer_caption, news_caption, star_player_caption, with_footer
from services.media import get_transfer_photo, get_news_photo

def is_admin(user_id):
    ids = {
        int(x.strip())
        for x in os.getenv("ADMIN_IDS", "").split(",")
        if x.strip().isdigit()
    }
    return user_id in ids

async def post_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu buyruq faqat adminlar uchun.")
        return

    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Foydalanish: /post Sizning matningiz")
        return

    channel = os.getenv("CHANNEL_ID")
    try:
        await context.bot.send_message(chat_id=channel, text=with_footer(text), parse_mode="HTML")
        await update.message.reply_text("✅ Kanalga yuborildi.")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")

async def handle_admin_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return

    channel = os.getenv("CHANNEL_ID")
    raw_caption = update.message.caption or ""

    # Yulduz futbolchi posti: caption "⭐ Ism | Klub | Ma'lumot" formatida bo'lsa,
    # chiroyli qilib formatlanadi. Aks holda caption o'zgarishsiz yuboriladi.
    caption = raw_caption
    if raw_caption.strip().startswith("⭐"):
        parts = [p.strip() for p in raw_caption.lstrip("⭐").split("|")]
        name = parts[0] if len(parts) > 0 else ""
        club = parts[1] if len(parts) > 1 else ""
        info = parts[2] if len(parts) > 2 else ""
        if name:
            caption = star_player_caption(name, club, info)

    try:
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=channel,
                photo=update.message.photo[-1].file_id,
                caption=caption[:1024] if caption else None,
                parse_mode="HTML"
            )
        elif update.message.video:
            await context.bot.send_video(
                chat_id=channel,
                video=update.message.video.file_id,
                caption=caption[:1024] if caption else None,
                parse_mode="HTML"
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=channel,
                document=update.message.document.file_id,
                caption=caption[:1024] if caption else None,
                parse_mode="HTML"
            )

        await update.message.reply_text("✅ Media kanalga yuborildi.")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

def _split_args(update: Update):
    raw = update.message.text.split(" ", 1)
    if len(raw) < 2:
        return []
    return [p.strip() for p in raw[1].split("|")]

async def transfer_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu buyruq faqat adminlar uchun.")
        return

    parts = _split_args(update)
    if len(parts) < 3:
        await update.message.reply_text(
            "Foydalanish:\n"
            "/transfer O'yinchi | Eski klub | Yangi klub | Tafsilotlar | Manba\n\n"
            "Tafsilotlar va Manba ixtiyoriy.\n"
            "Masalan:\n"
            "/transfer Lionel Messi | PSG | Inter Miami | 2 yillik shartnoma | Fabrizio Romano"
        )
        return

    player, old_club, new_club = parts[0], parts[1], parts[2]
    details = parts[3] if len(parts) > 3 else ""
    source = parts[4] if len(parts) > 4 else None

    text = transfer_caption(player, old_club, new_club, details, source)

    channel = os.getenv("CHANNEL_ID")
    try:
        image_path, image_source = get_transfer_photo(player, new_club)
        if image_path:
            caption = text
            # Keep attribution concise and inside Telegram's caption limit.
            caption += "\n\n📷 Foto: Wikimedia Commons"
            with open(image_path, "rb") as photo:
                await context.bot.send_photo(chat_id=channel, photo=photo, caption=caption[:1024], parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id=channel, text=text, parse_mode="HTML")
        await update.message.reply_text("✅ Transfer xabari kanalga yuborildi.")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")

async def news_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bu buyruq faqat adminlar uchun.")
        return

    parts = _split_args(update)
    if len(parts) < 2:
        await update.message.reply_text(
            "Foydalanish:\n"
            "/xabar Sarlavha | Matn | Manba\n\n"
            "Manba ixtiyoriy.\n"
            "Masalan:\n"
            "/xabar Yangi murabbiy tayinlandi | Klub rasman yangi bosh murabbiyni e'lon qildi. | Klub matbuot xizmati"
        )
        return

    title, body = parts[0], parts[1]
    source = parts[2] if len(parts) > 2 else None

    text = news_caption(title, body, source)

    channel = os.getenv("CHANNEL_ID")
    try:
        image_path, image_source = get_news_photo(title, body)
        if image_path:
            caption = text + "\n\n📷 Foto: Wikimedia Commons"
            with open(image_path, "rb") as photo:
                await context.bot.send_photo(chat_id=channel, photo=photo, caption=caption[:1024], parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id=channel, text=text, parse_mode="HTML")
        await update.message.reply_text("✅ Yangilik kanalga yuborildi.")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")
