"""
Módulo para generar teclados inline
"""

import base64
from typing import List, Dict, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import ITEMS_PER_PAGE

def safe_callback_data(text: str) -> str:
    """Codifica texto para hacerlo seguro para callback_data"""
    # Codificar en base64 y luego reemplazar caracteres problemáticos
    encoded = base64.urlsafe_b64encode(text.encode()).decode()
    return encoded

def decode_callback_data(encoded: str) -> str:
    """Decodifica texto de callback_data seguro"""
    try:
        decoded = base64.urlsafe_b64decode(encoded.encode()).decode()
        return decoded
    except:
        return encoded

def main_menu() -> InlineKeyboardMarkup:
    """Teclado del menú principal"""
    keyboard = [
        [
            InlineKeyboardButton("🔌 Test API", callback_data="handshake"),
            InlineKeyboardButton("📡 Configuraciones", callback_data="configs")
        ],
        [
            InlineKeyboardButton("🖥 Estado del Sistema", callback_data="system_status"),
            InlineKeyboardButton("⚡ Protocolos", callback_data="protocols")
        ],
        [
            InlineKeyboardButton("📊 Estadísticas", callback_data="stats"),
            InlineKeyboardButton("❓ Ayuda", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def config_menu(config_name: str) -> InlineKeyboardMarkup:
    """Menú para una configuración específica"""
    keyboard = [
        [InlineKeyboardButton("📥 Descargar Peers", callback_data=f"peers:{config_name}")],
        # Cambio: Llamar directamente a la vista paginada en lugar de al menú intermedio
	[InlineKeyboardButton("📋 Detalles Peers", callback_data=f"peers_detailed_paginated:{config_name}:0")],
        [InlineKeyboardButton("🗑 Eliminar Peer", callback_data=f"delete_peer:{config_name}")],
        [InlineKeyboardButton("➕ Agregar Peer", callback_data=f"add_peer:{config_name}")],
        [InlineKeyboardButton("⏰ Schedule Jobs", callback_data=f"schedule_jobs_menu:{config_name}")],
        # NUEVO: Botón de restricciones
        [InlineKeyboardButton("🚫 Restricciones", callback_data=f"restrictions:{config_name}")],
        [InlineKeyboardButton("🔄 Actualizar", callback_data=f"cfg:{config_name}")],
        [InlineKeyboardButton("⬅️ Volver", callback_data="configs")]
    ]
    return InlineKeyboardMarkup(keyboard)

def restrictions_menu(config_name: str) -> InlineKeyboardMarkup:
    """Menú de restricciones para una configuración"""
    keyboard = [
        [InlineKeyboardButton("👥 Restringidos", callback_data=f"restricted_peers:{config_name}:0")],
        [InlineKeyboardButton("🔒 Restringir Peer", callback_data=f"restrict_peer_menu:{config_name}:0")],
        [InlineKeyboardButton("⬅️ Volver", callback_data=f"cfg:{config_name}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# En keyboards.py, actualiza estas funciones:

def paginated_restricted_peers_menu(peers: List[Dict], config_name: str, page: int) -> InlineKeyboardMarkup:
    """Crea un teclado paginado con peers restringidos - VERSIÓN SIMPLIFICADA"""
    keyboard = []
    start_idx = page * 6  # REDUCIDO a 6 items por página
    end_idx = start_idx + 6
    page_peers = peers[start_idx:end_idx]
    
    for i, peer in enumerate(page_peers, start_idx):
        peer_name = peer.get('name', f'Peer {i+1}')
        # Usar solo el índice en callback_data - MUY CORTO
        button_text = f"🔓 {peer_name[:15]}"
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"unrestrict:{config_name}:{i}"
            )
        ])
    
    # Botones de navegación
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️", callback_data=f"page_res:{config_name}:{page-1}")
        )
    
    if end_idx < len(peers):
        nav_buttons.append(
            InlineKeyboardButton("▶️", callback_data=f"page_res:{config_name}:{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Botones de acción
    keyboard.append([
        InlineKeyboardButton("⬅️ Volver", callback_data=f"restrictions:{config_name}")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def paginated_unrestricted_peers_menu(peers: List[Dict], config_name: str, page: int) -> InlineKeyboardMarkup:
    """Crea un teclado paginado con peers NO restringidos - VERSIÓN SIMPLIFICADA"""
    keyboard = []
    start_idx = page * 6  # REDUCIDO a 6 items por página
    end_idx = start_idx + 6
    page_peers = peers[start_idx:end_idx]
    
    for i, peer in enumerate(page_peers, start_idx):
        peer_name = peer.get('name', f'Peer {i+1}')
        # Usar solo el índice en callback_data - MUY CORTO
        button_text = f"🔒 {peer_name[:15]}"
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"restrict:{config_name}:{i}"
            )
        ])
    
    # Botones de navegación
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️", callback_data=f"page_unres:{config_name}:{page-1}")
        )
    
    if end_idx < len(peers):
        nav_buttons.append(
            InlineKeyboardButton("▶️", callback_data=f"page_unres:{config_name}:{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Botones de acción
    keyboard.append([
        InlineKeyboardButton("⬅️ Volver", callback_data=f"restrictions:{config_name}")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def paginated_configs_menu(configs: List[Dict], page: int = 0) -> InlineKeyboardMarkup:
    """Menú paginado de configuraciones"""
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_configs = configs[start_idx:end_idx]
    
    keyboard = []
    
    # Botones de configuraciones
    for config in page_configs:
        config_name = config.get('Name', 'Sin nombre')
        total_peers = config.get('TotalPeers', 0)
        connected = config.get('ConnectedPeers', 0)
        
        button_text = f"{config_name} ({connected}/{total_peers})"
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"cfg:{config_name}")
        ])
    
    # Botones de navegación
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️ Anterior", callback_data=f"page_configs:{page-1}")
        )
    
    if end_idx < len(configs):
        nav_buttons.append(
            InlineKeyboardButton("Siguiente ▶️", callback_data=f"page_configs:{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Botones de acción global
    keyboard.extend([
        [
            InlineKeyboardButton("🔄 Actualizar", callback_data="configs"),
            InlineKeyboardButton("📋 Resumen", callback_data="configs_summary")
        ],
        [InlineKeyboardButton("⬅️ Menú Principal", callback_data="main_menu")]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def peers_selection_menu(peers: List[Dict], config_name: str, action: str, page: int = 0) -> InlineKeyboardMarkup:
    """Menú para seleccionar peers (para eliminar, ver detalles, etc.)"""
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_peers = peers[start_idx:end_idx]
    
    keyboard = []
    
    for peer in page_peers:
        peer_name = peer.get('name', 'Sin nombre')
        peer_key = peer.get('id', '')  # 'id' es la clave pública
        # Codificar la clave pública para callback_data seguro
        safe_peer_key = safe_callback_data(peer_key)
        
        button_text = f"{peer_name}"
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"{action}_confirm:{config_name}:{safe_peer_key}"
            )
        ])
    
    # Botones de navegación
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️ Anterior", callback_data=f"page_{action}:{config_name}:{page-1}")
        )
    
    if end_idx < len(peers):
        nav_buttons.append(
            InlineKeyboardButton("Siguiente ▶️", callback_data=f"page_{action}:{config_name}:{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Botón para cancelar/volver
    keyboard.append([
        InlineKeyboardButton("❌ Cancelar", callback_data=f"cfg:{config_name}")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def confirmation_menu(config_name: str, peer_identifier: str, action_type: str, action_text: str = None) -> InlineKeyboardMarkup:
    """Crea un menú de confirmación para acciones críticas"""
    # Si no se proporciona action_text, usar un valor por defecto basado en action_type
    if action_text is None:
        action_text_map = {
            "delete_peer": "Eliminar",
            "unrestrict": "Quitar Restricción",
            "restrict": "Restringir",
            "delete_schedule_job": "Eliminar Job"
        }
        action_text = action_text_map.get(action_type, "Confirmar")
    
    # Codificar el identificador si es necesario
    from keyboards import safe_callback_data
    safe_identifier = safe_callback_data(peer_identifier)
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"✅ Sí, {action_text.lower()}",
                callback_data=f"{action_type}_execute:{config_name}:{safe_identifier}"
            ),
            InlineKeyboardButton(
                f"❌ Cancelar",
                callback_data=f"cfg:{config_name}"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def back_button(target: str = "main_menu") -> InlineKeyboardMarkup:
    """Botón simple para volver"""
    keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data=target)]]
    return InlineKeyboardMarkup(keyboard)

def refresh_button(target: str) -> InlineKeyboardMarkup:
    """Botón para refrescar la vista actual"""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Actualizar", callback_data=target),
            InlineKeyboardButton("⬅️ Volver", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
