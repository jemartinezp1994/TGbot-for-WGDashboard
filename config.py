"""
Configuración centralizada del bot WGDashboard
"""

import os
from typing import Dict, List, Any, Optional
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
# Roles
ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"

# Diccionario de usuarios permitidos {user_id: {"name": "nombre", "role": "admin|operator"}}
ALLOWED_USERS: Dict[int, Dict] = {
    762494594: {"name": "Owner", "role": ROLE_ADMIN},
    # Agrega más usuarios aquí:
    7645879687: {"name": "Operador 1", "role": ROLE_OPERATOR},
    7287104338: {"name": "Operador 2", "role": ROLE_OPERATOR},
    # 987654321: {"name": "Admin 2", "role": ROLE_ADMIN},
}

# ================= RUTAS ================= #
DATA_DIR = "data"
OPERATORS_DB = os.path.join(DATA_DIR, "operator_peers.json")

# ================= LOGGING ================= #
LOG_FILE = os.getenv("LOG_FILE", "wg_bot.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# ================= INTERFAZ ================= #
MAX_PEERS_DISPLAY = int(os.getenv("MAX_PEERS_DISPLAY", "10"))
ITEMS_PER_PAGE = 8

# ================= LÍMITES OPERADORES ================= #
OPERATOR_LIMIT_HOURS = 24  # Horas entre creación de peers
OPERATOR_DATA_LIMIT_GB = 1  # Límite de datos en GB
OPERATOR_TIME_LIMIT_HOURS = 24  # Límite de tiempo en horas

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
    
    # Crear directorio de datos si no existe
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception as e:
        errors.append(f"No se pudo crear directorio data: {str(e)}")
    
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
