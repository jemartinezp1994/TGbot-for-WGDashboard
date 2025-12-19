"""
Configuración centralizada del bot WGDashboard
"""

import os
from typing import Dict, List, Any
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ================= TELEGRAM ================= #
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ================= WGDASHBOARD API ================= #
WG_API_BASE_URL = os.getenv("WG_API_BASE_URL", "http://localhost:10086/api")
WG_API_KEY = os.getenv("WG_API_KEY", "")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))

# Opcional: Prefijo para la URL del dashboard
WG_API_PREFIX = os.getenv("WG_API_PREFIX", "")

# ================= SEGURIDAD ================= #
# Diccionario de usuarios permitidos {user_id: "nombre"}
ALLOWED_USERS: Dict[int, str] = {
    762494594: "Admin Principal",
    # Agrega más usuarios aquí:
    # 987654321: "Otro Admin",
}

# ================= LOGGING ================= #
LOG_FILE = os.getenv("LOG_FILE", "wg_bot.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# ================= INTERFAZ ================= #
MAX_PEERS_DISPLAY = int(os.getenv("MAX_PEERS_DISPLAY", "10"))
ITEMS_PER_PAGE = 8

# ================= VALIDACIÓN ================= #
def validate_config():
    """Valida que la configuración sea correcta"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN no configurado")
    
    if not WG_API_KEY:
        errors.append("WG_API_KEY no configurada")
    
    if not WG_API_BASE_URL:
        errors.append("WG_API_BASE_URL no configurada")
    
    if not ALLOWED_USERS:
        errors.append("ALLOWED_USERS está vacío")
    
    return errors

# Validar al importar
if __name__ == "__main__":
    validation_errors = validate_config()
    if validation_errors:
        print("⚠️  Errores de configuración:")
        for error in validation_errors:
            print(f"   - {error}")
    else:
        print("✅ Configuración validada correctamente")
