const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeInMemoryStore,
  downloadMediaMessage
} = require('@whiskeysockets/baileys')
const qrcode = require('qrcode-terminal')
const axios = require('axios')
const FormData = require('form-data')
const pino = require('pino')
require('dotenv').config()

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'
const LOG_LEVEL = process.env.LOG_LEVEL || 'silent'

// Logger silencioso para no ensuciar la consola
const logger = pino({ level: LOG_LEVEL })

// Store en memoria para historial de mensajes
const store = makeInMemoryStore({ logger })

/**
 * Divide un texto largo en partes para no superar el limite de WhatsApp
 */
function splitMessage(text, maxLength = 4000) {
  if (text.length <= maxLength) return [text]
  const parts = []
  let remaining = text
  while (remaining.length > maxLength) {
    let splitAt = remaining.lastIndexOf('\n', maxLength)
    if (splitAt === -1) splitAt = maxLength
    parts.push(remaining.substring(0, splitAt))
    remaining = remaining.substring(splitAt).trimStart()
  }
  if (remaining) parts.push(remaining)
  return parts
}

/**
 * Envia un mensaje (posiblemente largo) dividido en partes
 */
async function sendLongMessage(sock, jid, text) {
  const parts = splitMessage(text)
  for (const part of parts) {
    await sock.sendMessage(jid, { text: part })
    // Pequena pausa entre mensajes
    if (parts.length > 1) await new Promise(r => setTimeout(r, 500))
  }
}

/**
 * Llama al backend para resumir un texto
 */
async function resumirTexto(texto) {
  const response = await axios.post(
    `${BACKEND_URL}/resumen_texto`,
    { texto },
    { timeout: 60000 }
  )
  return response.data.resumen
}

/**
 * Descarga el audio y lo envia al backend para transcribir y resumir
 */
async function transcribirAudio(sock, msg) {
  const buffer = await downloadMediaMessage(msg, 'buffer', {})
  const form = new FormData()
  form.append('file', buffer, {
    filename: 'audio.ogg',
    contentType: 'audio/ogg'
  })
  const response = await axios.post(
    `${BACKEND_URL}/transcribir_resumir_audio`,
    form,
    {
      headers: form.getHeaders(),
      timeout: 120000,
      maxBodyLength: Infinity,
      maxContentLength: Infinity
    }
  )
  return response.data
}

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys')
  const { version } = await fetchLatestBaileysVersion()

  console.log('Usando Baileys version:', version.join('.'))

  const sock = makeWASocket({
    version,
    logger,
    auth: state,
    printQRInTerminal: false,
    browser: ['Audio Transcriber Bot', 'Chrome', '1.0.0']
  })

  store.bind(sock.ev)

  // Manejo de QR
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update

    if (qr) {
      console.log('\n Escanea este QR con tu WhatsApp:')
      qrcode.generate(qr, { small: true })
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut

      console.log('Conexion cerrada. Reconectar:', shouldReconnect)

      if (shouldReconnect) {
        console.log('Reconectando en 5 segundos...')
        setTimeout(connectToWhatsApp, 5000)
      } else {
        console.log('Sesion cerrada. Borra la carpeta auth_info_baileys y reinicia.')
      }
    } else if (connection === 'open') {
      console.log('Conectado a WhatsApp exitosamente!')
    }
  })

  // Guardar credenciales
  sock.ev.on('creds.update', saveCreds)

  // Procesar mensajes
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return

    for (const msg of messages) {
      // Ignorar mensajes propios
      if (msg.key.fromMe) continue
      // Ignorar mensajes sin contenido
      if (!msg.message) continue

      const jid = msg.key.remoteJid
      const msgContent = msg.message

      // Detectar texto
      const text = msgContent.conversation ||
        msgContent.extendedTextMessage?.text ||
        ''

      // Comandos de texto
      if (text) {
        // !ayuda
        if (text.trim() === '!ayuda' || text.trim() === '!help') {
          await sock.sendMessage(jid, {
            text: 'Comandos disponibles:\n\n' +
              '- Envia una nota de voz o audio -> Transcripcion + Resumen\n' +
              '- !resumen <texto> -> Resumir un texto\n' +
              '- !ayuda -> Ver esta ayuda'
          })
          continue
        }

        // !resumen <texto>
        if (text.startsWith('!resumen ')) {
          const textoAResumir = text.replace('!resumen ', '').trim()
          if (!textoAResumir) {
            await sock.sendMessage(jid, { text: 'Uso: !resumen <texto a resumir>' })
            continue
          }

          await sock.sendMessage(jid, { text: 'Generando resumen...' })

          try {
            const resumen = await resumirTexto(textoAResumir)
            await sendLongMessage(sock, jid, `Resumen:\n\n${resumen}`)
          } catch (err) {
            console.error('Error al resumir:', err.message)
            await sock.sendMessage(jid, { text: 'Error al generar el resumen. Intenta de nuevo.' })
          }
          continue
        }
      }

      // Detectar audio
      const isAudio = msgContent.audioMessage || msgContent.voiceMessage

      if (isAudio) {
        await sock.sendMessage(jid, { text: 'Procesando audio, un momento...' })

        try {
          const { transcripcion, resumen } = await transcribirAudio(sock, msg)

          const respuesta = [
            'Transcripcion:',
            '',
            transcripcion,
            '',
            '='.repeat(30),
            '',
            'Resumen:',
            '',
            resumen
          ].join('\n')

          await sendLongMessage(sock, jid, respuesta)
        } catch (err) {
          console.error('Error al procesar audio:', err.message)
          await sock.sendMessage(jid, {
            text: 'Error al procesar el audio. Asegurate de que el backend este corriendo.'
          })
        }
      }
    }
  })

  return sock
}

// Inicio
console.log('Iniciando WhatsApp Audio Transcriber Bot...')
console.log(`Backend URL: ${BACKEND_URL}`)
connectToWhatsApp()
