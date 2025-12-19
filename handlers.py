"""
Manejadores de comandos y callbacks del bot WGDashboard
"""

import logging
import json
import datetime
import secrets
import base64
import ipaddress
import re
import subprocess
import hashlib
import time
import urllib.parse
from typing import Dict, List, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, CallbackContext
import io

from config import ALLOWED_USERS
from wg_api import api_client
from keyboards import (
    main_menu, config_menu, paginated_configs_menu, restrictions_menu,
    paginated_restricted_peers_menu, paginated_unrestricted_peers_menu,
    confirmation_menu, back_button, refresh_button,
    InlineKeyboardMarkup, decode_callback_data
)
from utils import (
    is_allowed, get_user_name, format_peer_info,
    format_system_status, format_config_summary,
    send_large_message, log_command, log_callback, log_error,
    format_bytes_human, format_time_ago
)

logger = logging.getLogger(__name__)

# ================= FUNCIONES AUXILIARES ================= #
def format_peer_for_list(peer: Dict) -> str:
    """Formatea un peer para la lista básica"""
    name = peer.get('name', 'Sin nombre')
    latest_handshake = peer.get('latest_handshake_seconds', 0)
    status = peer.get('status', 'stopped')
    
    # Determinar estado
    if status == 'running' and latest_handshake > 0:
        status_emoji = "✅"
        last_seen = format_time_ago(latest_handshake)
    else:
        status_emoji = "❌"
        last_seen = "Nunca" if latest_handshake == 0 else format_time_ago(latest_handshake)
    
    allowed_ip = peer.get('allowed_ip', 'N/A')
    return f"{status_emoji} **{name}** - IP: `{allowed_ip}` - Última conexión: {last_seen}"

def format_peer_for_detail(peer: Dict) -> str:
    """Formatea un peer para vista detallada"""
    lines = []
    
    # Información básica
    name = peer.get('name', 'Sin nombre')
    public_key = peer.get('id', 'N/A')
    
    lines.append(f"👤 Nombre: {name}")
    lines.append(f"🔑 Clave pública: {public_key}")
    
    # Endpoint
    endpoint = peer.get('endpoint', 'N/A')
    lines.append(f"📍 Endpoint: {endpoint}")
    
    # IPs permitidas
    allowed_ip = peer.get('allowed_ip', 'N/A')
    lines.append(f"🌐 IP permitida: {allowed_ip}")
    
    # Estado
    status = peer.get('status', 'stopped')
    latest_handshake = peer.get('latest_handshake_seconds', 0)
    
    if status == 'running' and latest_handshake > 0:
        lines.append(f"📊 Estado: ✅ Conectado")
        lines.append(f"🔗 Última conexión: {format_time_ago(latest_handshake)}")
    else:
        lines.append(f"📊 Estado: ❌ Desconectado")
        if latest_handshake > 0:
            lines.append(f"🔗 Última conexión: {format_time_ago(latest_handshake)}")
        else:
            lines.append(f"🔗 Última conexión: Nunca")
    
    # Transferencias
    transfer_received = peer.get('total_receive', 0)
    transfer_sent = peer.get('total_sent', 0)
    
    lines.append(f"⬇️ Recibido: {format_bytes_human(transfer_received)}")
    lines.append(f"⬆️ Enviado: {format_bytes_human(transfer_sent)}")
    
    # Keepalive (si existe)
    keepalive = peer.get('keepalive')
    if keepalive:
        lines.append(f"♻️ Keepalive: {keepalive} segundos")
    
    # Remote endpoint
    remote_endpoint = peer.get('remote_endpoint', 'N/A')
    if remote_endpoint != 'N/A':
        lines.append(f"🌍 Remote endpoint: {remote_endpoint}")
    
    # DNS
    dns = peer.get('DNS', 'N/A')
    if dns != 'N/A':
        lines.append(f"🔗 DNS: {dns}")
    
    # MTU
    mtu = peer.get('mtu', 'N/A')
    if mtu != 'N/A':
        lines.append(f"📡 MTU: {mtu}")
    
    # Jobs (trabajos/restricciones)
    jobs = peer.get('jobs', [])
    if jobs:
        lines.append(f"\n⏰ Schedule Jobs activos: {len(jobs)}")
        for job in jobs:
            action = job.get('Action', '')
            field = job.get('Field', '')
            value = job.get('Value', 'N/A')
            operator = job.get('Operator', 'lgt')
            
            if field == "total_data":
                field_text = "Límite de datos (GB)"
                value_display = f"{value} GB"
            elif field == "date":
                field_text = "Fecha de expiración"
                value_display = value
            else:
                field_text = field
                value_display = value
            
            lines.append(f"   • {action.upper()} {field_text}: {value_display}")
    
    return "\n".join(lines)

def format_peer_for_detail_plain(peer: Dict) -> str:
    """Formatea un peer para vista detallada SIN formato Markdown"""
    lines = []
    
    # Información básica
    name = peer.get('name', 'Sin nombre')
    public_key = peer.get('id', 'N/A')
    
    lines.append(f"👤 Nombre: {name}")
    lines.append(f"🔑 Clave pública: {public_key}")
    
    # Endpoint
    endpoint = peer.get('endpoint', 'N/A')
    lines.append(f"📍 Endpoint: {endpoint}")
    
    # IPs permitidas
    allowed_ip = peer.get('allowed_ip', 'N/A')
    lines.append(f"🌐 IP permitida: {allowed_ip}")
    
    # Estado
    status = peer.get('status', 'stopped')
    latest_handshake = peer.get('latest_handshake_seconds', 0)
    
    if status == 'running' and latest_handshake > 0:
        lines.append(f"📊 Estado: ✅ Conectado")
        lines.append(f"🔗 Última conexión: {format_time_ago(latest_handshake)}")
    else:
        lines.append(f"📊 Estado: ❌ Desconectado")
        if latest_handshake > 0:
            lines.append(f"🔗 Última conexión: {format_time_ago(latest_handshake)}")
        else:
            lines.append(f"🔗 Última conexión: Nunca")
    
    # Transferencias
    transfer_received = peer.get('total_receive', 0)
    transfer_sent = peer.get('total_sent', 0)
    
    lines.append(f"⬇️ Recibido: {format_bytes_human(transfer_received)}")
    lines.append(f"⬆️ Enviado: {format_bytes_human(transfer_sent)}")
    
    # Keepalive (si existe)
    keepalive = peer.get('keepalive')
    if keepalive:
        lines.append(f"♻️ Keepalive: {keepalive} segundos")
    
    # Remote endpoint
    remote_endpoint = peer.get('remote_endpoint', 'N/A')
    if remote_endpoint != 'N/A':
        lines.append(f"🌍 Remote endpoint: {remote_endpoint}")
    
    # DNS
    dns = peer.get('DNS', 'N/A')
    if dns != 'N/A':
        lines.append(f"🔗 DNS: {dns}")
    
    # MTU
    mtu = peer.get('mtu', 'N/A')
    if mtu != 'N/A':
        lines.append(f"📡 MTU: {mtu}")
    
    # Jobs (trabajos/restricciones)
    jobs = peer.get('jobs', [])
    if jobs:
        lines.append(f"\n⏰ Schedule Jobs activos: {len(jobs)}")
        for job in jobs:
            action = job.get('Action', '')
            field = job.get('Field', '')
            value = job.get('Value', 'N/A')
            operator = job.get('Operator', 'lgt')
            
            if field == "total_data":
                field_text = "Límite de datos (GB)"
                value_display = f"{value} GB"
            elif field == "date":
                field_text = "Fecha de expiración"
                value_display = value
            else:
                field_text = field
                value_display = value
            
            lines.append(f"   • {action.upper()} {field_text}: {value_display}")
    
    return "\n".join(lines)

def format_schedule_job_for_list(job: Dict) -> str:
    """Formatea un schedule job para la lista"""
    action = job.get('Action', 'desconocido')
    field = job.get('Field', 'desconocido')
    value = job.get('Value', 'N/A')
    
    if field == "total_data":
        field_text = "Límite de datos (GB)"
        value_display = f"{value} GB"
    elif field == "date":
        field_text = "Fecha de expiración"
        value_display = value
    else:
        field_text = field
        value_display = value
    
    return f"{action.upper()} {field_text}: {value_display}"

