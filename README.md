# 🎙️ Audio Transcriber Bot

Bot para **transcribir audios a texto** y generar **resúmenes automáticos** usando OpenAI Whisper y GPT.

Compatible con **WhatsApp** (via Baileys) y **Telegram**.

---

## 📁 Estructura del Proyecto

```
audio-transcriber-bot/
├── backend/              # API Python (FastAPI)
│   ├── main.py           # Servidor principal con endpoints
│   ├── requirements.txt  # Dependencias Python
│   └── .env.example      # Variables de entorno
├── whatsapp-bot/         # Bot WhatsApp con Baileys (Node.js)
│   ├── index.js          # Bot principal
│   ├── package.json      # Dependencias Node
│   └── .env.example
├── telegram-bot/         # Bot Telegram (Python)
│   ├── bot.py            # Bot principal
│   ├── requirements.txt
│   └── .env.example
└── README.md
```

---

## 🚀 Características

- 🎧 Transcripción de notas de voz y audios
- 📝 Resumen automático en español
- 📱 Compatible con WhatsApp y Telegram
- ⚡ Backend compartido (FastAPI)
- 🔒 Variables de entorno seguras
- 🌐 Listo para Railway / Render / VPS

---

## ⚙️ Requisitos

- Python 3.10+
- Node.js 18+
- Cuenta OpenAI con API Key
- Token de Telegram Bot (via @BotFather)
- Número de WhatsApp activo

---

## 🔧 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/efrenvzpiva-spec/audio-transcriber-bot.git
cd audio-transcriber-bot
```

### 2. Configurar el Backend

```bash
cd backend
cp .env.example .env
# Edita .env con tu OPENAI_API_KEY
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Configurar el Bot de Telegram

```bash
cd telegram-bot
cp .env.example .env
# Edita .env con tu TELEGRAM_BOT_TOKEN y OPENAI_API_KEY
pip install -r requirements.txt
python bot.py
```

### 4. Configurar el Bot de WhatsApp

```bash
cd whatsapp-bot
cp .env.example .env
# Edita .env con la URL del backend
npm install
node index.js
# Escanea el QR con tu WhatsApp
```

---

## 📲 Comandos

### Telegram
| Comando | Descripción |
|---------|-------------|
| `/start` | Mensaje de bienvenida |
| `/help` | Ayuda |
| `/resumen <texto>` | Resumir texto |
| Enviar audio/voz | Transcribir + resumen automático |

### WhatsApp
| Acción | Descripción |
|--------|-------------|
| Enviar audio/nota de voz | Transcripción + resumen |
| `!resumen <texto>` | Resumir texto enviado |
| `!ayuda` | Ver comandos disponibles |

---

## 🌐 Despliegue en Railway

1. Crea un proyecto en [Railway](https://railway.app)
2. Agrega 3 servicios: `backend`, `telegram-bot`, `whatsapp-bot`
3. Configura las variables de entorno en cada servicio
4. Despliega directamente desde este repositorio

---

## 📄 Variables de Entorno

### Backend
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL_TRANSCRIBE=whisper-1
OPENAI_MODEL_SUMMARY=gpt-4o-mini
```

### Telegram Bot
```env
TELEGRAM_BOT_TOKEN=...
BACKEND_URL=http://localhost:8000
```

### WhatsApp Bot
```env
BACKEND_URL=http://localhost:8000
```

---

## 🛠️ Tecnologías

- **OpenAI Whisper** - Transcripción de audio
- **OpenAI GPT-4o-mini** - Generación de resúmenes
- **FastAPI** - Backend API
- **python-telegram-bot** - Bot de Telegram
- **Baileys** - Bot de WhatsApp (no oficial)

---

## ⚠️ Advertencia

El bot de WhatsApp usa Baileys, una librería no oficial. Su uso puede violar los términos de servicio de WhatsApp. Úsalo bajo tu propia responsabilidad.

---

## 📝 Licencia

MIT License - ver [LICENSE](LICENSE)
