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
        
        # Log de la petición (sin datos sensibles)
        logger.debug(f"[API] {method} {endpoint}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            
            # Log del código de estado
            logger.debug(f"[API] Response: {response.status_code}")
            
            # Verificar código HTTP primero
            if response.status_code == 204:  # No Content
                logger.debug("[API] Respuesta 204 No Content")
                return {
                    "status": True,
                    "message": "Operación exitosa",
                    "data": None
                }
            
            if response.status_code == 404:
                error_msg = f"Endpoint no encontrado: {endpoint}"
                logger.error(f"[API] Error 404: {error_msg}")
                return {
                    "status": False,
                    "message": error_msg,
                    "data": None
                }
            
            if response.status_code != 200:
                # Intentar obtener mensaje de error del JSON si existe
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", f"HTTP {response.status_code}")
                except:
                    error_msg = f"HTTP {response.status_code}"
                
                logger.error(f"[API] Error HTTP {response.status_code}: {error_msg}")
                return {
                    "status": False,
                    "message": error_msg,
                    "data": None
                }
            
            # Si la respuesta está vacía pero fue exitosa
            if not response.text.strip():
                logger.debug("[API] Respuesta vacía pero código 200")
                return {
                    "status": True,
                    "message": "Operación exitosa",
                    "data": None
                }
            
            # Intentar parsear JSON
            try:
                result = response.json()
                return result
                
            except json.JSONDecodeError:
                logger.error(f"[API] Respuesta no es JSON válido: {response.text[:200]}")
                return {
                    "status": False,
                    "message": "Respuesta inválida del servidor",
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
        
        # Convertir latest_handshake de string a segundos para facilitar el procesamiento
        for peer in peers:
            latest_handshake_str = peer.get('latest_handshake', '').strip()
            seconds = 0
            
            if latest_handshake_str and latest_handshake_str.lower() != 'no handshake':
                try:
                    if 'days' in latest_handshake_str:
                        # Formato: "64 days, 14:20:56"
                        parts = latest_handshake_str.split(', ')
                        days = int(parts[0].split(' ')[0])
                        time_parts = list(map(int, parts[1].split(':')))
                        seconds = days * 86400 + time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
                    else:
                        # Formato: "0:01:01" o "01:01"
                        time_parts = list(map(int, latest_handshake_str.split(':')))
                        if len(time_parts) == 3:
                            seconds = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
                        elif len(time_parts) == 2:
                            seconds = time_parts[0] * 60 + time_parts[1]
                        # Si len es 1 o más de 3, se queda en 0
                except (ValueError, IndexError) as e:
                    # Si falla el parsing, dejamos en 0 sin loguear (es un caso normal)
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

    def download_peer_config(self, config_name: str, public_key: str) -> Dict:
        """Descarga la configuración de un peer"""
        endpoint = f"/downloadPeerConfig/{config_name}/{public_key}"
        
        logger.info(f"[API] Descargando configuración de {config_name} para peer: {public_key[:30]}...")
        
        try:
            response = self._make_request("GET", endpoint)
            
            if response.get("status"):
                config_content = response.get("data", "")
                return {
                    "status": True,
                    "message": "Configuración descargada",
                    "data": config_content
                }
            else:
                logger.warning(f"Endpoint directo falló, intentando alternativa...")
                
                alternative_endpoint = "/email/previewBody"
                payload = {
                    "ConfigurationName": config_name,
                    "Peer": public_key,
                    "Body": "{{ peer.configuration }}"
                }
                
                alt_response = self._make_request("POST", alternative_endpoint, json=payload)
                
                if alt_response.get("status"):
                    return {
                        "status": True,
                        "message": "Configuración obtenida",
                        "data": alt_response.get("data", "")
                    }
                else:
                    return response
        
        except Exception as e:
            logger.error(f"[API] Error al descargar configuración: {str(e)}")
            return {
                "status": False,
                "message": f"Error al descargar: {str(e)}",
                "data": None
            }
    
    def get_system_status(self) -> Dict:
        """Obtiene el estado del sistema"""
        cache_key = "system_status"
        cached = self._get_cached(cache_key)
        
        if cached:
            logger.debug("[API] Usando cache para system_status")
            return cached
        
        result = self._make_request("GET", "/systemStatus")
        
        if result.get("status"):
            self._set_cache(cache_key, result)
        
        return result
    
    def get_protocols(self) -> Dict:
        """Obtiene los protocolos habilitados"""
        cache_key = "protocols"
        cached = self._get_cached(cache_key)
        
        if cached:
            logger.debug("[API] Usando cache para protocols")
            return cached
        
        result = self._make_request("GET", "/protocolsEnabled")
        
        if result.get("status"):
            self._set_cache(cache_key, result)
        
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
                    # Asegurar formato de 2 dígitos para mes y día
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
        
        Args:
            config_name: Nombre de la configuración
            public_key: Clave pública del peer
            job_id: ID del trabajo a eliminar
            job_data: Datos completos del job (opcional)
        
        Returns:
            Dict con el resultado de la operación
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
        
        # Loguear el payload exacto que se envía
        logger.debug(f"[API] Payload de eliminación: {json.dumps(payload, indent=2)}")
        
        result = self._make_request("POST", endpoint, json=payload)
        
        # Si falla, intentar con endpoint alternativo
        if not result.get("status"):
            logger.warning(f"Endpoint {endpoint} falló, intentando con /savePeerScheduleJob...")
            
            alt_endpoint = "/savePeerScheduleJob"
            alt_payload = payload.copy()
            alt_payload["Job"]["Action"] = "delete"
            
            result = self._make_request("POST", alt_endpoint, json=alt_payload)
        
        return result

# Instancia global del cliente
api_client = WGApiClient()