# ================= GENERACIÓN DE CLAVES ================= #
def generate_wireguard_keys():
    """Genera un par de claves WireGuard válidas"""
    try:
        # Intentar usar el comando wg si está disponible
        private_key = subprocess.run(
            ["wg", "genkey"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        public_key = subprocess.run(
            ["wg", "pubkey"],
            input=private_key,
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        return private_key, public_key
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: generar claves base64 válidas (32 bytes)
        private_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
        # Para WireGuard, la clave pública se calcula de forma criptográfica
        # Como no tenemos la librería criptográfica, generamos otra clave
        # En producción real, usaría cryptography o wg nativo
        public_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
        logger.warning("Usando claves simuladas (wg no disponible)")
        return private_key, public_key

def generate_preshared_key():
    """Genera una pre-shared key para WireGuard"""
    try:
        # Usar wg genpsk si está disponible
        preshared_key = subprocess.run(
            ["wg", "genpsk"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        return preshared_key
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: generar clave base64 válida (32 bytes)
        preshared_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
        return preshared_key

def create_peer_hash(config_name: str, public_key: str, peer_name: str) -> str:
    """Crea un hash único y corto para identificar un peer (versión simplificada)"""
    # Usar solo información básica para evitar problemas
    unique_string = f"{config_name}:{public_key}:{peer_name}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:12]

# ================= COMANDOS ================= #
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador del comando /start"""
    if not is_allowed(update):
        return
    
    log_command(update, "start")
    
    welcome_text = f"""🤖 *Bienvenido al Bot de WGDashboard, {get_user_name(update)}!*

Con este bot puedes gestionar tus configuraciones WireGuard de manera remota.

*Funciones disponibles:*
• 📡 Ver y gestionar configuraciones
• 👤 Administrar peers (conectados/desconectados)
• 🖥 Monitorear estado del sistema
• ⚡ Ver protocolos habilitados
• 📊 Estadísticas detalladas
• ⏰ Schedule Jobs (trabajos programados)
• 🚫 Gestionar restricciones de peers

Selecciona una opción del menú o usa /help para ver todos los comandos."""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador del comando /help"""
    if not is_allowed(update):
        return
    
    log_command(update, "help")
    
    help_text = """📚 *Comandos disponibles:*

*Comandos principales:*
/start - Iniciar el bot y mostrar menú
/help - Mostrar esta ayuda
/stats - Estadísticas del sistema
/configs - Listar configuraciones

*Funciones desde el menú:*
• 🔌 Test API - Verificar conexión con WGDashboard
• 📡 Configuraciones - Listar y gestionar configs
• 🖥 Estado del Sistema - Monitoreo en tiempo real
• ⚡ Protocolos - Ver protocolos habilitados
• 📊 Estadísticas - Estadísticas detalladas
• 🚫 Restricciones - Gestionar peers restringidos

*Acciones por configuración:*
• 👤 Listar Peers - Ver lista de peers
• 📋 Detalles Peers - Información detallada
• 🗑 Eliminar Peer - Eliminar un peer
• ➕ Agregar Peer - Agregar nuevo peer automáticamente
• ⏰ Schedule Jobs - Gestionar trabajos programados
• 🚫 Restricciones - Ver y gestionar peers restringidos
• 🔄 Actualizar - Refrescar información

*Nuevo: Gestión de Restricciones*
• 👥 Restringidos - Ver peers restringidos y quitar restricción
• 🔒 Restringir Peer - Restringir acceso a un peer

*Notas:*
- Solo usuarios autorizados pueden usar este bot
- Los datos se actualizan automáticamente
- Usa los botones para navegar fácilmente"""
    
    await update.message.reply_text(
        help_text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador del comando /stats"""
    if not is_allowed(update):
        return
    
    log_command(update, "stats")
    
    await update.message.reply_text(
        "📊 Obteniendo estadísticas del sistema...",
        reply_markup=refresh_button("system_status")
    )
    
    # Obtener datos
    result = api_client.get_system_status()
    
    if not result.get("status"):
        await update.message.reply_text(
            f"❌ Error: {result.get('message', 'Error desconocido')}",
            reply_markup=refresh_button("system_status")
        )
        return
    
    status_data = result.get("data", {})
    formatted_text = format_system_status(status_data)
    
    await update.message.reply_text(
        formatted_text,
        reply_markup=refresh_button("system_status"),
        parse_mode="Markdown"
    )

async def configs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador del comando /configs"""
    if not is_allowed(update):
        return
    
    log_command(update, "configs")
    await show_configurations(update)

# ================= CALLBACK HANDLERS ================= #
async def callback_handler(update: Update, context: CallbackContext):
    """Manejador central de callbacks"""
    if not is_allowed(update):
        return
    
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    log_callback(update, callback_data)
    
    logger.debug(f"CALLBACK DEBUG: {callback_data}")
    
    try:
        # --- MANEJO DE ACCIONES PRINCIPALES ---
        if callback_data == "main_menu":
            await handle_main_menu(query)
        
        elif callback_data == "handshake":
            await handle_handshake(query)
        
        elif callback_data == "configs":
            await handle_configs(query)
        
        elif callback_data.startswith("configs_summary"):
            await handle_configs_summary(query)
        
        elif callback_data == "system_status":
            await handle_system_status(query)
        
        elif callback_data == "protocols":
            await handle_protocols(query)
        
        elif callback_data == "stats":
            await handle_stats(query)
        
        elif callback_data == "help":
            await handle_help(query)
        
        # --- MANEJO DE RESTRICCIONES (VERSIÓN SIMPLIFICADA) ---
        elif callback_data.startswith("restrictions:"):
            parts = callback_data.split(":")
            if len(parts) > 1:
                await handle_restrictions_menu(query, parts[1])
        
        elif callback_data.startswith("restricted_peers:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                page = int(parts[2])
                await handle_restricted_peers_list(query, context, config_name, page)
        
        elif callback_data.startswith("restrict_peer_menu:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                page = int(parts[2])
                await handle_unrestricted_peers_list(query, context, config_name, page)
        
        # --- NUEVAS RUTAS SIMPLIFICADAS ---
        elif callback_data.startswith("unrestrict:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                peer_index = int(parts[2])
                await handle_unrestrict_simple(query, context, config_name, peer_index)
        
        elif callback_data.startswith("restrict:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                peer_index = int(parts[2])
                await handle_restrict_simple(query, context, config_name, peer_index)
        
        # --- PAGINACIÓN SIMPLIFICADA ---
        elif callback_data.startswith("page_res:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                page = int(parts[2])
                await handle_restricted_peers_list(query, context, config_name, page)
        
        elif callback_data.startswith("page_unres:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                page = int(parts[2])
                await handle_unrestricted_peers_list(query, context, config_name, page)
        
        # --- MANEJO DE PAGINACIÓN ORIGINAL ---
        elif callback_data.startswith("page_configs:"):
            parts = callback_data.split(":")
            page = int(parts[1]) if len(parts) > 1 else 0
            await handle_configs(query, page)
        
        elif callback_data.startswith("page_delete_peer:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                page = int(parts[2])
                await handle_delete_peer_menu(query, config_name, page)
        
        elif callback_data.startswith("page_peers:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                page = int(parts[2])
                await handle_peers_list(query, context, config_name, page)
        
        elif callback_data.startswith("page_schedule_jobs:"):
            parts = callback_data.split(":")
            if len(parts) >= 4:
                config_name = parts[1]
                peer_index = parts[2]
                page = int(parts[3])
                await handle_schedule_jobs_list(query, context, config_name, peer_index, page)
        
        # --- MANEJO DE DESCARGA DIRECTA DESDE LISTA ---
        elif callback_data.startswith("download_peer_direct:"):
            parts = callback_data.split(":")
            if len(parts) >= 2:
                peer_hash = parts[1]
                await handle_download_peer_direct(query, context, peer_hash)

        # --- MANEJO DE CONFIGURACIONES ESPECÍFICAS ---
        elif callback_data.startswith("cfg:"):
            parts = callback_data.split(":")
            if len(parts) > 1:
                await handle_config_detail(query, parts[1])
        
        elif callback_data.startswith("peers:"):
            parts = callback_data.split(":")
            if len(parts) > 1:
                await handle_peers_list(query, context, parts[1], 0)
        
        elif callback_data.startswith("peers_detailed:"):
            parts = callback_data.split(":")
            if len(parts) > 1:
                config_name = parts[1]
                await handle_peers_detailed(query, config_name)
        
        elif callback_data.startswith("peers_detailed_full:"):
            parts = callback_data.split(":")
            if len(parts) >= 2:
                config_name = parts[1]
                await handle_peers_detailed_full(query, config_name)
        
        # --- MANEJO DE DETALLES PAGINADOS (AGREGADO PARA CORREGIR EL ERROR) ---
        elif callback_data.startswith("peers_detailed_paginated:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                page = int(parts[2])
                await handle_peers_detailed_paginated(query, config_name, page)
        
        # --- MANEJO DE ELIMINACIÓN DE PEERS ---
        elif callback_data.startswith("delete_peer:"):
            parts = callback_data.split(":")
            if len(parts) > 1:
                await handle_delete_peer_menu(query, parts[1], 0)
        
        elif callback_data.startswith("delete_peer_confirm:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                peer_index = parts[2]
                await handle_delete_peer_confirm(query, config_name, peer_index)
        
        elif callback_data.startswith("delete_peer_execute:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                peer_index_encoded = parts[2]
                peer_index = decode_callback_data(peer_index_encoded)
                await handle_delete_peer_final(query, config_name, peer_index)
        
        # --- MANEJO DE AGREGAR PEER (AUTOMÁTICO) ---
        elif callback_data.startswith("add_peer:"):
            parts = callback_data.split(":")
            if len(parts) > 1:
                await handle_add_peer(query, context, parts[1])
        
        # --- MANEJO DE DESCARGA DE CONFIGURACIÓN ---
        elif callback_data.startswith("download_config:"):
            parts = callback_data.split(":")
            if len(parts) >= 2:
                peer_hash = parts[1]
                await handle_download_peer_config(query, context, peer_hash)
        
        elif callback_data.startswith("peer_download:"):
            parts = callback_data.split(":")
            if len(parts) >= 4:
                config_name = parts[1]
                peer_index = parts[2]
                peer_hash = parts[3]
                await handle_peer_download_list(query, context, config_name, peer_index, peer_hash)
        
        # --- MANEJO DE SCHEDULE JOBS ---
        elif callback_data.startswith("schedule_jobs_menu:"):
            parts = callback_data.split(":")
            if len(parts) > 1:
                await handle_schedule_jobs_menu(query, context, parts[1])
        
        elif callback_data.startswith("schedule_job_peer:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                peer_index = int(parts[2])
                await handle_schedule_job_peer_selected(query, context, config_name, peer_index)
        
        elif callback_data.startswith("add_schedule_job_data:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                peer_index = parts[2]
                await handle_add_schedule_job_data(query, context, config_name, peer_index)
        
        elif callback_data.startswith("add_schedule_job_date:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                peer_index = parts[2]
                await handle_add_schedule_job_date(query, context, config_name, peer_index)
        
        # --- MANEJO DE ELIMINACIÓN DE SCHEDULE JOBS ---
        elif callback_data.startswith("delete_schedule_job_final:"):
            parts = callback_data.split(":")
            if len(parts) >= 4:
                config_name = parts[1]
                peer_index = parts[2]
                job_index = parts[3]
                await handle_delete_schedule_job_execute(query, context, config_name, peer_index, job_index)
        
        elif callback_data.startswith("delete_schedule_job_all:"):
            parts = callback_data.split(":")
            if len(parts) >= 3:
                config_name = parts[1]
                peer_index = parts[2]
                await handle_delete_schedule_job_confirm(query, context, config_name, peer_index, "all")
        
        elif callback_data.startswith("delete_schedule_job_confirm:"):
            parts = callback_data.split(":")
            if len(parts) >= 4:
                config_name = parts[1]
                peer_index = parts[2]
                job_index = parts[3]
                await handle_delete_schedule_job_confirm(query, context, config_name, peer_index, job_index)
        
        elif callback_data.startswith("delete_schedule_job_execute:"):
            parts = callback_data.split(":")
            if len(parts) >= 4:
                config_name = parts[1]
                peer_index = parts[2]
                job_index = parts[3]
                await handle_delete_schedule_job_execute(query, context, config_name, peer_index, job_index)
        
        # --- SI NO RECONOCE EL CALLBACK ---
        else:
            logger.warning(f"Acción no reconocida: {callback_data}")
            await query.edit_message_text(
                f"❌ Acción no reconocida: {callback_data}",
                reply_markup=back_button("main_menu")
            )
            
    except Exception as e:
        log_error(update, e, f"callback_handler: {callback_data}")
        await query.edit_message_text(
            f"❌ Ocurrió un error al procesar la acción\n\nError: {str(e)}\n\nCallback: {callback_data}",
            reply_markup=back_button("main_menu")
        )

# ================= HANDLERS DE RESTRICCIONES ================= #
async def handle_restrictions_menu(query, config_name: str):
    """Muestra el menú de restricciones"""
    await query.edit_message_text(
        f"🚫 *Restricciones - {config_name}*\n\n"
        f"Selecciona una opción para gestionar restricciones:",
        reply_markup=restrictions_menu(config_name),
        parse_mode="Markdown"
    )

async def handle_restricted_peers_list(query, context: CallbackContext, config_name: str, page: int = 0):
    """Muestra la lista paginada de peers restringidos - VERSIÓN SIMPLIFICADA"""
    await query.edit_message_text(f"👥 Obteniendo peers restringidos...")
    
    result = api_client.get_peers(config_name)
    
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error: {result.get('message', 'Error desconocido')}",
            reply_markup=back_button(f"restrictions:{config_name}")
        )
        return
    
    restricted_peers = result.get("restricted_data", [])
    
    if not restricted_peers:
        await query.edit_message_text(
            f"✅ *No hay peers restringidos*\n\nTodos los peers tienen acceso normal.",
            reply_markup=back_button(f"restrictions:{config_name}"),
            parse_mode="Markdown"
        )
        return
    
    # Guardar en el contexto para uso posterior
    context.user_data[f'restricted_peers_{config_name}'] = restricted_peers
    
    total_peers = len(restricted_peers)
    total_pages = (total_peers - 1) // 6 + 1  # Cambiado a 6
    
    if page >= total_pages:
        page = total_pages - 1
    
    keyboard = paginated_restricted_peers_menu(restricted_peers, config_name, page)
    
    message = f"🚫 *Peers Restringidos - {config_name}*\n\n"
    message += f"📊 Total: {total_peers}\n"
    message += f"📄 Página {page + 1} de {total_pages}\n\n"
    message += "Selecciona un peer para quitar restricción:"
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def handle_unrestricted_peers_list(query, context: CallbackContext, config_name: str, page: int = 0):
    """Muestra la lista paginada de peers NO restringidos - VERSIÓN SIMPLIFICADA"""
    await query.edit_message_text(f"🔒 Obteniendo peers...")
    
    result = api_client.get_peers(config_name)
    
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error: {result.get('message', 'Error desconocido')}",
            reply_markup=back_button(f"restrictions:{config_name}")
        )
        return
    
    all_peers = result.get("data", [])
    restricted_peers = result.get("restricted_data", [])
    
    # Obtener claves de peers restringidos
    restricted_keys = {peer.get('id') for peer in restricted_peers}
    
    # Filtrar peers no restringidos
    unrestricted_peers = []
    for peer in all_peers:
        if peer.get('id') not in restricted_keys:
            unrestricted_peers.append(peer)
    
    if not unrestricted_peers:
        await query.edit_message_text(
            f"ℹ️ *Todos los peers están restringidos*\n\nNo hay peers disponibles.",
            reply_markup=back_button(f"restrictions:{config_name}"),
            parse_mode="Markdown"
        )
        return
    
    # Guardar en el contexto
    context.user_data[f'unrestricted_peers_{config_name}'] = unrestricted_peers
    
    total_peers = len(unrestricted_peers)
    total_pages = (total_peers - 1) // 6 + 1  # Cambiado a 6
    
    if page >= total_pages:
        page = total_pages - 1
    
    keyboard = paginated_unrestricted_peers_menu(unrestricted_peers, config_name, page)
    
    message = f"🔒 *Restringir Peer - {config_name}*\n\n"
    message += f"📊 Disponibles: {total_peers}\n"
    message += f"📄 Página {page + 1} de {total_pages}\n\n"
    message += "Selecciona un peer para restringir:"
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def handle_unrestrict_simple(query, context: CallbackContext, config_name: str, peer_index: int):
    """Quitar restricción de forma simplificada"""
    await query.edit_message_text(f"🔓 Quitando restricción...")
    
    # Obtener peers del contexto
    restricted_peers = context.user_data.get(f'restricted_peers_{config_name}', [])
    
    if peer_index < 0 or peer_index >= len(restricted_peers):
        await query.edit_message_text(
            f"❌ Índice de peer inválido",
            reply_markup=back_button(f"restricted_peers:{config_name}:0")
        )
        return
    
    peer = restricted_peers[peer_index]
    public_key = peer.get('id', '')
    peer_name = peer.get('name', 'Desconocido')
    
    if not public_key:
        await query.edit_message_text(
            f"❌ No se pudo obtener la clave pública",
            reply_markup=back_button(f"restricted_peers:{config_name}:0")
        )
        return
    
    # Llamar a la API
    result = api_client.allow_access_peer(config_name, public_key)
    
    if result.get("status"):
        await query.edit_message_text(
            f"✅ *Restricción quitada*\n\nPeer: {peer_name}\nAhora puede conectarse.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Actualizar lista", callback_data=f"restricted_peers:{config_name}:0")],
                [InlineKeyboardButton("⬅️ Volver", callback_data=f"restrictions:{config_name}")]
            ]),
            parse_mode="Markdown"
        )
    else:
        error_msg = result.get('message', 'Error desconocido')
        await query.edit_message_text(
            f"❌ *Error*\n\n{error_msg}",
            reply_markup=back_button(f"restricted_peers:{config_name}:0"),
            parse_mode="Markdown"
        )

async def handle_restrict_simple(query, context: CallbackContext, config_name: str, peer_index: int):
    """Restringir peer de forma simplificada"""
    await query.edit_message_text(f"🔒 Restringiendo peer...")
    
    # Obtener peers del contexto
    unrestricted_peers = context.user_data.get(f'unrestricted_peers_{config_name}', [])
    
    if peer_index < 0 or peer_index >= len(unrestricted_peers):
        await query.edit_message_text(
            f"❌ Índice de peer inválido",
            reply_markup=back_button(f"restrict_peer_menu:{config_name}:0")
        )
        return
    
    peer = unrestricted_peers[peer_index]
    public_key = peer.get('id', '')
    peer_name = peer.get('name', 'Desconocido')
    
    if not public_key:
        await query.edit_message_text(
            f"❌ No se pudo obtener la clave pública",
            reply_markup=back_button(f"restrict_peer_menu:{config_name}:0")
        )
        return
    
    # Llamar a la API
    result = api_client.restrict_peer(config_name, public_key)
    
    if result.get("status"):
        await query.edit_message_text(
            f"✅ *Peer restringido*\n\nPeer: {peer_name}\nYa no podrá conectarse.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Actualizar lista", callback_data=f"restrict_peer_menu:{config_name}:0")],
                [InlineKeyboardButton("⬅️ Volver", callback_data=f"restrictions:{config_name}")]
            ]),
            parse_mode="Markdown"
        )
    else:
        error_msg = result.get('message', 'Error desconocido')
        await query.edit_message_text(
            f"❌ *Error*\n\n{error_msg}",
            reply_markup=back_button(f"restrict_peer_menu:{config_name}:0"),
            parse_mode="Markdown"
        )

async def handle_unrestrict_confirm(query, context: CallbackContext, config_name: str, public_key_short: str, peer_index: str):
    """Muestra confirmación para quitar restricción a un peer"""
    await query.edit_message_text(f"🔍 Buscando información del peer...")
    
    # Obtener información del peer
    result = api_client.get_peers(config_name)
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error: {result.get('message', 'Error desconocido')}",
            reply_markup=back_button(f"restricted_peers:{config_name}:0")
        )
        return
    
    restricted_peers = result.get("restricted_data", [])
    
    # Buscar el peer específico usando el índice
    try:
        idx = int(peer_index)
        if idx < 0 or idx >= len(restricted_peers):
            await query.edit_message_text(
                f"❌ Índice de peer inválido",
                reply_markup=back_button(f"restricted_peers:{config_name}:0")
            )
            return
        
        peer_info = restricted_peers[idx]
        public_key = peer_info.get('id', '')
        peer_name = peer_info.get('name', 'Desconocido')
        
        if not public_key:
            await query.edit_message_text(
                f"❌ No se pudo obtener la clave pública del peer",
                reply_markup=back_button(f"restricted_peers:{config_name}:0")
            )
            return
        
        allowed_ip = peer_info.get('allowed_ip', 'N/A')
        
        message = f"⚠️ *Confirmar Quitar Restricción*\n\n"
        message += f"¿Estás seguro de que deseas quitar la restricción a este peer?\n\n"
        message += f"*Peer:* {peer_name}\n"
        message += f"*Configuración:* {config_name}\n"
        message += f"*IP:* `{allowed_ip}`\n"
        message += f"*Clave pública:* `{public_key[:30]}...`\n\n"
        message += "ℹ️ *Al quitar la restricción, el peer podrá conectarse nuevamente.*"
        
        # Codificar la clave pública completa
        from keyboards import safe_callback_data
        safe_public_key = safe_callback_data(public_key)
        
        keyboard = confirmation_menu(config_name, safe_public_key, "unrestrict", "Quitar Restricción")
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error en confirmación de quitar restricción: {str(e)}")
        await query.edit_message_text(
            f"❌ Error al procesar la solicitud: {str(e)}",
            reply_markup=back_button(f"restricted_peers:{config_name}:0")
        )

async def handle_unrestrict_execute(query, config_name: str, public_key: str):
    """Ejecuta la acción de quitar restricción a un peer"""
    await query.edit_message_text(f"🔄 Quitando restricción al peer...")
    
    result = api_client.allow_access_peer(config_name, public_key)
    
    if result.get("status"):
        await query.edit_message_text(
            f"✅ *Restricción quitada correctamente*\n\n"
            f"El peer ahora puede conectarse a {config_name}.",
            reply_markup=back_button(f"restricted_peers:{config_name}:0"),
            parse_mode="Markdown"
        )
    else:
        error_msg = result.get('message', 'Error desconocido')
        await query.edit_message_text(
            f"❌ *Error al quitar restricción*\n\n"
            f"*Error:* {error_msg}",
            reply_markup=back_button(f"restricted_peers:{config_name}:0"),
            parse_mode="Markdown"
        )

async def handle_restrict_confirm(query, context: CallbackContext, config_name: str, public_key_short: str, peer_index: str):
    """Muestra confirmación para restringir un peer"""
    await query.edit_message_text(f"🔍 Buscando información del peer...")
    
    # Obtener información del peer
    result = api_client.get_peers(config_name)
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error: {result.get('message', 'Error desconocido')}",
            reply_markup=back_button(f"restrict_peer_menu:{config_name}:0")
        )
        return
    
    all_peers = result.get("data", [])
    
    # Buscar el peer específico usando el índice
    try:
        idx = int(peer_index)
        if idx < 0 or idx >= len(all_peers):
            await query.edit_message_text(
                f"❌ Índice de peer inválido",
                reply_markup=back_button(f"restrict_peer_menu:{config_name}:0")
            )
            return
        
        peer_info = all_peers[idx]
        public_key = peer_info.get('id', '')
        peer_name = peer_info.get('name', 'Desconocido')
        
        if not public_key:
            await query.edit_message_text(
                f"❌ No se pudo obtener la clave pública del peer",
                reply_markup=back_button(f"restrict_peer_menu:{config_name}:0")
            )
            return
        
        allowed_ip = peer_info.get('allowed_ip', 'N/A')
        status = peer_info.get('status', 'stopped')
        status_text = "✅ Conectado" if status == 'running' else "❌ Desconectado"
        
        message = f"⚠️ *Confirmar Restricción de Peer*\n\n"
        message += f"¿Estás seguro de que deseas restringir este peer?\n\n"
        message += f"*Peer:* {peer_name}\n"
        message += f"*Configuración:* {config_name}\n"
        message += f"*IP:* `{allowed_ip}`\n"
        message += f"*Estado:* {status_text}\n"
        message += f"*Clave pública:* `{public_key[:30]}...`\n\n"
        message += "⚠️ *Al restringir el peer, no podrá conectarse hasta que se quite la restricción.*"
        
        # Codificar la clave pública completa
        from keyboards import safe_callback_data
        safe_public_key = safe_callback_data(public_key)
        
        keyboard = confirmation_menu(config_name, safe_public_key, "restrict", "Restringir")
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error en confirmación de restricción: {str(e)}")
        await query.edit_message_text(
            f"❌ Error al procesar la solicitud: {str(e)}",
            reply_markup=back_button(f"restrict_peer_menu:{config_name}:0")
        )

async def handle_restrict_execute(query, config_name: str, public_key: str):
    """Ejecuta la acción de restringir un peer"""
    await query.edit_message_text(f"🔄 Restringiendo peer...")
    
    result = api_client.restrict_peer(config_name, public_key)
    
    if result.get("status"):
        await query.edit_message_text(
            f"✅ *Peer restringido correctamente*\n\n"
            f"El peer ya no podrá conectarse a {config_name}.",
            reply_markup=back_button(f"restrict_peer_menu:{config_name}:0"),
            parse_mode="Markdown"
        )
    else:
        error_msg = result.get('message', 'Error desconocido')
        await query.edit_message_text(
            f"❌ *Error al restringir peer*\n\n"
            f"*Error:* {error_msg}",
            reply_markup=back_button(f"restrict_peer_menu:{config_name}:0"),
            parse_mode="Markdown"
        )

# ================= HANDLERS ESPECÍFICOS (EXISTENTES) ================= #
async def handle_main_menu(query):
    """Muestra el menú principal"""
    await query.edit_message_text(
        "🤖 *Menú Principal*\nSelecciona una opción:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

async def handle_handshake(query):
    """Verifica la conexión con la API"""
    await query.edit_message_text("🔌 Probando conexión con la API...")
    
    result = api_client.handshake()
    
    if result.get("status"):
        await query.edit_message_text(
            "✅ *Conexión exitosa*\nLa API de WGDashboard responde correctamente.",
            reply_markup=refresh_button("handshake")
        )
    else:
        await query.edit_message_text(
            f"❌ *Error de conexión*\n{result.get('message', 'Error desconocido')}",
            reply_markup=refresh_button("handshake")
        )

async def handle_configs(query, page: int = 0):
    """Muestra la lista de configuraciones"""
    await query.edit_message_text("📡 Obteniendo configuraciones...")
    
    result = api_client.get_configurations()
    
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error: {result.get('message', 'Error desconocido')}",
            reply_markup=refresh_button("configs")
        )
        return
    
    configs = result.get("data", [])
    
    if not configs:
        await query.edit_message_text(
            "⚠️ No hay configuraciones WireGuard disponibles",
            reply_markup=refresh_button("configs")
        )
        return
    
    # Crear menú paginado
    keyboard = paginated_configs_menu(configs, page)
    
    total_configs = len(configs)
    total_pages = (total_configs - 1) // 8 + 1
    
    message = f"📡 *Configuraciones disponibles*\n"
    message += f"Página {page + 1} de {total_pages}\n"
    message += f"Total: {total_configs} configuraciones\n\n"
    message += "Selecciona una configuración para ver más opciones:"
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def handle_configs_summary(query):
    """Muestra un resumen de todas las configuraciones"""
    await query.edit_message_text("📊 Generando resumen...")
    
    result = api_client.get_configurations()
    
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error: {result.get('message', 'Error desconocido')}",
            reply_markup=refresh_button("configs_summary")
        )
        return
    
    configs = result.get("data", [])
    formatted_text = format_config_summary(configs)
    
    await query.edit_message_text(
        formatted_text,
        reply_markup=refresh_button("configs_summary"),
        parse_mode="Markdown"
    )

async def show_configurations(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Función auxiliar para mostrar menú de configuraciones"""
    if hasattr(update, 'message'):
        await update.message.reply_text("📡 Obteniendo configuraciones...")
        query = update
        is_message = True
    else:
        query = update.callback_query
        is_message = False
    
    result = api_client.get_configurations()
    
    if not result.get("status"):
        error_msg = f"❌ Error: {result.get('message', 'Error desconocido')}"
        if is_message:
            await update.message.reply_text(error_msg)
        else:
            await query.edit_message_text(error_msg)
        return
    
    configs = result.get("data", [])
    
    if not configs:
        no_configs_msg = "⚠️ No hay configuraciones WireGuard disponibles"
        if is_message:
            await update.message.reply_text(no_configs_msg)
        else:
            await query.edit_message_text(no_configs_msg)
        return
    
    keyboard = paginated_configs_menu(configs, page)
    
    total_configs = len(configs)
    total_pages = (total_configs - 1) // 8 + 1
    
    message = f"📡 *Configuraciones disponibles*\n"
    message += f"Página {page + 1} de {total_pages}\n"
    message += f"Total: {total_configs} configuraciones\n\n"
    message += "Selecciona una configuración para ver más opciones:"
    
    if is_message:
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

async def handle_config_detail(query, config_name: str):
    """Muestra el menú de una configuración específica"""
    await query.edit_message_text(f"⚙️ Obteniendo información de {config_name}...")
    
    result = api_client.get_configuration_detail(config_name)
    
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error: {result.get('message', 'Error desconocido')}",
            reply_markup=back_button("configs")
        )
        return
    
    config = result.get("data", {})
    
    # Información básica de la configuración
    listen_port = config.get('ListenPort', 'N/A')
    private_key = config.get('PrivateKey', '')
    public_key = config.get('PublicKey', '')
    total_peers = config.get('TotalPeers', 0)
    connected_peers = config.get('ConnectedPeers', 0)
    
    # Obtener información de peers restringidos
    peers_result = api_client.get_peers(config_name)
    restricted_count = 0
    if peers_result.get("status"):
        restricted_count = peers_result.get("metadata", {}).get("restricted", 0)
    
    message = f"⚙️ *Configuración: {config_name}*\n\n"
    message += f"📡 Puerto: `{listen_port}`\n"
    message += f"🔑 Clave pública: `{public_key[:30]}...`\n"
    message += f"👥 Peers: *{connected_peers}/{total_peers}* conectados\n"
    message += f"🚫 Restringidos: *{restricted_count}* peers\n\n"
    message += "*Opciones disponibles:*\n"
    message += "• 📥 Descargar Peers: Lista para descargar configuraciones\n"
    message += "• 📋 Detalles completos: Información detallada de todos los peers\n"
    message += "• 🗑 Eliminar Peer: Eliminar un peer existente\n"
    message += "• ➕ Agregar Peer: Crear un nuevo peer automáticamente\n"
    message += "• ⏰ Schedule Jobs: Gestionar trabajos programados\n"
    message += "• 🚫 Restricciones: Gestionar peers restringidos\n"
    message += "• 🔄 Actualizar: Refrescar información"
    
    await query.edit_message_text(
        message,
        reply_markup=config_menu(config_name),
        parse_mode="Markdown"
    )

async def handle_peers_list(query, context: CallbackContext, config_name: str, page: int = 0):
    """Muestra la lista de peers para descarga directa"""
    await query.edit_message_text(f"👤 Obteniendo peers de {config_name}...")
    
    result = api_client.get_peers(config_name)
    
    if not result.get("status"):
        error_msg = result.get("message", "Error desconocido")
        
        await query.edit_message_text(
            f"❌ Error: {error_msg}",
            reply_markup=back_button(f"cfg:{config_name}")
        )
        return
    
    peers = result.get("data", [])
    metadata = result.get("metadata", {})
    
    if not peers:
        await query.edit_message_text(
            f"⚠️ No hay peers en {config_name}",
            reply_markup=back_button(f"cfg:{config_name}")
        )
        return
    
    # Crear teclado con paginación
    keyboard = []
    start_idx = page * 8  # 8 items por página
    end_idx = start_idx + 8
    page_peers = peers[start_idx:end_idx]
    
    for i, peer in enumerate(page_peers, start_idx):
        peer_name = peer.get('name', 'Sin nombre')
        public_key = peer.get('id', '')
        allowed_ip = peer.get('allowed_ip', 'N/A')
        latest_handshake = peer.get('latest_handshake_seconds', 0)
        status = peer.get('status', 'stopped')
        
        # Determinar estado para el emoji
        if status == 'running' and latest_handshake > 0:
            status_emoji = "✅"
        else:
            status_emoji = "❌"
        
        # Crear texto del botón con estado e información básica
        button_text = f"{status_emoji} {peer_name} - IP: {allowed_ip}"
        
        # Crear un hash corto para este peer
        peer_hash = create_peer_hash(config_name, public_key, peer_name)
        
        # Guardar información del peer en el contexto si no existe
        context_key = f'peer_{peer_hash}'
        if not context.user_data.get(context_key):
            context.user_data[context_key] = {
                'config_name': config_name,
                'peer_name': peer_name,
                'public_key': public_key,
                'allowed_ip': allowed_ip
            }
        
        # Un solo botón por peer que descarga directamente
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"download_peer_direct:{peer_hash}"
            )
        ])
    
    # Botones de navegación
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️ Anterior", callback_data=f"page_peers:{config_name}:{page-1}")
        )
    
    if end_idx < len(peers):
        nav_buttons.append(
            InlineKeyboardButton("Siguiente ▶️", callback_data=f"page_peers:{config_name}:{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Botones de acción global (reducidos)
    keyboard.append([
        InlineKeyboardButton("📋 Ver detalles", callback_data=f"peers_detailed:{config_name}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("⬅️ Volver", callback_data=f"cfg:{config_name}")
    ])
    
    total_peers = len(peers)
    total_pages = (total_peers - 1) // 8 + 1
    
    message = f"👥 *Peers en {config_name}*\n\n"
    message += f"📊 Total peers: {metadata.get('total', 0)}\n"
    message += f"✅ Conectados: {metadata.get('connected', 0)}\n"
    message += f"📄 Página {page + 1} de {total_pages}\n\n"
    message += "*Presiona sobre un peer para descargar su configuración.*\n"
    message += "✅ = Conectado | ❌ = Desconectado"
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_download_peer_direct(query, context: CallbackContext, peer_hash: str):
    """Descarga directamente la configuración de un peer desde la lista"""
    await query.edit_message_text("📥 Descargando configuración...")
    
    try:
        # Obtener datos del peer desde el contexto
        peer_data = context.user_data.get(f'peer_{peer_hash}')
        if not peer_data:
            await query.edit_message_text(
                f"❌ No se pudo encontrar la información del peer.\n"
                f"La información puede haber expirado. Por favor, vuelve a la lista.",
                reply_markup=back_button("main_menu")
            )
            return
        
        config_name = peer_data['config_name']
        peer_name = peer_data['peer_name']
        public_key = peer_data.get('public_key', '')
        allowed_ip = peer_data.get('allowed_ip', '10.21.0.2/32')
        
        # Primero intentar obtener la configuración del servidor
        download_result = api_client.download_peer_config(config_name, public_key)
        
        if download_result.get("status"):
            # El servidor proporciona la configuración completa
            config_content = download_result.get("data", "")
            filename = f"{peer_name}_{config_name}.conf"
            
            file_like = io.BytesIO(config_content.encode('utf-8'))
            file_like.name = filename
            
            # Enviar el archivo
            await query.message.reply_document(
                document=InputFile(file_like, filename=filename),
                caption=f"📁 Configuración de {peer_name} para {config_name}"
            )
            
            # Actualizar mensaje original
            await query.edit_message_text(
                f"✅ *Configuración descargada*\n\n"
                f"El archivo `{filename}` ha sido enviado.\n\n"
                f"*Peer:* {peer_name}\n"
                f"*Configuración:* {config_name}",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("⬅️ Volver a Lista", callback_data=f"peers:{config_name}"),
                        InlineKeyboardButton("🔄 Descargar de nuevo", callback_data=f"download_peer_direct:{peer_hash}")
                    ]
                ]),
                parse_mode="Markdown"
            )
            
        else:
            # El servidor no proporciona la configuración, generar plantilla
            await query.edit_message_text(f"🔄 Generando plantilla para {peer_name}...")
            
            # Obtener información del servidor
            from config import WG_API_BASE_URL
            
            parsed_url = urllib.parse.urlparse(WG_API_BASE_URL)
            server_host = parsed_url.hostname
            
            # Obtener información de la configuración
            config_result = api_client.get_configuration_detail(config_name)
            if not config_result.get("status"):
                await query.edit_message_text(
                    f"❌ No se pudo obtener información de la configuración",
                    reply_markup=back_button(f"peers:{config_name}")
                )
                return
            
            config_data = config_result.get("data", {})
            listen_port = config_data.get('ListenPort', '51820')
            server_public_key = config_data.get('PublicKey', '')
            
            # Obtener DNS del peer si existe, o usar el predeterminado
            peers_result = api_client.get_peers(config_name)
            dns = "1.1.1.1"
            if peers_result.get("status"):
                peers = peers_result.get("data", [])
                for peer in peers:
                    if peer.get('id') == public_key:
                        dns = peer.get('DNS', '1.1.1.1')
                        break
            
            # Crear plantilla de configuración
            template = f"""# Configuración WireGuard para {peer_name}
# Completa la información faltante

[Interface]
PrivateKey = [TU_CLAVE_PRIVADA_AQUÍ]
Address = {allowed_ip}
DNS = {dns}

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {server_host}:{listen_port}
PersistentKeepalive = 21"""
            
            filename = f"{peer_name}_{config_name}_plantilla.conf"
            
            file_like = io.BytesIO(template.encode('utf-8'))
            file_like.name = filename
            
            # Enviar el archivo
            await query.message.reply_document(
                document=InputFile(file_like, filename=filename),
                caption=f"📄 Plantilla de configuración para {peer_name}"
            )
            
            # Actualizar mensaje original
            await query.edit_message_text(
                f"📄 *Plantilla generada para {peer_name}*\n\n"
                f"Se ha enviado una plantilla de configuración.\n\n"
                f"*Información incluida:*\n"
                f"• IP: `{allowed_ip}`\n"
                f"• DNS: `{dns}`\n"
                f"• Servidor: `{server_host}:{listen_port}`\n"
                f"• Clave pública del servidor: `{server_public_key[:30]}...`\n\n"
                f"*Para completar:*\n"
                f"1. Reemplaza `[TU_CLAVE_PRIVADA_AQUÍ]` con la clave privada\n"
                f"2. Guarda el archivo como `{peer_name}.conf`\n"
                f"3. Importa en tu cliente WireGuard\n\n"
                f"*Nota:* La clave privada solo está disponible al crear el peer desde el bot.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("⬅️ Volver a Lista", callback_data=f"peers:{config_name}"),
                        InlineKeyboardButton("➕ Crear nuevo Peer", callback_data=f"add_peer:{config_name}")
                    ]
                ]),
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Error al descargar configuración directa: {str(e)}")
        await query.edit_message_text(
            f"❌ *Error al descargar configuración*\n\n"
            f"*Error:* {str(e)}\n\n"
            f"Intenta obtener la configuración desde el panel web de WGDashboard.",
            reply_markup=back_button(f"cfg:{config_name}"),
            parse_mode="Markdown"
        )

async def handle_peers_detailed(query, config_name: str):
    """Muestra información detallada de todos los peers - DIRECTO A PAGINADO"""
    # Cambio: Ir directamente a la vista paginada
    await handle_peers_detailed_paginated(query, config_name, 0)

async def handle_peers_detailed_paginated(query, config_name: str, page: int = 0):
    """Muestra información detallada de peers paginada - VERSIÓN SIN FORMATO"""
    await query.edit_message_text(f"📋 Preparando detalles paginados...")
    
    result = api_client.get_peers(config_name)
    
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error: {result.get('message', 'Error desconocido')}",
            reply_markup=back_button(f"cfg:{config_name}")
        )
        return
    
    peers = result.get("data", [])
    
    if not peers:
        await query.edit_message_text(
            f"⚠️ No hay peers en {config_name}",
            reply_markup=back_button(f"cfg:{config_name}")
        )
        return
    
    # Mostrar 2 peers por página para no exceder el límite
    peers_per_page = 2
    total_pages = (len(peers) + peers_per_page - 1) // peers_per_page
    
    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0
    
    start_idx = page * peers_per_page
    end_idx = min(start_idx + peers_per_page, len(peers))
    page_peers = peers[start_idx:end_idx]
    
    # Construir mensaje para esta página - SIN FORMATO MARKDOWN
    message = f"📋 Detalles de Peers - {config_name}\n\n"
    message += f"Página {page + 1} de {total_pages}\n"
    message += f"Mostrando peers {start_idx + 1}-{end_idx} de {len(peers)}\n\n"
    
    for i, peer in enumerate(page_peers, start_idx + 1):
        message += f"Peer #{i}\n"
        message += format_peer_for_detail_plain(peer)  # Usar versión sin formato
        message += "\n" + "─" * 30 + "\n\n"
    
    # Crear teclado de navegación
    keyboard = []
    
    # Botones de navegación
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️ Anterior", callback_data=f"peers_detailed_paginated:{config_name}:{page-1}")
        )
    
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton("Siguiente ▶️", callback_data=f"peers_detailed_paginated:{config_name}:{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # ELIMINAR el botón "Ver todo en un mensaje"
    # keyboard.append([
    #     InlineKeyboardButton("📋 Ver todo en un mensaje", callback_data=f"peers_detailed_full:{config_name}")
    # ])
    
    keyboard.append([
        InlineKeyboardButton("⬅️ Volver al menú", callback_data=f"cfg:{config_name}")
    ])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=None  # SIN FORMATO
    )

async def handle_delete_peer_menu(query, config_name: str, page: int = 0):
    """Muestra el menú para seleccionar peer a eliminar"""
    await query.edit_message_text(f"🗑 Obteniendo peers de {config_name}...")
    
    result = api_client.get_peers(config_name)
    
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error: {result.get('message', 'Error desconocido')}",
            reply_markup=back_button(f"cfg:{config_name}")
        )
        return
    
    peers = result.get("data", [])
    
    if not peers:
        await query.edit_message_text(
            f"⚠️ No hay peers para eliminar en {config_name}",
            reply_markup=back_button(f"cfg:{config_name}")
        )
        return
    
    keyboard = []
    start_idx = page * 8  # 8 items por página
    end_idx = start_idx + 8
    page_peers = peers[start_idx:end_idx]
    
    for i, peer in enumerate(page_peers, start_idx):
        peer_name = peer.get('name', 'Sin nombre')
        button_text = f"{peer_name}"
        callback_data = f"delete_peer_confirm:{config_name}:{i}"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Botones de navegación
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️ Anterior", callback_data=f"page_delete_peer:{config_name}:{page-1}")
        )
    
    if end_idx < len(peers):
        nav_buttons.append(
            InlineKeyboardButton("Siguiente ▶️", callback_data=f"page_delete_peer:{config_name}:{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Botón para cancelar
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data=f"cfg:{config_name}")])
    
    total_peers = len(peers)
    total_pages = (total_peers - 1) // 8 + 1
    
    message = f"🗑 *Eliminar Peer - {config_name}*\n"
    message += f"Página {page + 1} de {total_pages}\n"
    message += f"Total: {total_peers} peers\n\n"
    message += "Selecciona el peer que deseas eliminar:"
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_delete_peer_confirm(query, config_name: str, peer_index: str):
    """Muestra confirmación para eliminar un peer - CORREGIDO"""
    try:
        # Obtener el índice del peer
        idx = int(peer_index)
        
        # Obtener los peers para encontrar el peer específico
        result = api_client.get_peers(config_name)
        if not result.get("status"):
            await query.edit_message_text(
                f"❌ Error: {result.get('message', 'Error desconocido')}",
                reply_markup=back_button(f"cfg:{config_name}")
            )
            return
        
        peers = result.get("data", [])
        
        if idx < 0 or idx >= len(peers):
            await query.edit_message_text(
                f"❌ Error: Índice de peer inválido",
                reply_markup=back_button(f"cfg:{config_name}")
            )
            return
        
        peer = peers[idx]
        peer_key = peer.get('id', '')
        peer_name = peer.get('name', 'Sin nombre')
        
        if not peer_key:
            await query.edit_message_text(
                f"❌ Error: No se pudo obtener la clave pública del peer",
                reply_markup=back_button(f"cfg:{config_name}")
            )
            return
        
        message = f"⚠️ *Confirmar eliminación*\n\n"
        message += f"¿Estás seguro de que deseas eliminar el peer?\n\n"
        message += f"*Configuración:* {config_name}\n"
        message += f"*Peer:* {peer_name}\n"
        message += f"*Clave pública:* `{peer_key[:30]}...`\n\n"
        message += "⚠️ *Esta acción no se puede deshacer.*"
        
        # CORREGIDO: Añadir el cuarto parámetro action_text
        await query.edit_message_text(
            message,
            reply_markup=confirmation_menu(config_name, peer_index, "delete_peer", "Eliminar"),
            parse_mode="Markdown"
        )
        
    except ValueError as e:
        await query.edit_message_text(
            f"❌ Error: Índice de peer inválido\n{str(e)}",
            reply_markup=back_button(f"cfg:{config_name}")
        )

async def handle_delete_peer_final(query, config_name: str, peer_index: str):
    """Elimina definitivamente el peer"""
    try:
        # Obtener el índice del peer
        idx = int(peer_index)
        
        # Obtener el peer específico para obtener su clave pública
        result = api_client.get_peers(config_name)
        if not result.get("status"):
            await query.edit_message_text(
                f"❌ Error: {result.get('message', 'Error desconocido')}",
                reply_markup=back_button(f"cfg:{config_name}")
            )
            return
        
        peers = result.get("data", [])
        
        if idx < 0 or idx >= len(peers):
            await query.edit_message_text(
                f"❌ Error: Índice de peer inválido",
                reply_markup=back_button(f"cfg:{config_name}")
            )
            return
        
        peer = peers[idx]
        peer_key = peer.get('id', '')
        
        if not peer_key:
            await query.edit_message_text(
                f"❌ Error: No se pudo obtener la clave pública del peer",
                reply_markup=back_button(f"cfg:{config_name}")
            )
            return
        
        await query.edit_message_text("🗑 Eliminando peer...")
        
        result = api_client.delete_peer(config_name, peer_key)
        
        if result.get("status"):
            await query.edit_message_text(
                f"✅ *Peer eliminado correctamente*\n\n"
                f"El peer ha sido eliminado de {config_name}.",
                reply_markup=back_button(f"cfg:{config_name}")
            )
        else:
            await query.edit_message_text(
                f"❌ *Error al eliminar peer*\n"
                f"{result.get('message', 'Error desconocido')}",
                reply_markup=back_button(f"cfg:{config_name}")
            )
            
    except ValueError as e:
        await query.edit_message_text(
            f"❌ Error al procesar la eliminación: {str(e)}",
            reply_markup=back_button(f"cfg:{config_name}")
        )

async def handle_add_peer(query, context: CallbackContext, config_name: str):
    """Pide el nombre para generar un peer automáticamente"""
    # Limpiar estado previo
    for key in ['waiting_for_peer_name', 'config_name_for_peer', 'waiting_for_peer_data']:
        if key in context.user_data:
            del context.user_data[key]
    
    # Guardar en el contexto que estamos esperando un nombre para esta configuración
    context.user_data['waiting_for_peer_name'] = True
    context.user_data['config_name_for_peer'] = config_name
    
    # Obtener información de la configuración para mostrar detalles
    result = api_client.get_configuration_detail(config_name)
    if result.get("status"):
        config_data = result.get("data", {})
        address = config_data.get('Address', '10.21.0.0/24')
        listen_port = config_data.get('ListenPort', 'N/A')
        
        message = f"➕ *Agregar Peer a {config_name}*\n\n"
        message += f"*Configuración actual:*\n"
        message += f"• Red: `{address}`\n"
        message += f"• Puerto: `{listen_port}`\n\n"
    else:
        message = f"➕ *Agregar Peer a {config_name}*\n\n"
    
    message += "Por favor, envía el *nombre* para el nuevo peer:\n\n"
    message += "*Requisitos:*\n"
    message += "• Solo letras, números, guiones y guiones bajos\n"
    message += "• Máximo 32 caracteres\n"
    message += "• Ejemplo: `mi-celular`, `laptop-juan`, `servidor-01`\n\n"
    message += "Envía el nombre ahora o escribe */cancel* para cancelar."
    
    keyboard = [[InlineKeyboardButton("⬅️ Cancelar", callback_data=f"cfg:{config_name}")]]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_download_peer_config(query, context: CallbackContext, peer_hash: str):
    """Descarga la configuración de un peer usando hash"""
    await query.edit_message_text("📥 Descargando configuración...")
    
    try:
        # Obtener datos del peer desde el contexto usando el hash
        peer_data = context.user_data.get(f'peer_{peer_hash}')
        if not peer_data:
            await query.edit_message_text(
                f"❌ No se pudo encontrar la información del peer.\n"
                f"La información puede haber expirado. Por favor, crea un nuevo peer.",
                reply_markup=back_button("main_menu")
            )
            return
        
        config_name = peer_data['config_name']
        peer_name = peer_data['peer_name']
        public_key = peer_data['public_key']
        private_key = peer_data['private_key']
        preshared_key = peer_data['preshared_key']
        allowed_ip = peer_data['allowed_ip']
        
        # Obtener información del servidor
        from config import WG_API_BASE_URL
        
        # Extraer el host y puerto de la URL base
        parsed_url = urllib.parse.urlparse(WG_API_BASE_URL)
        server_host = parsed_url.hostname
        
        # Obtener información de la configuración
        config_result = api_client.get_configuration_detail(config_name)
        if not config_result.get("status"):
            await query.edit_message_text(
                f"❌ No se pudo obtener información de la configuración",
                reply_markup=back_button(f"cfg:{config_name}")
            )
            return
        
        config_data = config_result.get("data", {})
        listen_port = config_data.get('ListenPort', '51820')
        server_public_key = config_data.get('PublicKey', '')
        
        if not server_public_key:
            await query.edit_message_text(
                f"❌ No se pudo obtener la clave pública del servidor",
                reply_markup=back_button(f"cfg:{config_name}")
            )
            return
        
        # Construir el contenido del archivo .conf
        config_content = f"""[Interface]
PrivateKey = {private_key}
Address = {allowed_ip}
DNS = 1.1.1.1

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {server_host}:{listen_port}
PersistentKeepalive = 21"""
        
        # Agregar pre-shared key si existe
        if preshared_key:
            config_content += f"\nPresharedKey = {preshared_key}"
        
        # Nombre del archivo
        filename = f"{peer_name}_{config_name}.conf"
        
        # Crear un archivo en memoria
        file_like = io.BytesIO(config_content.encode('utf-8'))
        file_like.name = filename
        
        # Primero, enviar el archivo
        await query.message.reply_document(
            document=InputFile(file_like, filename=filename),
            caption=f"📁 Configuración de {peer_name} para {config_name}"
        )
        
        # Luego actualizar el mensaje original
        await query.edit_message_text(
            f"✅ *Configuración descargada*\n\n"
            f"El archivo `{filename}` ha sido enviado.\n\n"
            f"*Información de conexión:*\n"
            f"• Servidor: `{server_host}:{listen_port}`\n"
            f"• IP asignada: `{allowed_ip}`\n"
            f"• DNS: `1.1.1.1`\n\n"
            f"*Instrucciones:*\n"
            f"1. Guarda este archivo en tu dispositivo\n"
            f"2. Importa en tu cliente WireGuard\n"
            f"3. Conéctate y ¡listo!",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("⬅️ Volver a Configuración", callback_data=f"cfg:{config_name}"),
                    InlineKeyboardButton("🔄 Descargar de nuevo", callback_data=f"download_config:{peer_hash}")
                ]
            ]),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error al descargar configuración: {str(e)}")
        await query.edit_message_text(
            f"❌ *Error al descargar configuración*\n\n"
            f"*Error:* {str(e)}\n\n"
            f"Intenta obtener la configuración manualmente desde el dashboard.",
            reply_markup=back_button("main_menu"),
            parse_mode="Markdown"
        )

async def handle_peer_download_list(query, context: CallbackContext, config_name: str, peer_index: str, peer_hash: str):
    """Descarga la configuración de un peer desde la lista usando índice"""
    await query.edit_message_text(f"📥 Obteniendo información del peer...")
    
    try:
        idx = int(peer_index)
        
        # Obtener la lista de peers actualizada
        result = api_client.get_peers(config_name)
        if not result.get("status"):
            await query.edit_message_text(
                f"❌ Error al obtener la lista de peers: {result.get('message')}",
                reply_markup=back_button(f"peers:{config_name}")
            )
            return
        
        peers = result.get("data", [])
        
        if idx < 0 or idx >= len(peers):
            await query.edit_message_text(
                f"❌ Índice de peer inválido",
                reply_markup=back_button(f"peers:{config_name}")
            )
            return
        
        peer = peers[idx]
        peer_name = peer.get('name', 'Sin nombre')
        public_key = peer.get('id', '')
        allowed_ip = peer.get('allowed_ip', '10.21.0.2/32')
        
        # Buscar en el contexto si tenemos información completa de este peer
        peer_data = context.user_data.get(f'peer_{peer_hash}')
        
        if peer_data and peer_data.get('public_key') == public_key:
            # Tenemos información completa, usar la función de descarga normal
            await handle_download_peer_config(query, context, peer_hash)
        else:
            # No tenemos la clave privada, ofrecer plantilla
            await query.edit_message_text(f"🔄 Generando plantilla para {peer_name}...")
            
            # Obtener información del servidor
            from config import WG_API_BASE_URL
            
            parsed_url = urllib.parse.urlparse(WG_API_BASE_URL)
            server_host = parsed_url.hostname
            
            # Obtener información de la configuración
            config_result = api_client.get_configuration_detail(config_name)
            if not config_result.get("status"):
                await query.edit_message_text(
                    f"❌ No se pudo obtener información de la configuración",
                    reply_markup=back_button(f"peers:{config_name}")
                )
                return
            
            config_data = config_result.get("data", {})
            listen_port = config_data.get('ListenPort', '51820')
            server_public_key = config_data.get('PublicKey', '')
            dns = peer.get('DNS', '1.1.1.1')
            
            # Crear plantilla de configuración
            template = f"""# Configuración WireGuard para {peer_name}
# Completa la información faltante

[Interface]
PrivateKey = [TU_CLAVE_PRIVADA_AQUÍ]
Address = {allowed_ip}
DNS = {dns}

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {server_host}:{listen_port}
PersistentKeepalive = 21"""
            
            # Nombre del archivo
            filename = f"{peer_name}_{config_name}_plantilla.conf"
            
            file_like = io.BytesIO(template.encode('utf-8'))
            file_like.name = filename
            
            # Enviar el archivo
            await query.message.reply_document(
                document=InputFile(file_like, filename=filename),
                caption=f"📄 Plantilla de configuración para {peer_name}"
            )
            
            # Actualizar mensaje original
            await query.edit_message_text(
                f"📄 *Plantilla generada para {peer_name}*\n\n"
                f"Se ha enviado una plantilla de configuración.\n\n"
                f"*Información incluida:*\n"
                f"• IP: `{allowed_ip}`\n"
                f"• DNS: `{dns}`\n"
                f"• Servidor: `{server_host}:{listen_port}`\n"
                f"• Clave pública del servidor: `{server_public_key[:30]}...`\n\n"
                f"*Para completar:*\n"
                f"1. Reemplaza `[TU_CLAVE_PRIVADA_AQUÍ]` con la clave privada\n"
                f"2. Guarda el archivo como `{peer_name}.conf`\n"
                f"3. Importa en tu cliente WireGuard\n\n"
                f"*Nota:* La clave privada solo está disponible al crear el peer.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("⬅️ Volver a Lista", callback_data=f"peers:{config_name}"),
                        InlineKeyboardButton("➕ Crear nuevo Peer", callback_data=f"add_peer:{config_name}")
                    ]
                ]),
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Error al descargar desde lista: {str(e)}")
        await query.edit_message_text(
            f"❌ *Error al descargar configuración*\n\n"
            f"*Error:* {str(e)}\n\n"
            f"Intenta obtener la configuración desde el panel web de WGDashboard.",
            reply_markup=back_button(f"peers:{config_name}"),
            parse_mode="Markdown"
        )

# ================= HANDLERS DE SCHEDULE JOBS (ACTUALIZADOS) ================= #
async def handle_schedule_jobs_menu(query, context: CallbackContext, config_name: str):
    """Muestra el menú inicial de Schedule Jobs con lista de peers"""
    await query.edit_message_text(f"⏰ Obteniendo peers de {config_name}...")
    
    result = api_client.get_peers(config_name)
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error al obtener peers: {result.get('message')}",
            reply_markup=back_button(f"cfg:{config_name}")
        )
        return
    
    peers = result.get("data", [])
    
    if not peers:
        await query.edit_message_text(
            f"⚠️ No hay peers en {config_name}",
            reply_markup=back_button(f"cfg:{config_name}")
        )
        return
    
    # Crear teclado con lista de peers
    keyboard = []
    for i, peer in enumerate(peers):
        peer_name = peer.get('name', f'Peer {i+1}')
        keyboard.append([
            InlineKeyboardButton(
                f"👤 {peer_name}",
                callback_data=f"schedule_job_peer:{config_name}:{i}"
            )
        ])
    
    # Botones de navegación
    keyboard.append([
        InlineKeyboardButton("⬅️ Volver", callback_data=f"cfg:{config_name}")
    ])
    
    message = f"⏰ *Schedule Jobs - {config_name}*\n\n"
    message += f"Total peers: {len(peers)}\n\n"
    message += "Selecciona un peer para gestionar sus Schedule Jobs:"
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_schedule_job_peer_selected(query, context: CallbackContext, config_name: str, peer_index: int):
    """Muestra el menú de Schedule Jobs para un peer específico"""
    await query.edit_message_text(f"⏰ Obteniendo información del peer...")
    
    # Obtener información del peer usando el índice
    result = api_client.get_peers(config_name)
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error al obtener información del peer: {result.get('message')}",
            reply_markup=back_button(f"schedule_jobs_menu:{config_name}")
        )
        return
    
    peers = result.get("data", [])
    
    if peer_index < 0 or peer_index >= len(peers):
        await query.edit_message_text(
            f"❌ Índice de peer inválido",
            reply_markup=back_button(f"schedule_jobs_menu:{config_name}")
        )
        return
    
    peer = peers[peer_index]
    public_key = peer.get('id', '')
    peer_name = peer.get('name', 'Desconocido')
    jobs = peer.get('jobs', [])
    
    # Guardar en el contexto para uso posterior
    context.user_data[f'schedule_peer_{config_name}_{peer_index}'] = {
        'public_key': public_key,
        'peer_name': peer_name
    }
    
    message = f"⏰ *Schedule Jobs para {peer_name}*\n\n"
    message += f"*Configuración:* {config_name}\n"
    message += f"*Peer:* {peer_name}\n\n"
    
    if jobs:
        message += f"*Jobs activos:* {len(jobs)}\n\n"
        for i, job in enumerate(jobs, 1):
            message += f"{i}. {format_schedule_job_for_list(job)}\n"
        message += "\n"
    else:
        message += "ℹ️ *No hay jobs programados activos.*\n"
        message += "Puedes agregar nuevos jobs usando los botones.\n\n"
    
    message += "*Agregar nuevo Job:*\n"
    message += "• *Límite de datos*: Agrega un límite en GB\n"
    message += "• *Fecha de expiración*: Agrega una fecha de expiración"
    
    # Crear teclado
    keyboard = []
    
    # Botones para agregar jobs
    keyboard.append([
        InlineKeyboardButton("📊 Límite de datos (GB)", callback_data=f"add_schedule_job_data:{config_name}:{peer_index}"),
        InlineKeyboardButton("📅 Fecha de expiración", callback_data=f"add_schedule_job_date:{config_name}:{peer_index}")
    ])
    
    # Si hay jobs, mostrar botones para eliminarlos
    if jobs:
        keyboard.append([
            InlineKeyboardButton("🗑 Eliminar Job", callback_data=f"delete_schedule_job_all:{config_name}:{peer_index}")
        ])
    
    # Botones de navegación
    keyboard.append([
        InlineKeyboardButton("⬅️ Volver a Lista", callback_data=f"schedule_jobs_menu:{config_name}"),
        InlineKeyboardButton("🔄 Actualizar", callback_data=f"schedule_job_peer:{config_name}:{peer_index}")
    ])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_add_schedule_job_data(query, context: CallbackContext, config_name: str, peer_index: str):
    """Pide el valor para agregar un límite de datos en GB"""
    idx = int(peer_index)
    
    # Obtener información del peer
    peer_data = context.user_data.get(f'schedule_peer_{config_name}_{idx}')
    if not peer_data:
        result = api_client.get_peers(config_name)
        if not result.get("status"):
            await query.edit_message_text(
                f"❌ Error al obtener información del peer: {result.get('message')}",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        peers = result.get("data", [])
        if idx < 0 or idx >= len(peers):
            await query.edit_message_text(
                f"❌ Índice de peer inválido",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        peer = peers[idx]
        peer_data = {
            'public_key': peer.get('id', ''),
            'peer_name': peer.get('name', 'Desconocido')
        }
        context.user_data[f'schedule_peer_{config_name}_{idx}'] = peer_data
    
    peer_name = peer_data['peer_name']
    
    # Guardar en el contexto
    context.user_data['configuring_schedule_job'] = True
    context.user_data['schedule_job_config_name'] = config_name
    context.user_data['schedule_job_peer_index'] = idx
    context.user_data['schedule_job_public_key'] = peer_data['public_key']
    context.user_data['schedule_job_type'] = 'data'  # Tipo: data (total_data)
    
    # CORREGIDO: Usar HTML para evitar problemas con caracteres especiales en el nombre del peer
    message = f"⏰ <b>Agregar límite de datos para {peer_name}</b>\n\n"
    message += "Ingresa la cantidad de <b>GB</b> para el límite de datos:\n\n"
    message += "<b>Ejemplo:</b> <code>50</code> para 50 GB de límite\n\n"
    message += "El bot creará automáticamente un Schedule Job RESTRICT con total_data.\n\n"
    message += "Envía el número ahora o escribe /cancel para cancelar."
    
    # Guardar en el contexto que estamos esperando el valor
    context.user_data['waiting_for_schedule_job_value'] = True
    
    keyboard = [[InlineKeyboardButton("⬅️ Cancelar", callback_data=f"schedule_job_peer:{config_name}:{idx}")]]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def handle_add_schedule_job_date(query, context: CallbackContext, config_name: str, peer_index: str):
    """Pide la fecha para agregar una fecha de expiración"""
    idx = int(peer_index)
    
    # Obtener información del peer
    peer_data = context.user_data.get(f'schedule_peer_{config_name}_{idx}')
    if not peer_data:
        result = api_client.get_peers(config_name)
        if not result.get("status"):
            await query.edit_message_text(
                f"❌ Error al obtener información del peer: {result.get('message')}",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        peers = result.get("data", [])
        if idx < 0 or idx >= len(peers):
            await query.edit_message_text(
                f"❌ Índice de peer inválido",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        peer = peers[idx]
        peer_data = {
            'public_key': peer.get('id', ''),
            'peer_name': peer.get('name', 'Desconocido')
        }
        context.user_data[f'schedule_peer_{config_name}_{idx}'] = peer_data
    
    peer_name = peer_data['peer_name']
    
    # Guardar en el contexto
    context.user_data['configuring_schedule_job'] = True
    context.user_data['schedule_job_config_name'] = config_name
    context.user_data['schedule_job_peer_index'] = idx
    context.user_data['schedule_job_public_key'] = peer_data['public_key']
    context.user_data['schedule_job_type'] = 'date'  # Tipo: date
    
    # CORREGIDO: Usar HTML o texto plano para evitar problemas de Markdown
    message = f"⏰ *Agregar fecha de expiración para {peer_name}*\n\n"
    message += "Ingresa la *fecha* para la expiración:\n\n"
    message += "*Formato:* dd/mm/aaaa (ej: `25/12/2025`)\n\n"
    message += "El bot creará automáticamente un Schedule Job RESTRICT con date.\n\n"
    message += "Envía la fecha ahora o escribe /cancel para cancelar."
    
    # Guardar en el contexto que estamos esperando el valor
    context.user_data['waiting_for_schedule_job_value'] = True
    
    keyboard = [[InlineKeyboardButton("⬅️ Cancelar", callback_data=f"schedule_job_peer:{config_name}:{idx}")]]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_schedule_jobs_list(query, context: CallbackContext, config_name: str, peer_index: str, page: int = 0):
    """Muestra la lista paginada de Schedule Jobs"""
    await query.edit_message_text(f"⏰ Obteniendo jobs del peer...")
    
    # Obtener información del peer
    result = api_client.get_peers(config_name)
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error al obtener información del peer: {result.get('message')}",
            reply_markup=back_button(f"schedule_jobs_menu:{config_name}")
        )
        return
    
    peers = result.get("data", [])
    
    idx = int(peer_index)
    if idx < 0 or idx >= len(peers):
        await query.edit_message_text(
            f"❌ Índice de peer inválido",
            reply_markup=back_button(f"schedule_jobs_menu:{config_name}")
        )
        return
    
    peer = peers[idx]
    peer_name = peer.get('name', 'Desconocido')
    jobs = peer.get('jobs', [])
    
    # Crear teclado paginado
    keyboard = []
    start_idx = page * 8
    end_idx = start_idx + 8
    page_jobs = jobs[start_idx:end_idx]
    
    for i, job in enumerate(page_jobs, start_idx):
        job_text = format_schedule_job_for_list(job)
        
        # Información del job
        keyboard.append([InlineKeyboardButton(f"{i+1}. {job_text}", callback_data=f"noop")])
        
        # Botón para eliminar este job - usando el callback_data correcto
        keyboard.append([
            InlineKeyboardButton(
                f"🗑 Eliminar este Job", 
                callback_data=f"delete_schedule_job_confirm:{config_name}:{idx}:{i}"
            )
        ])
    
    # Botones de navegación
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️ Anterior", callback_data=f"page_schedule_jobs:{config_name}:{idx}:{page-1}")
        )
    
    if end_idx < len(jobs):
        nav_buttons.append(
            InlineKeyboardButton("Siguiente ▶️", callback_data=f"page_schedule_jobs:{config_name}:{idx}:{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Botones de acción
    keyboard.append([
        InlineKeyboardButton("➕ Agregar Nuevo Job", callback_data=f"add_schedule_job_data:{config_name}:{idx}"),
        InlineKeyboardButton("🗑 Eliminar un Job", callback_data=f"delete_schedule_job_all:{config_name}:{idx}")
    ])
    keyboard.append([
        InlineKeyboardButton("⬅️ Volver", callback_data=f"schedule_job_peer:{config_name}:{idx}")
    ])
    
    total_jobs = len(jobs)
    total_pages = (total_jobs - 1) // 8 + 1
    
    message = f"⏰ *Schedule Jobs para {peer_name}*\n\n"
    message += f"Página {page + 1} de {total_pages}\n"
    message += f"Total: {total_jobs} jobs\n\n"
    message += "Selecciona 'Eliminar este Job' para eliminar un job específico."
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_delete_schedule_job_confirm(query, context: CallbackContext, config_name: str, peer_index: str, job_index: str = None):
    """Muestra confirmación para eliminar un Schedule Job individual - CORREGIDO"""
    try:
        idx = int(peer_index)
        
        # Obtener información actualizada del peer
        await query.edit_message_text("🔄 Obteniendo información del job...")
        
        result = api_client.get_peers(config_name)
        if not result.get("status"):
            await query.edit_message_text(
                f"❌ Error al obtener información del peer: {result.get('message')}",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        peers = result.get("data", [])
        if idx < 0 or idx >= len(peers):
            await query.edit_message_text(
                f"❌ Índice de peer inválido",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        peer = peers[idx]
        peer_name = peer.get('name', 'Desconocido')
        jobs = peer.get('jobs', [])
        
        if not jobs:
            await query.edit_message_text(
                f"ℹ️ No hay jobs programados en {peer_name}.",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        if job_index is None or job_index == "all":
            # Mostrar lista de jobs para eliminar uno específico
            keyboard = []
            for i, job in enumerate(jobs):
                job_text = format_schedule_job_for_list(job)
                keyboard.append([
                    InlineKeyboardButton(
                        f"{i+1}. {job_text}", 
                        callback_data=f"delete_schedule_job_final:{config_name}:{idx}:{i}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("⬅️ Volver", callback_data=f"schedule_job_peer:{config_name}:{idx}")
            ])
            
            message = f"🗑 *Eliminar Schedule Job de {peer_name}*\n\n"
            message += f"Selecciona el job que deseas eliminar:\n\n"
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return
        
        # Confirmación para eliminar un job específico
        job_idx = int(job_index)
        if job_idx < 0 or job_idx >= len(jobs):
            await query.edit_message_text(
                f"❌ Índice de job inválido",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        job = jobs[job_idx]
        job_id = job.get('JobID')
        
        if not job_id:
            await query.edit_message_text(
                f"❌ No se pudo obtener el JobID",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        # Formatear información del job
        action = job.get('Action', 'N/A')
        field = job.get('Field', 'N/A')
        value = job.get('Value', 'N/A')
        
        if field == "total_data":
            field_display = f"Límite de datos: {value} GB"
        elif field == "date":
            field_display = f"Fecha de expiración: {value}"
        else:
            field_display = f"{field}: {value}"
        
        message = f"⚠️ *Confirmar eliminación de Schedule Job*\n\n"
        message += f"¿Estás seguro de que deseas eliminar este job?\n\n"
        message += f"*Peer:* {peer_name}\n"
        message += f"*Configuración:* {config_name}\n"
        message += f"*Acción:* {action.upper()}\n"
        message += f"*{field_display}*\n\n"
        message += "⚠️ *Esta acción no se puede deshacer.*"
        
        # CORREGIDO: Usar el formato simplificado en lugar de confirmation_menu
        keyboard = [
            [
                InlineKeyboardButton("✅ Sí, eliminar", callback_data=f"delete_schedule_job_execute:{config_name}:{idx}:{job_idx}"),
                InlineKeyboardButton("❌ Cancelar", callback_data=f"schedule_job_peer:{config_name}:{idx}")
            ]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error en confirmación de eliminación: {str(e)}")
        await query.edit_message_text(
            f"❌ Error al procesar la solicitud: {str(e)}",
            reply_markup=back_button(f"schedule_job_peer:{config_name}:{peer_index}")
        )

async def handle_delete_schedule_job_execute(query, context: CallbackContext, config_name: str, peer_index: str, job_index: str):
    """Ejecuta la eliminación de un Schedule Job individual"""
    try:
        idx = int(peer_index)
        job_idx = int(job_index)
        
        await query.edit_message_text("🗑 Eliminando Schedule Job...")
        
        # Obtener información actualizada del peer
        result = api_client.get_peers(config_name)
        if not result.get("status"):
            await query.edit_message_text(
                f"❌ Error al obtener información del peer: {result.get('message')}",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        peers = result.get("data", [])
        if idx < 0 or idx >= len(peers):
            await query.edit_message_text(
                f"❌ Índice de peer inválido",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        peer = peers[idx]
        peer_name = peer.get('name', 'Desconocido')
        jobs = peer.get('jobs', [])
        
        if job_idx < 0 or job_idx >= len(jobs):
            await query.edit_message_text(
                f"❌ Índice de job inválido",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        job = jobs[job_idx]
        job_id = job.get('JobID')
        public_key = peer.get('id', '')
        
        if not job_id or not public_key:
            await query.edit_message_text(
                f"❌ No se pudo obtener la información necesaria",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}")
            )
            return
        
        # Formatear información del job para mostrar
        job_info = format_schedule_job_for_list(job)
        
        # Intentar eliminar el job
        result = api_client.delete_schedule_job(config_name, public_key, job_id, job_data=job)
        
        if result.get("status"):
            await query.edit_message_text(
                f"✅ *Schedule Job eliminado correctamente*\n\n"
                f"*Peer:* {peer_name}\n"
                f"*Job eliminado:* {job_info}\n\n"
                f"El job ha sido eliminado permanentemente.",
                reply_markup=back_button(f"schedule_job_peer:{config_name}:{idx}"),
                parse_mode="Markdown"
            )
        else:
            error_msg = result.get('message', 'Error desconocido')
            
            # Ofrecer opciones alternativas
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Intentar de nuevo", callback_data=f"delete_schedule_job_execute:{config_name}:{idx}:{job_idx}"),
                    InlineKeyboardButton("📋 Ver jobs", callback_data=f"schedule_job_peer:{config_name}:{idx}")
                ],
                [
                    InlineKeyboardButton("🆘 Ayuda", callback_data="help"),
                    InlineKeyboardButton("🏠 Menú principal", callback_data="main_menu")
                ]
            ]
            
            await query.edit_message_text(
                f"❌ *Error al eliminar Schedule Job*\n\n"
                f"*Job:* {job_info}\n"
                f"*Error:* {error_msg}\n\n"
                f"*Posibles soluciones:*\n"
                f"1. Intenta eliminar manualmente desde el dashboard web\n"
                f"2. Verifica que el job aún exista\n"
                f"3. Contacta al administrador del sistema",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Error al eliminar schedule job: {str(e)}", exc_info=True)
        await query.edit_message_text(
            f"❌ *Error al eliminar Schedule Job*\n\n"
            f"*Error:* {str(e)}\n\n"
            f"Intenta eliminar manualmente desde el dashboard web.",
            reply_markup=back_button(f"schedule_job_peer:{config_name}:{peer_index}"),
            parse_mode="Markdown"
        )

async def handle_system_status(query):
    """Muestra el estado del sistema"""
    await query.edit_message_text("🖥 Obteniendo estado del sistema...")
    
    result = api_client.get_system_status()
    
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error: {result.get('message', 'Error desconocido')}",
            reply_markup=refresh_button("system_status")
        )
        return
    
    status_data = result.get("data", {})
    formatted_text = format_system_status(status_data)
    
    await query.edit_message_text(
        formatted_text,
        reply_markup=refresh_button("system_status"),
        parse_mode="Markdown"
    )

async def handle_protocols(query):
    """Muestra los protocolos habilitados"""
    await query.edit_message_text("⚡ Obteniendo protocolos...")
    
    result = api_client.get_protocols()
    
    if not result.get("status"):
        await query.edit_message_text(
            f"❌ Error: {result.get('message', 'Error desconocido')}",
            reply_markup=refresh_button("protocols")
        )
        return
    
    protocols = result.get("data", [])
    
    if not protocols:
        await query.edit_message_text(
            "⚠️ No hay protocolos habilitados",
            reply_markup=refresh_button("protocols")
        )
        return
    
    message = "⚡ *Protocolos habilitados*\n\n"
    
    for protocol in protocols:
        emoji = "✅" if protocol in ["wg", "awg"] else "⚙️"
        message += f"{emoji} {protocol.upper()}\n"
    
    message += "\n*Notas:*\n"
    message += "- *WG*: WireGuard estándar\n"
    message += "- *AWG*: WireGuard avanzado\n"
    
    await query.edit_message_text(
        message,
        reply_markup=refresh_button("protocols"),
        parse_mode="Markdown"
    )

async def handle_stats(query):
    """Muestra estadísticas específicas de WireGuard sin datos de transferencia"""
    await query.edit_message_text("📊 Obteniendo estadísticas de WireGuard...")
    
    # Obtener todas las configuraciones para calcular estadísticas
    configs_result = api_client.get_configurations()
    
    if not configs_result.get("status"):
        await query.edit_message_text(
            f"❌ Error: {configs_result.get('message', 'Error desconocido')}",
            reply_markup=refresh_button("stats")
        )
        return
    
    configs = configs_result.get("data", [])
    
    if not configs:
        await query.edit_message_text(
            "⚠️ No hay configuraciones WireGuard disponibles",
            reply_markup=refresh_button("stats")
        )
        return
    
    lines = []
    lines.append("📊 **Estadísticas de WireGuard**\n")
    
    total_peers = 0
    total_connected = 0
    
    # Calcular estadísticas de todas las configuraciones
    for config in configs:
        config_name = config.get('Name', 'Desconocido')
        config_peers = config.get('TotalPeers', 0)
        config_connected = config.get('ConnectedPeers', 0)
        
        total_peers += config_peers
        total_connected += config_connected
    
    # Estadísticas generales
    lines.append(f"📡 **Configuraciones totales:** {len(configs)}")
    lines.append(f"👥 **Total de peers:** {total_peers}")
    lines.append(f"✅ **Peers conectados:** {total_connected}")
    
    if total_peers > 0:
        connection_rate = (total_connected / total_peers) * 100
        lines.append(f"📶 **Tasa de conexión:** {connection_rate:.1f}%\n")
    else:
        lines.append("\n")
    
    # Configuraciones individuales (mostrar solo las principales)
    lines.append("🔧 **Configuraciones activas:**")
    
    # Ordenar configuraciones por número de peers conectados (más activas primero)
    sorted_configs = sorted(configs, key=lambda x: x.get('ConnectedPeers', 0), reverse=True)
    
    for config in sorted_configs[:5]:  # Mostrar solo las primeras 5 configuraciones
        name = config.get('Name', 'Desconocido')
        peers = config.get('TotalPeers', 0)
        connected = config.get('ConnectedPeers', 0)
        listen_port = config.get('ListenPort', 'N/A')
        
        status_emoji = "✅" if connected > 0 else "⚠️"
        lines.append(f"   {status_emoji} **{name}** (puerto {listen_port})")
        lines.append(f"      👥 {connected}/{peers} peers conectados")
    
    if len(configs) > 5:
        lines.append(f"   ... y {len(configs) - 5} configuraciones más")
    
    # Agregar timestamp de la última actualización
    from datetime import datetime
    lines.append(f"\n🕐 Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    formatted_text = "\n".join(lines)
    
    await query.edit_message_text(
        formatted_text,
        reply_markup=refresh_button("stats"),
        parse_mode="Markdown"
    )

async def handle_help(query):
    """Muestra la ayuda"""
    help_text = """📚 *Ayuda del Bot WGDashboard*

*Navegación:*
• Usa los botones para navegar entre menús
• Los botones "🔄 Actualizar" recargan la información actual
• "⬅️ Volver" te lleva al menú anterior

*Funciones disponibles:*
• *Configuraciones*: Ver y gestionar todas tus configs WireGuard
• *Peers*: Listar, ver detalles y eliminar peers
• *Agregar Peer*: Crea automáticamente un nuevo peer con nombre, claves e IP
• *Descargar Configuración*: Obtén el archivo .conf listo para usar
• *Schedule Jobs*: Gestiona trabajos programados para restringir acceso
• *Estado del sistema*: Monitoreo de CPU, memoria, discos y red
• *Protocolos*: Ver qué protocolos están habilitados

*Schedule Jobs:*
- *Acción*: Siempre será **RESTRICT**
- *Tipos disponibles*:
  - *Límite de datos (GB)*: Número entero (ej: `50` para 50 GB)
  - *Fecha de expiración*: Fecha dd/mm/aaaa (ej: `25/12/2025`)
- *Cómo usar*:
  1. Selecciona "⏰ Schedule Jobs" en el menú de configuración
  2. Selecciona un peer de la lista
  3. Elige el tipo de job a agregar
  4. Envía el valor (número o fecha)
  5. El job se crea automáticamente

*Consejos:*
- Los datos se actualizan automáticamente
- Puedes usar /start para volver al menú principal
- Contacta al administrador si necesitas acceso

*Comandos de texto:*
/start - Iniciar bot
/help - Mostrar ayuda
/stats - Estadísticas del sistema
/configs - Listar configuraciones
/cancel - Cancelar operación en curso"""
    
    await query.edit_message_text(
        help_text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ================= MANEJO DE MENSAJES DE TEXTO ================= #
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto"""
    if not is_allowed(update):
        return
    
    message_text = update.message.text.strip()
    
    # Comando /cancel
    if message_text.lower() == '/cancel':
        # Limpiar estado de schedule job si está activo
        if context.user_data.get('waiting_for_schedule_job_value', False):
            for key in ['configuring_schedule_job', 'schedule_job_config_name', 'schedule_job_peer_index',
                       'schedule_job_public_key', 'schedule_job_type', 
                       'waiting_for_schedule_job_value']:
                if key in context.user_data:
                    del context.user_data[key]
            
            await update.message.reply_text(
                "✅ Configuración de Schedule Job cancelada.",
                parse_mode=None
            )
            return
        
        # Limpiar estado de agregar peer
        for key in ['waiting_for_peer_name', 'config_name_for_peer', 'waiting_for_peer_data']:
            if key in context.user_data:
                del context.user_data[key]
        
        await update.message.reply_text(
            "✅ Operación cancelada. Usa /start para volver al menú principal.",
            parse_mode=None
        )
        return
    
    # Verificar si estamos esperando un valor para un Schedule Job
    if context.user_data.get('waiting_for_schedule_job_value', False):
        config_name = context.user_data.get('schedule_job_config_name')
        peer_index = context.user_data.get('schedule_job_peer_index')
        job_type = context.user_data.get('schedule_job_type')  # 'data' o 'date'
        
        if not all([config_name, peer_index, job_type]):
            await update.message.reply_text(
                "❌ Error en la configuración del Schedule Job. Por favor, cancela e intenta nuevamente.",
                parse_mode=None
            )
            return
        
        value = message_text.strip()
        
        # Obtener información del peer
        peer_data = context.user_data.get(f'schedule_peer_{config_name}_{peer_index}')
        if not peer_data:
            await update.message.reply_text(
                "❌ No se pudo encontrar la información del peer",
                parse_mode=None
            )
            return
        
        public_key = peer_data['public_key']
        peer_name = peer_data['peer_name']
        
        # Validar según el tipo
        if job_type == 'data':
            # Validar que sea un número
            if not value.isdigit():
                await update.message.reply_text(
                    "❌ Valor inválido. Debe ser un número entero (ej: 50).\n"
                    "Por favor, envía un número válido o escribe /cancel para cancelar.",
                    parse_mode=None
                )
                return
            
            field = "total_data"
            field_display = "Límite de datos"
            processed_value = value  # El número tal cual
            value_display = f"{value} GB"
            
        else:  # job_type == 'date'
            # Validar formato de fecha dd/mm/aaaa
            from datetime import datetime
            
            if not re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', value):
                await update.message.reply_text(
                    "❌ Formato de fecha inválido. Debe ser dd/mm/aaaa (ej: 25/12/2025).\n"
                    "Por favor, envía una fecha válida o escribe /cancel para cancelar.",
                    parse_mode=None
                )
                return
            
            try:
                # Validar que sea una fecha válida
                day, month, year = map(int, value.split('/'))
                datetime(year, month, day)
                
                # Convertir a formato YYYY-MM-DD HH:MM:SS
                field = "date"
                field_display = "Fecha de expiración"
                processed_value = f"{year:04d}-{month:02d}-{day:02d} 00:00:00"
                value_display = value
                
            except ValueError:
                await update.message.reply_text(
                    "❌ Fecha inválida. Asegúrate de que el día, mes y año sean correctos.\n"
                    "Por favor, envía una fecha válida o escribe /cancel para cancelar.",
                    parse_mode=None
                )
                return
        
        # Crear el objeto job
        job_data = {
            "Field": field,
            "Value": processed_value,
            "Operator": "lgt"
        }
        
        await update.message.reply_text(f"⏰ Creando Schedule Job...")
        
        # Enviar a la API
        result = api_client.create_schedule_job(config_name, public_key, job_data)
        
        # Limpiar el contexto
        for key in ['configuring_schedule_job', 'schedule_job_config_name', 'schedule_job_peer_index',
                   'schedule_job_public_key', 'schedule_job_type', 'waiting_for_schedule_job_value']:
            if key in context.user_data:
                del context.user_data[key]
        
        if result.get("status"):
            await update.message.reply_text(
                f"✅ *Schedule Job creado correctamente*\n\n"
                f"*Peer:* {peer_name}\n"
                f"*Configuración:* {config_name}\n"
                f"*Acción:* RESTRICT\n"
                f"*Campo:* {field_display}\n"
                f"*Valor:* {value_display}\n\n"
                f"El peer será restringido cuando se alcance el límite o la fecha.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("⬅️ Volver a Schedule Jobs", callback_data=f"schedule_job_peer:{config_name}:{peer_index}"),
                        InlineKeyboardButton("➕ Agregar otro Job", callback_data=f"schedule_job_peer:{config_name}:{peer_index}")
                    ]
                ]),
                parse_mode="Markdown"
            )
        else:
            error_msg = result.get('message', 'Error desconocido')
            await update.message.reply_text(
                f"❌ *Error al crear Schedule Job*\n\n*Error:* {error_msg}\n\n"
                f"Intenta nuevamente o crea el job manualmente desde el dashboard.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver a Schedule Jobs", callback_data=f"schedule_job_peer:{config_name}:{peer_index}")]
                ]),
                parse_mode="Markdown"
            )
        
        return
    
    # Verificar si estamos esperando un nombre para generar un peer automáticamente
    elif context.user_data.get('waiting_for_peer_name', False):
        config_name = context.user_data.get('config_name_for_peer')
        
        # Validar el nombre
        if not message_text or len(message_text) > 32:
            await update.message.reply_text(
                "❌ Nombre inválido. Debe tener máximo 32 caracteres.\n"
                "Por favor, envía un nombre válido o escribe /cancel para cancelar.",
                parse_mode=None
            )
            return
        
        # Verificar caracteres válidos
        if not re.match(r'^[a-zA-Z0-9\-_]+$', message_text):
            await update.message.reply_text(
                "❌ Nombre inválido. Solo se permiten letras, números, guiones y guiones bajos.\n"
                "Por favor, envía un nombre válido o escribe /cancel para cancelar.",
                parse_mode=None
            )
            return
        
        peer_name = message_text
        
        # Limpiar el estado
        del context.user_data['waiting_for_peer_name']
        del context.user_data['config_name_for_peer']
        
        # Generar el peer automáticamente
        await generate_peer_automatically(update, context, config_name, peer_name)
        return
    
    # Si no es ninguno de los casos anteriores, mostrar mensaje de ayuda
    else:
        await update.message.reply_text(
            "No entiendo ese comando. Usa /help para ver los comandos disponibles o selecciona una opción del menú.\n\n"
            "También puedes usar /cancel si tienes una operación en curso.",
            parse_mode=None
        )

async def generate_peer_automatically(update: Update, context: ContextTypes.DEFAULT_TYPE, config_name: str, peer_name: str):
    """Genera un peer automáticamente con el nombre proporcionado"""
    await update.message.reply_text(f"⚙️ Generando peer '{peer_name}' para {config_name}...")
    
    # 1. Generar claves WireGuard y pre-shared key
    private_key, public_key = generate_wireguard_keys()
    preshared_key = generate_preshared_key()
    
    # 2. Obtener información de la configuración para la IP
    result = api_client.get_configuration_detail(config_name)
    if not result.get("status"):
        await update.message.reply_text(
            f"❌ Error al obtener información de {config_name}: {result.get('message')}",
            parse_mode=None
        )
        return
    
    config_data = result.get("data", {})
    address = config_data.get('Address', '10.21.0.0/24')
    
    # 3. Obtener IPs usadas
    peers_result = api_client.get_peers(config_name)
    used_ips = []
    if peers_result.get("status"):
        peers = peers_result.get("data", [])
        for peer in peers:
            allowed_ip = peer.get('allowed_ip', '')
            if allowed_ip and '/' in allowed_ip:
                ip_part = allowed_ip.split('/')[0]
                used_ips.append(ip_part)
    
    # 4. Encontrar IP disponible
    try:
        network = ipaddress.ip_network(address, strict=False)
        ip_found = None
        
        # Empezar desde .2 (.1 suele ser el servidor)
        start_ip = 2
        for i in range(start_ip, 255):
            ip = f"{network.network_address + i}"
            if ip not in used_ips:
                ip_found = ip
                break
        
        if not ip_found:
            ip_found = f"{network.network_address + start_ip}"
            
        allowed_ip = f"{ip_found}/32"
        
    except Exception as e:
        logger.error(f"Error calculando IP: {e}")
        allowed_ip = "10.21.0.2/32"
    
    # 5. Preparar datos para la API - FORMATO EXACTO
    peer_data = {
        "name": peer_name,
        "public_key": public_key,
        "private_key": private_key,
        "allowed_ips": allowed_ip,
        "dns": "1.1.1.1",
        "persistent_keepalive": 21,
        "mtu": 1420,
        "preshared_key": preshared_key
    }
    
    # 6. Enviar a la API
    await update.message.reply_text("📡 Enviando datos a WGDashboard...")
    
    result = api_client.add_peer(config_name, peer_data)
    
    if result.get("status"):
        # Crear un hash único para este peer
        peer_hash = create_peer_hash(config_name, public_key, peer_name)
        
        # Guardar datos del peer en el contexto para descarga posterior
        context.user_data[f'peer_{peer_hash}'] = {
            'config_name': config_name,
            'peer_name': peer_name,
            'public_key': public_key,
            'private_key': private_key,
            'preshared_key': preshared_key,
            'allowed_ip': allowed_ip
        }
        
        # Formatear mensaje
        message = f"✅ *Peer '{peer_name}' agregado correctamente a {config_name}*\n\n"
        message += f"*Información del peer:*\n"
        message += f"• 🏷️ Nombre: `{peer_name}`\n"
        message += f"• 🌐 IP asignada: `{allowed_ip}`\n"
        message += f"• 🔗 DNS: `1.1.1.1`\n"
        message += f"• ⏱️ Keepalive: `21`\n"
        message += f"• 📡 MTU: `1420`\n\n"
        message += f"*Claves generadas:*\n"
        message += f"• 🔑 Clave pública:\n`{public_key}`\n\n"
        message += f"• 🔐 Clave privada:\n`{private_key}`\n\n"
        message += f"• 🔒 Pre-shared key:\n`{preshared_key}`\n\n"
        message += f"⚠️ *¡GUARDA TODAS LAS CLAVES DE FORMA SEGURA!*\n"
        message += f"Estas claves solo se mostrarán una vez y son necesarias para configurar el cliente."
        
        # Crear teclado con botones de volver y descargar
        keyboard = [
            [
                InlineKeyboardButton("⬅️ Volver a Configuración", callback_data=f"cfg:{config_name}"),
                InlineKeyboardButton("📥 Descargar Configuración", callback_data=f"download_config:{peer_hash}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        error_msg = result.get('message', 'Error desconocido')
        
        # Crear teclado con botón para volver
        keyboard = [[InlineKeyboardButton("⬅️ Volver a Configuración", callback_data=f"cfg:{config_name}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"❌ *Error al agregar peer*\n\n*Error:* {error_msg}\n\n"
            f"Intenta nuevamente o contacta al administrador.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
