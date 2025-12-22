"""
Funciones de utilidad para el bot
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
import html

from config import ALLOWED_USERS, MAX_PEERS_DISPLAY, ROLE_ADMIN, ROLE_OPERATOR
from operators import operators_db

logger = logging.getLogger(__name__)

# ================= SEGURIDAD ================= #
def is_allowed(update: Update) -> bool:
    """Verifica si el usuario está autorizado"""
    if not update.effective_user:
        return False
    
    user_id = update.effective_user.id
    is_allowed_user = user_id in ALLOWED_USERS
    
    if not is_allowed_user:
        username = update.effective_user.username or "Sin nombre"
        logger.warning(f"Intento de acceso no autorizado: {user_id} (@{username})")
    
    return is_allowed_user

def get_user_role(user_id: int) -> Optional[str]:
    """Obtiene el rol del usuario"""
    user_data = ALLOWED_USERS.get(user_id)
    if user_data:
        return user_data.get("role")
    return None

def is_admin(user_id: int) -> bool:
    """Verifica si el usuario es administrador"""
    return get_user_role(user_id) == ROLE_ADMIN

def is_operator(user_id: int) -> bool:
    """Verifica si el usuario es operador"""
    return get_user_role(user_id) == ROLE_OPERATOR

def can_operator_create_peer(user_id: int) -> tuple:
    """
    Verifica si un operador puede crear un peer.
    
    Returns:
        (bool, str, datetime) - (puede_crear, mensaje_error, proximo_permiso)
    """
    return operators_db.can_create_peer(user_id)

def get_user_name(update_or_user) -> str:
    """Obtiene el nombre del usuario para logging - Ahora acepta Update o User"""
    from telegram import Update, User, CallbackQuery
    
    if isinstance(update_or_user, Update):
        user = update_or_user.effective_user
    elif isinstance(update_or_user, CallbackQuery):
        user = update_or_user.from_user
    elif isinstance(update_or_user, User):
        user = update_or_user
    else:
        return "Desconocido"
    
    if not user:
        return "Desconocido"
    
    username = f"@{user.username}" if user.username else ""
    return f"{user.first_name} {username}".strip()

# ================= FORMATEO ================= #
def format_size(bytes_size: int) -> str:
    """Formatea bytes a tamaño legible"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def format_handshake_time(seconds: Optional[int]) -> str:
    """Formatea el tiempo desde último handshake"""
    if not seconds:
        return "Nunca"
    
    if seconds < 60:
        return f"{seconds} seg"
    elif seconds < 3600:
        return f"{seconds // 60} min"
    elif seconds < 86400:
        return f"{seconds // 3600} horas"
    else:
        return f"{seconds // 86400} días"

def format_bytes_human(bytes_size: float) -> str:
    """Formatea bytes a formato humano legible (recibe MB)"""
    # Convertir MB a bytes
    bytes_size = bytes_size * 1024 * 1024
    
    if bytes_size == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(bytes_size)
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"

def format_time_ago(seconds: int) -> str:
    """Formatea segundos a 'hace X tiempo'"""
    if seconds <= 0:
        return "Nunca"
    
    if seconds < 60:
        return f"hace {int(seconds)} segundos"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"hace {int(minutes)} minutos"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"hace {int(hours)} horas"
    else:
        days = seconds // 86400
        return f"hace {int(days)} días"

def format_time_remaining(seconds: int) -> str:
    """Formatea segundos restantes en formato legible"""
    if seconds <= 0:
        return "Ahora mismo"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def format_peer_info(peer: Dict) -> str:
    """Formatea la información de un peer"""
    lines = []
    
    # Información básica
    name = peer.get('name', 'Sin nombre')
    public_key = peer.get('id', '')  # En esta API, la clave pública está en 'id'
    lines.append(f"👤 **{name}**")
    
    # Estado de conexión
    status = peer.get('status', '')
    latest_handshake = peer.get('latest_handshake_seconds', 0)
    
    if status == 'running' and latest_handshake > 0:
        lines.append(f"   🔗 Última conexión: {format_handshake_time(latest_handshake)}")
        status_text = "✅ Conectado"
    else:
        status_text = "❌ Desconectado"
    lines.append(f"   📊 Estado: {status_text}")
    
    # Transferencia de datos (en MB)
    total_receive = peer.get('total_receive', 0)  # MB
    total_sent = peer.get('total_sent', 0)        # MB
    
    lines.append(f"   ⬇️ Recibido: {format_bytes_human(total_receive)}")
    lines.append(f"   ⬆️ Enviado: {format_bytes_human(total_sent)}")
    
    # IPs
    allowed_ip = peer.get('allowed_ip', 'N/A')
    endpoint = peer.get('endpoint', 'N/A')
    lines.append(f"   📍 IP permitida: `{allowed_ip}`")
    lines.append(f"   🌐 Endpoint: `{endpoint}`")
    
    # Información adicional si existe
    if 'keepalive' in peer:
        lines.append(f"   ♻️ Keepalive: {peer['keepalive']}s")
    
    return "\n".join(lines)

