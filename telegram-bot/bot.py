import os
import logging
import tempfile
import httpx
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

load_dotenv()

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuracion
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN no configurado en .env")

MAX_MESSAGE_LENGTH = 4096


def split_message(text: str) -> list[str]:
    """Divide mensajes largos respetando el limite de Telegram."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]
    parts = []
    while len(text) > MAX_MESSAGE_LENGTH:
        split_at = text.rfind('\n', 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = MAX_MESSAGE_LENGTH
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
    if text:
        parts.append(text)
    return parts


async def send_long_message(update: Update, text: str):
    """Envia un mensaje dividido si es muy largo."""
    parts = split_message(text)
    for part in parts:
        await update.message.reply_text(part)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola! Soy tu bot de transcripcion de audio.\n\n"
        "Puedo hacer lo siguiente:\n"
        "- Enviarme una nota de voz o archivo de audio y lo transcribo + resumo\n"
        "- /resumen <texto> - Resumir cualquier texto\n"
        "- /ayuda - Ver todos los comandos\n\n"
        "Prueba enviandome un audio ahora mismo!"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponibles:\n\n"
        "/start - Bienvenida\n"
        "/ayuda - Esta ayuda\n"
        "/resumen <texto> - Resumir un texto\n\n"
        "Acciones:\n"
        "- Envia una nota de voz -> Transcripcion + Resumen\n"
        "- Envia un archivo de audio -> Transcripcion + Resumen"
    )


async def resumen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /resumen <texto>"""
    if not context.args:
        await update.message.reply_text(
            "Uso: /resumen <texto a resumir>\n\n"
            "Ejemplo: /resumen El mercado de criptomonedas sube un 5% hoy..."
        )
        return

    texto = ' '.join(context.args)
    await update.message.reply_text("Generando resumen...")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{BACKEND_URL}/resumen_texto",
                json={"texto": texto}
            )
            resp.raise_for_status()
            data = resp.json()

        resumen = data.get("resumen", "No se pudo generar el resumen.")
        await send_long_message(update, f"Resumen:\n\n{resumen}")

    except httpx.HTTPError as e:
        logger.error(f"Error HTTP al resumir: {e}")
        await update.message.reply_text("Error al conectar con el servidor. Intenta de nuevo.")
    except Exception as e:
        logger.error(f"Error al resumir: {e}")
        await update.message.reply_text("Error al generar el resumen.")


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja audios y notas de voz."""
    message = update.message

    # Detectar tipo de audio
    audio_file = None
    file_extension = ".ogg"

    if message.voice:
        audio_file = message.voice
        file_extension = ".ogg"
    elif message.audio:
        audio_file = message.audio
        name = audio_file.file_name or ""
        ext = os.path.splitext(name)[1].lower()
        file_extension = ext if ext in [".mp3", ".wav", ".m4a", ".ogg", ".mp4"] else ".mp3"
    elif message.document:
        doc = message.document
        mime = doc.mime_type or ""
        if not mime.startswith("audio/"):
            await update.message.reply_text("Solo acepto archivos de audio.")
            return
        audio_file = doc
        ext = os.path.splitext(doc.file_name or "")[1].lower()
        file_extension = ext if ext else ".ogg"

    if not audio_file:
        return

    await update.message.reply_text("Procesando audio, un momento...")

    try:
        # Descargar audio
        tg_file = await context.bot.get_file(audio_file.file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            tmp_path = tmp.name

        await tg_file.download_to_drive(tmp_path)
        logger.info(f"Audio descargado: {tmp_path}")

        # Enviar al backend
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{BACKEND_URL}/transcribir_resumir_audio",
                files={"file": (f"audio{file_extension}", audio_bytes, "audio/ogg")}
            )
            resp.raise_for_status()
            data = resp.json()

        os.unlink(tmp_path)

        transcripcion = data.get("transcripcion", "")
        resumen = data.get("resumen", "")

        if not transcripcion:
            await update.message.reply_text("No se pudo transcribir el audio.")
            return

        resultado = (
            f"Transcripcion:\n\n{transcripcion}\n\n"
            f"{'=' * 30}\n\n"
            f"Resumen:\n\n{resumen}"
        )
        await send_long_message(update, resultado)

    except httpx.HTTPError as e:
        logger.error(f"Error HTTP: {e}")
        await update.message.reply_text("Error al procesar el audio. Intenta de nuevo.")
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        await update.message.reply_text(f"Error inesperado: {str(e)}")


async def post_init(application: Application):
    """Configurar comandos del bot en Telegram."""
    await application.bot.set_my_commands([
        BotCommand("start", "Iniciar el bot"),
        BotCommand("ayuda", "Ver comandos disponibles"),
        BotCommand("resumen", "Resumir un texto: /resumen <texto>"),
    ])


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ayuda", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("resumen", resumen_command))

    # Audios
    app.add_handler(MessageHandler(filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.Document.AUDIO, handle_audio))

    logger.info("Bot de Telegram iniciado...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
