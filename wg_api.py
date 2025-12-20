"""
Cliente para la API de WGDashboard
"""

import json
import logging
import uuid
from typing import Dict, List, Optional, Any
import requests
from requests.exceptions import RequestException
from datetime import datetime
import psutil
import platform

from config import WG_API_BASE_URL, WG_API_KEY, API_TIMEOUT, WG_API_PREFIX

logger = logging.getLogger(__name__)

class WGApiError(Exception):
    """Excepción personalizada para errores de API"""
    pass

class WGApiClient:
    """Cliente para interactuar con la API de WGDashboard"""
    
    def __init__(self):
        self.base_url = WG_API_BASE_URL.rstrip('/')
        if WG_API_PREFIX:
            self.base_url = f"{self.base_url.rstrip('/')}/{WG_API_PREFIX.lstrip('/')}"
        
        self.headers = {
            "wg-dashboard-apikey": WG_API_KEY,
            "Content-Type": "application/json",
            "User-Agent": "WGDashboard-Bot/1.0"
        }
        self.timeout = API_TIMEOUT
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Cache simple
        self._cache = {}
        self._cache_ttl = 30  # segundos
    
    def _get_cached(self, key: str):
        """Obtiene datos del cache si son recientes"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if (datetime.now() - timestamp).seconds < self._cache_ttl:
                return data
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Guarda datos en cache"""
        self._cache[key] = (data, datetime.now())
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Realiza una petición HTTP a la API"""
        url = f"{self.base_url}{endpoint}"
        
        logger.debug(f"[API] {method} {endpoint}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            
            logger.debug(f"[API] Response: {response.status_code}")
            
            if response.status_code == 200:
                # Intentar determinar si es JSON o texto plano
                content_type = response.headers.get('Content-Type', '').lower()
                
                if 'application/json' in content_type:
                    try:
                        result = response.json()
                        return result
                    except json.JSONDecodeError:
                        logger.error(f"[API] Respuesta no es JSON válido: {response.text[:200]}")
                        return {
                            "status": False,
                            "message": "Respuesta JSON inválida del servidor",
                            "data": None
                        }
                else:
                    # Es texto plano (como un archivo .conf)
                    return {
                        "status": True,
                        "message": "Configuración descargada",
                        "data": response.text
                    }
            else:
                # Manejar otros códigos de estado
                error_msg = f"HTTP {response.status_code}"
                if response.text:
                    error_msg += f": {response.text[:100]}"
                
                # Para errores 404, usar WARNING en lugar de ERROR
                if response.status_code == 404:
                    logger.warning(f"[API] Endpoint no encontrado (404): {method} {endpoint}")
                else:
                    logger.error(f"[API] Error HTTP {response.status_code}: {method} {endpoint}")
                
                return {
                    "status": False,
                    "message": error_msg,
                    "data": None
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"[API] Timeout en {method} {endpoint}")
            return {
                "status": False,
                "message": "Timeout al conectar con el servidor",
                "data": None
            }
        except requests.exceptions.ConnectionError:
            logger.error(f"[API] Error de conexión en {method} {endpoint}")
            return {
                "status": False,
                "message": "No se puede conectar al servidor",
                "data": None
            }
        except RequestException as e:
            logger.error(f"[API] Error en petición: {str(e)}")
            return {
                "status": False,
                "message": f"Error de red: {str(e)}",
                "data": None
            }
        except Exception as e:
            logger.error(f"[API] Error inesperado: {str(e)}", exc_info=True)
            return {
                "status": False,
                "message": f"Error interno: {str(e)}",
                "data": None
            }
    
    # ================= MÉTODOS DE API ================= #
    
    def handshake(self) -> Dict:
        """Verifica la conexión con la API"""
        return self._make_request("GET", "/handshake")
    
    def get_configurations(self, use_cache: bool = True) -> Dict:
        """Obtiene todas las configuraciones WireGuard"""
        cache_key = "configurations"
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                logger.debug("[API] Usando cache para configuraciones")
                return cached
        
        result = self._make_request("GET", "/getWireguardConfigurations")
        
        if result.get("status") and use_cache:
            self._set_cache(cache_key, result)
        
        return result
    
    def get_configuration_detail(self, config_name: str) -> Dict:
        """Obtiene detalles de una configuración específica"""
        endpoint = f"/getWireguardConfigurationInfo?configurationName={config_name}"
        
        result = self._make_request("GET", endpoint)
        
        if not result.get("status"):
            return result
        
        data = result.get("data", {})
        config_info = data.get("configurationInfo", {})
        
        return {
            "status": True,
            "message": None,
            "data": config_info
        }
    
    def get_peers(self, config_name: str) -> Dict:
        """Obtiene la lista de peers de una configuración"""
        endpoint = f"/getWireguardConfigurationInfo?configurationName={config_name}"
        
        result = self._make_request("GET", endpoint)
        
        if not result.get("status"):
            logger.error(f"[API] Error en getWireguardConfigurationInfo: {result.get('message')}")
            return result
        
        data = result.get("data", {})
        config_info = data.get("configurationInfo", {})
        peers = data.get("configurationPeers", [])
        restricted_peers = data.get("configurationRestrictedPeers", [])
        
        # Convertir latest_handshake de string a segundos
        for peer in peers:
            latest_handshake_str = peer.get('latest_handshake', '').strip()
            seconds = 0
            
            if latest_handshake_str and latest_handshake_str.lower() != 'no handshake':
                try:
                    if 'days' in latest_handshake_str:
                        parts = latest_handshake_str.split(', ')
                        days = int(parts[0].split(' ')[0])
                        time_parts = list(map(int, parts[1].split(':')))
                        seconds = days * 86400 + time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
                    else:
                        time_parts = list(map(int, latest_handshake_str.split(':')))
                        if len(time_parts) == 3:
                            seconds = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
                        elif len(time_parts) == 2:
                            seconds = time_parts[0] * 60 + time_parts[1]
                except (ValueError, IndexError):
                    pass
            
            peer['latest_handshake_seconds'] = seconds
        
        # Calcular peers conectados
        connected_peers = 0
        for peer in peers:
            if peer.get('status') == 'running' and peer.get('latest_handshake_seconds', 0) > 0:
                connected_peers += 1
        
        return {
            "status": True,
            "message": None,
            "data": peers,
            "restricted_data": restricted_peers,
            "metadata": {
                "total": len(peers) + len(restricted_peers),
                "connected": connected_peers,
                "restricted": len(restricted_peers),
                "config_name": config_name,
                "config_data": config_info
            }
        }
    
    def get_restricted_peers(self, config_name: str) -> Dict:
        """Obtiene solo los peers restringidos de una configuración"""
        endpoint = f"/getWireguardConfigurationInfo?configurationName={config_name}"
        
        result = self._make_request("GET", endpoint)
        
        if not result.get("status"):
            logger.error(f"[API] Error en getWireguardConfigurationInfo: {result.get('message')}")
            return result
        
        data = result.get("data", {})
        restricted_peers = data.get("configurationRestrictedPeers", [])
        
        return {
            "status": True,
            "message": None,
            "data": restricted_peers,
            "metadata": {
                "total": len(restricted_peers),
                "config_name": config_name
            }
        }
    
    def restrict_peer(self, config_name: str, public_key: str) -> Dict:
        """Restringe un peer específico"""
        endpoint = f"/restrictPeers/{config_name}"
        payload = {
            "peers": [public_key]
        }
        
        logger.info(f"[API] Restringiendo peer en {config_name}: {public_key[:30]}...")
        
        result = self._make_request("POST", endpoint, json=payload)
        
        # Invalidar cache de configuraciones
        if "configurations" in self._cache:
            del self._cache["configurations"]
        
        return result
    
    def allow_access_peer(self, config_name: str, public_key: str) -> Dict:
        """Quita la restricción de un peer específico"""
        endpoint = f"/allowAccessPeers/{config_name}"
        payload = {
            "peers": [public_key]
        }
        
        logger.info(f"[API] Quitando restricción a peer en {config_name}: {public_key[:30]}...")
        
        result = self._make_request("POST", endpoint, json=payload)
        
        # Invalidar cache de configuraciones
        if "configurations" in self._cache:
            del self._cache["configurations"]
        
        return result
    
    def delete_peer(self, config_name: str, public_key: str) -> Dict:
        """Elimina un peer específico"""
        endpoint = f"/deletePeers/{config_name}"
        payload = {
            "peers": [public_key]
        }
        
        logger.info(f"[API] Eliminando peer de {config_name}: {public_key[:30]}...")
        
        result = self._make_request("POST", endpoint, json=payload)
        
        # Invalidar cache de configuraciones
        if "configurations" in self._cache:
            del self._cache["configurations"]
        
        return result
    
    def add_peer(self, config_name: str, peer_data: Dict) -> Dict:
        """Agrega un nuevo peer a la configuración"""
        endpoint = f"/addPeers/{config_name}"
        
        payload = {
            "bulkAdd": False,
            "bulkAddAmount": 0,
            "name": peer_data.get("name", "nuevo-peer"),
            "allowed_ips": [peer_data.get("allowed_ips", "10.21.0.2/32")],
            "private_key": peer_data.get("private_key", ""),
            "public_key": peer_data.get("public_key", ""),
            "DNS": peer_data.get("dns", "1.1.1.1"),
            "endpoint_allowed_ip": "0.0.0.0/0",
            "keepalive": peer_data.get("persistent_keepalive", 21),
            "mtu": peer_data.get("mtu", 1420),
            "preshared_key": peer_data.get("preshared_key", ""),
            "preshared_key_bulkAdd": False,
            "advanced_security": "off",
            "allowed_ips_validation": True
        }
        
        logger.info(f"[API] Agregando peer a {config_name}: {payload['name']}")
        logger.debug(f"[API] Payload EXACTO: {json.dumps(payload, indent=2)}")
        
        result = self._make_request("POST", endpoint, json=payload)
        
        # Log de respuesta completa
        if result:
            logger.debug(f"[API] Respuesta completa: {json.dumps(result, indent=2)}")
        
        # Invalidar cache de configuraciones
        if "configurations" in self._cache:
            del self._cache["configurations"]
        
        return result
    
    def create_schedule_job(self, config_name: str, public_key: str, job_data: Dict) -> Dict:
        """Crea un trabajo programado para un peer usando el endpoint correcto"""
        endpoint = "/savePeerScheduleJob"
        
        # Generar un JobID único
        job_id = str(uuid.uuid4())
        
        # Determinar el campo según el tipo
        field = job_data.get("Field", "total_data")
        value = job_data.get("Value", "")
        
        # Si es una fecha, formatearla correctamente
        if field == "date":
            # Asegurarnos de que la fecha tenga formato YYYY-MM-DD HH:MM:SS
            try:
                # Convertir de dd/mm/yyyy a YYYY-MM-DD
                if '/' in value:
                    day, month, year = value.split('/')
                    day = day.zfill(2)
                    month = month.zfill(2)
                    value = f"{year}-{month}-{day} 00:00:00"
            except:
                pass
        
        # Construir el payload según la API real
        payload = {
            "Job": {
                "JobID": job_id,
                "Configuration": config_name,
                "Peer": public_key,
                "Field": field,
                "Operator": "lgt",
                "Value": value,
                "CreationDate": "",
                "ExpireDate": "",
                "Action": "restrict"
            }
        }
        
        logger.info(f"[API] Creando schedule job para peer {public_key[:30]}... en {config_name}")
        logger.debug(f"[API] Payload EXACTO: {json.dumps(payload, indent=2)}")
        
        result = self._make_request("POST", endpoint, json=payload)
        
        return result
    
    def delete_schedule_job(self, config_name: str, public_key: str, job_id: str, job_data: Dict = None) -> Dict:
        """
        Elimina un trabajo programado específico.
        """
        # Intentar primero con el endpoint principal
        endpoint = "/deletePeerScheduleJob"
        
        # Construir payload mínimo
        payload = {
            "Job": {
                "JobID": job_id,
                "Configuration": config_name,
                "Peer": public_key
            }
        }
        
        # Si tenemos datos completos del job, incluirlos
        if job_data:
            # Copiar todos los campos del job
            for key, value in job_data.items():
                if key not in ["JobID", "Configuration", "Peer"]:
                    payload["Job"][key] = value
            # Forzar acción delete
            payload["Job"]["Action"] = "delete"
        
        logger.info(f"[API] Eliminando schedule job: {job_id} para peer {public_key[:30]}")
        
        result = self._make_request("POST", endpoint, json=payload)
        
        # Si falla, intentar con endpoint alternativo
        if not result.get("status"):
            logger.warning(f"Endpoint {endpoint} falló, intentando con /savePeerScheduleJob...")
            
            alt_endpoint = "/savePeerScheduleJob"
            alt_payload = payload.copy()
            alt_payload["Job"]["Action"] = "delete"
            
            result = self._make_request("POST", alt_endpoint, json=alt_payload)
        
        return result
    
    def download_peer_config(self, config_name: str, public_key: str) -> Dict:
        """Descarga la configuración de un peer"""
        logger.info(f"[API] Descargando configuración para peer recién creado: {public_key[:30]}...")
        
        return {
            "status": True,
            "message": "Configuración lista para generarse localmente",
            "data": None
        }
    
    def get_system_status(self) -> Dict:
        """Obtiene el estado del sistema"""
        # Intentar diferentes endpoints posibles
        endpoints = [
            "/systemStatus",
            "/getSystemStatus",
            "/status",
            "/system/status"
        ]
        
        for endpoint in endpoints:
            result = self._make_request("GET", endpoint)
            if result.get("status"):
                data = result.get("data", {})
                if data:
                    logger.info(f"[API] Sistema status obtenido desde {endpoint}")
                    return result
        
        # Si ninguno funcionó, devolver datos de ejemplo
        logger.warning("[API] No se pudo obtener estado del sistema, devolviendo datos de ejemplo")
        
        # Datos de ejemplo basados en psutil
        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "mountPoint": partition.mountpoint,
                    "percent": usage.percent,
                    "free": usage.free,
                    "total": usage.total,
                    "used": usage.used
                })
            except:
                pass
        
        net_io = psutil.net_io_counters(pernic=True)
        network_interfaces = {}
        for interface, stats in net_io.items():
            network_interfaces[interface] = {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv
            }
        
        return {
            "status": True,
            "message": "Datos de ejemplo para desarrollo",
            "data": {
                "CPU": {
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                    "cpu_count": psutil.cpu_count(),
                    "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else 0
                },
                "Memory": {
                    "VirtualMemory": {
                        "total": psutil.virtual_memory().total,
                        "available": psutil.virtual_memory().available,
                        "percent": psutil.virtual_memory().percent,
                        "used": psutil.virtual_memory().used,
                        "free": psutil.virtual_memory().free
                    },
                    "SwapMemory": {
                        "total": psutil.swap_memory().total,
                        "used": psutil.swap_memory().used,
                        "free": psutil.swap_memory().free,
                        "percent": psutil.swap_memory().percent
                    }
                },
                "Disks": disks[:3],
                "NetworkInterfaces": network_interfaces,
                "System": {
                    "platform": platform.system(),
                    "release": platform.release(),
                    "uptime": int(datetime.now().timestamp() - psutil.boot_time()),
                    "boot_time": psutil.boot_time()
                }
            }
        }
    
    def get_protocols(self) -> Dict:
        """Obtiene los protocolos habilitados"""
        # Solo intentar el endpoint principal
        endpoint = "/protocols"
        result = self._make_request("GET", endpoint)
        
        # Si el endpoint existe y devuelve datos, usarlos
        if result.get("status") and result.get("data"):
            return result
        
        # Si no, devolver la lista básica
        logger.debug("[API] Endpoint de protocolos no disponible, usando lista por defecto")
        return {
            "status": True,
            "message": "Protocolos obtenidos",
            "data": ["wg"]
        }
    
    def get_system_stats(self) -> Dict:
        """Obtiene estadísticas del sistema"""
        return self.get_system_status()

# ========== INSTANCIA GLOBAL DEL CLIENTE ==========
api_client = WGApiClient()