def format_system_status(status_data: Dict) -> str:
    """Formatea el estado del sistema"""
    lines = ["🖥 **Estado del Sistema**\n"]
    
    # CPU
    cpu = status_data.get('CPU', {})
    cpu_percent = cpu.get('cpu_percent', 0)
    lines.append(f"💻 **CPU**: {cpu_percent}%")
    
    # Memoria
    memory = status_data.get('Memory', {}).get('VirtualMemory', {})
    mem_percent = memory.get('percent', 0)
    mem_total = format_size(memory.get('total', 0))
    mem_available = format_size(memory.get('available', 0))
    lines.append(f"🧠 **Memoria**: {mem_percent:.1f}% usado")
    lines.append(f"   Total: {mem_total} | Disponible: {mem_available}")
    
    # Swap
    swap = status_data.get('Memory', {}).get('SwapMemory', {})
    if swap.get('total', 0) > 0:
        swap_percent = swap.get('percent', 0)
        swap_total = format_size(swap.get('total', 0))
        lines.append(f"💾 **Swap**: {swap_percent}% de {swap_total}")
    
    # Discos (solo los principales)
    disks = status_data.get('Disks', [])
    if disks:
        lines.append("\n💾 **Discos principales:**")
        for disk in disks[:3]:  # Mostrar solo 3 discos
            mount = disk.get('mountPoint', 'N/A')
            percent = disk.get('percent', 0)
            free = format_size(disk.get('free', 0))
            lines.append(f"   {mount}: {percent}% usado ({free} libre)")
    
    # Interfaces de red - MODIFICADO PARA MOSTRAR TODAS LAS INTERFACES
    interfaces = status_data.get('NetworkInterfaces', {})
    if interfaces:
        lines.append("\n📡 **Interfaces de Red:**")
        
        # Ordenar interfaces para mostrar primero las importantes
        interface_order = ['lo', 'ens3', 'eth0', 'eth1']  # Interfaces principales
        wg_interfaces = []
        other_interfaces = []
        
        for iface_name, iface_data in interfaces.items():
            if iface_name.startswith('wg'):
                wg_interfaces.append((iface_name, iface_data))
            elif iface_name not in interface_order:
                other_interfaces.append((iface_name, iface_data))
        
        # Mostrar interfaces en orden específico
        for iface_name in interface_order:
            if iface_name in interfaces:
                iface_data = interfaces[iface_name]
                sent = format_size(iface_data.get('bytes_sent', 0))
                recv = format_size(iface_data.get('bytes_recv', 0))
                lines.append(f"   {iface_name}: ⬆{sent} ⬇{recv}")
        
        # Mostrar todas las interfaces WireGuard
        if wg_interfaces:
            lines.append("\n🔗 **Interfaces WireGuard:**")
            for iface_name, iface_data in sorted(wg_interfaces):
                sent = format_size(iface_data.get('bytes_sent', 0))
                recv = format_size(iface_data.get('bytes_recv', 0))
                lines.append(f"   {iface_name}: ⬆{sent} ⬇{recv}")
        
        # Mostrar otras interfaces (limitado a 5 para no hacer muy largo el mensaje)
        if other_interfaces:
            lines.append("\n🌐 **Otras Interfaces:**")
            for iface_name, iface_data in sorted(other_interfaces)[:5]:  # Máximo 5
                sent = format_size(iface_data.get('bytes_sent', 0))
                recv = format_size(iface_data.get('bytes_recv', 0))
                lines.append(f"   {iface_name}: ⬆{sent} ⬇{recv}")
            
            if len(other_interfaces) > 5:
                lines.append(f"   ... y {len(other_interfaces) - 5} más")
    
    return "\n".join(lines)

def format_config_summary(configs: List[Dict]) -> str:
    """Formatea un resumen de todas las configuraciones"""
    if not configs:
        return "⚠️ No hay configuraciones disponibles"
    
    lines = ["📡 **Resumen de Configuraciones**\n"]
    
    total_peers = 0
    total_connected = 0
    
    for config in configs:
        name = config.get('Name', 'Desconocido')
        peers = config.get('TotalPeers', 0)
        connected = config.get('ConnectedPeers', 0)
        listen_port = config.get('ListenPort', 'N/A')
        
        total_peers += peers
        total_connected += connected
        
        status_emoji = "✅" if connected > 0 else "⚠️"
        lines.append(f"{status_emoji} **{name}** (puerto: {listen_port})")
        lines.append(f"   👥 Peers: {connected}/{peers} conectados")
    
    lines.append(f"\n📊 **Totales:** {total_connected}/{total_peers} peers conectados")
    
    return "\n".join(lines)

