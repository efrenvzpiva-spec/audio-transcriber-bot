import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import logging

load_dotenv()

# Configuracion de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_TRANSCRIBE = os.getenv("OPENAI_MODEL_TRANSCRIBE", "whisper-1")
OPENAI_MODEL_SUMMARY = os.getenv("OPENAI_MODEL_SUMMARY", "gpt-4o-mini")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY no configurada en .env")

client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI(
    title="Audio Transcriber API",
    description="API para transcribir audios y generar resumenes usando OpenAI",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextoIn(BaseModel):
    texto: str


class TranscripcionResponse(BaseModel):
    transcripcion: str
    resumen: str


class ResumenResponse(BaseModel):
    resumen: str


def transcribe_audio_bytes(data: bytes, extension: str = ".ogg") -> str:
    """Transcribe bytes de audio usando OpenAI Whisper."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model=OPENAI_MODEL_TRANSCRIBE,
                file=f,
                language="es"
            )
        return result.text.strip()
    except Exception as e:
        logger.error(f"Error transcribiendo audio: {e}")
        raise HTTPException(status_code=500, detail=f"Error en transcripcion: {str(e)}")
    finally:
        os.unlink(tmp_path)


def generate_summary(text: str) -> str:
    """Genera un resumen usando GPT."""
    if not text or len(text.strip()) < 10:
        return "El texto es demasiado corto para generar un resumen."

    prompt = (
        "Eres un asistente experto en resumir contenido en espanol.\n"
        "Genera un resumen claro y conciso del siguiente texto.\n"
        "Incluye:\n"
        "- Idea principal\n"
        "- Puntos clave (maximo 5 vietas)\n"
        "- Conclusion breve\n\n"
        f"Texto:\n{text}"
    )

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL_SUMMARY,
            messages=[
                {"role": "system", "content": "Eres un asistente que resume textos de forma clara y concisa en espanol."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generando resumen: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando resumen: {str(e)}")


@app.get("/")
async def root():
    return {"message": "Audio Transcriber API funcionando", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "ok", "models": {"transcribe": OPENAI_MODEL_TRANSCRIBE, "summary": OPENAI_MODEL_SUMMARY}}


@app.post("/transcribir_resumir_audio", response_model=TranscripcionResponse)
async def transcribir_resumir_audio(file: UploadFile = File(...)):
    """
    Recibe un archivo de audio, lo transcribe y genera un resumen.
    Formatos soportados: ogg, mp3, mp4, wav, m4a, webm
    """
    logger.info(f"Recibiendo audio: {file.filename}, tipo: {file.content_type}")

    # Determinar extension
    extension = ".ogg"
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in [".ogg", ".mp3", ".mp4", ".wav", ".m4a", ".webm", ".oga"]:
            extension = ext

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Archivo de audio vacio")

    logger.info(f"Audio recibido: {len(data)} bytes")

    transcripcion = transcribe_audio_bytes(data, extension)
    logger.info(f"Transcripcion completada: {len(transcripcion)} caracteres")

    resumen = generate_summary(transcripcion)
    logger.info("Resumen generado")

    return TranscripcionResponse(transcripcion=transcripcion, resumen=resumen)


@app.post("/transcribir_audio")
async def solo_transcribir(file: UploadFile = File(...)):
    """
    Solo transcribe el audio sin generar resumen.
    """
    extension = ".ogg"
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in [".ogg", ".mp3", ".mp4", ".wav", ".m4a", ".webm"]:
            extension = ext

    data = await file.read()
    transcripcion = transcribe_audio_bytes(data, extension)
    return {"transcripcion": transcripcion}


@app.post("/resumen_texto", response_model=ResumenResponse)
async def resumen_texto(body: TextoIn):
    """
    Genera un resumen de un texto dado.
    """
    if not body.texto or len(body.texto.strip()) < 5:
        raise HTTPException(status_code=400, detail="Texto muy corto o vacio")

    resumen = generate_summary(body.texto)
    return ResumenResponse(resumen=resumen)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