# ================= MANEJO DE MENSAJES ================= #
async def send_large_message(update, text: str, parse_mode: str = "Markdown", 
                           max_length: int = 4000, reply_markup=None) -> None:
    """Divide mensajes largos para evitar límites de Telegram"""
    if len(text) <= max_length:
        if hasattr(update, 'edit_message_text'):
            await update.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        return
    
    # Dividir por líneas si es posible
    lines = text.split('\n')
    current_part = []
    current_length = 0
    
    for line in lines:
        if current_length + len(line) + 1 > max_length:
            # Enviar parte actual
            part_text = '\n'.join(current_part)
            if hasattr(update, 'edit_message_text'):
                await update.edit_message_text(part_text, parse_mode=parse_mode)
            else:
                await update.message.reply_text(part_text, parse_mode=parse_mode)
            
            # Resetear para siguiente parte
            current_part = [line]
            current_length = len(line)
        else:
            current_part.append(line)
            current_length += len(line) + 1
    
    # Enviar última parte CON el botón de volver
    if current_part:
        part_text = '\n'.join(current_part)
        if hasattr(update, 'edit_message_text'):
            await update.edit_message_text(part_text, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            await update.message.reply_text(part_text, parse_mode=parse_mode, reply_markup=reply_markup)

def truncate_text(text: str, max_length: int = 100) -> str:
    """Trunca texto y agrega ... si es muy largo"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

# ================= LOGGING MEJORADO ================= #
def log_command(update: Update, command: str):
    """Registra el uso de un comando"""
    user_id = update.effective_user.id
    username = get_user_name(update)
    role = get_user_role(user_id) or "sin_rol"
    logger.info(f"Comando '{command}' ejecutado por {username} ({user_id}) - Rol: {role}")

def log_command_with_role(update: Update, command: str):
    """Registra el uso de un comando incluyendo rol"""
    user_id = update.effective_user.id
    username = get_user_name(update)
    role = get_user_role(user_id) or "sin_rol"
    logger.info(f"Comando '{command}' por {username} ({user_id}) - Rol: {role}")

def log_callback(update: Update, callback_data: str):
    """Registra el uso de un callback"""
    user_id = update.effective_user.id
    username = get_user_name(update)
    logger.info(f"Callback '{callback_data}' por {username} ({user_id})")

def log_callback_with_role(update: Update, callback_data: str):
    """Registra el uso de un callback incluyendo rol"""
    user_id = update.effective_user.id
    username = get_user_name(update)
    role = get_user_role(user_id) or "sin_rol"
    logger.info(f"Callback '{callback_data}' por {username} ({user_id}) - Rol: {role}")

def log_error(update: Update, error: Exception, context: str = ""):
    """Registra un error con contexto"""
    user_info = f"Usuario: {get_user_name(update)}" if update else "Sin usuario"
    logger.error(f"Error en {context}: {str(error)} | {user_info}", exc_info=True)

def escape_markdown(text: str) -> str:
    """Escapa caracteres especiales de Markdown"""
    if not text:
        return text
    
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

# ================= SISTEMA DE MENSAJES SEGUROS ================= #
def safe_message(text: str, parse_mode: str = "HTML", **kwargs) -> dict:
    """
    Crea mensajes seguros para Telegram con escape automático de variables.
    
    Args:
        text: Texto del mensaje con placeholders {nombre_variable}
        parse_mode: "HTML" (recomendado) o "Markdown"
        **kwargs: Variables para reemplazar en el texto
        
    Returns:
        dict: Diccionario listo para usar con ** en reply_text/edit_message_text
        
    Ejemplo:
        message_data = safe_message(
            "ℹ️ <b>Información de {peer}</b>\\n"
            "<b>Config:</b> {config}\\n"
            "<b>IP:</b> <code>{ip}</code>",
            peer=peer_name,
            config=config_name,
            ip=allowed_ip,
            parse_mode="HTML"
        )
        await update.message.reply_text(**message_data)
    """
    if parse_mode == "HTML":
        # Escapar todas las variables para HTML
        escaped_kwargs = {k: html.escape(str(v)) for k, v in kwargs.items()}
        formatted_text = text.format(**escaped_kwargs)
    elif parse_mode == "Markdown":
        # Escapar para Markdown
        escaped_kwargs = {}
        for k, v in kwargs.items():
            str_v = str(v)
            escaped_v = escape_markdown(str_v)
            escaped_kwargs[k] = escaped_v
        formatted_text = text.format(**escaped_kwargs)
    else:
        # Texto plano
        escaped_kwargs = {k: str(v) for k, v in kwargs.items()}
        formatted_text = text.format(**escaped_kwargs)
        parse_mode = None
    
    return {"text": formatted_text, "parse_mode": parse_mode}
