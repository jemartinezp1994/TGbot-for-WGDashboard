"""
Manejo de base de datos para operadores y sus peers
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging

from config import OPERATORS_DB, OPERATOR_LIMIT_HOURS

logger = logging.getLogger(__name__)

class OperatorsDB:
    """Base de datos para gestionar peers creados por operadores"""
    
    def __init__(self):
        self.db_path = OPERATORS_DB
        self._ensure_db()
    
    def _ensure_db(self):
        """Asegura que exista la base de datos"""
        # Obtener el directorio del archivo
        db_dir = os.path.dirname(self.db_path)
        
        # Crear directorio si no existe
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Directorio de datos creado: {db_dir}")
            except Exception as e:
                logger.error(f"Error creando directorio de datos: {str(e)}")
                raise
        
        # Crear archivo si no existe
        if not os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                logger.info(f"Base de datos de operadores creada: {self.db_path}")
            except Exception as e:
                logger.error(f"Error creando base de datos: {str(e)}")
                raise
    
    def _load_db(self) -> Dict:
        """Carga la base de datos desde el archivo"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error cargando DB de operadores: {str(e)}")
            return {}
    
    def _save_db(self, data: Dict):
        """Guarda la base de datos en el archivo"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando DB de operadores: {str(e)}")
    
    def can_create_peer(self, user_id: int) -> Tuple[bool, Optional[str], Optional[datetime]]:
        """
        Verifica si un operador puede crear un nuevo peer.
        
        Returns:
            Tuple[bool, Optional[str], Optional[datetime]]: 
            - (True, None, None) si puede crear
            - (False, mensaje_error, datetime_proximo_permiso) si no puede
        """
        data = self._load_db()
        user_id_str = str(user_id)
        
        if user_id_str not in data:
            return True, None, None
        
        user_peers = data[user_id_str]
        if not user_peers:
            return True, None, None
        
        # Ordenar por fecha descendente (más reciente primero)
        user_peers.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        last_peer = user_peers[0]
        
        last_created_str = last_peer.get('created_at')
        if not last_created_str:
            return True, None, None
        
        try:
            last_created = datetime.fromisoformat(last_created_str)
            now = datetime.now()
            next_allowed = last_created + timedelta(hours=OPERATOR_LIMIT_HOURS)
            
            if now < next_allowed:
                # Calcular tiempo restante
                remaining = next_allowed - now
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                
                if hours > 0:
                    time_msg = f"{hours} horas y {minutes} minutos"
                else:
                    time_msg = f"{minutes} minutos"
                
                error_msg = f"Ya creaste un peer recientemente. Debes esperar {time_msg} para crear otro."
                return False, error_msg, next_allowed
            else:
                return True, None, None
                
        except Exception as e:
            logger.error(f"Error calculando límite de operador: {str(e)}")
            return True, None, None
    
    def register_peer(self, user_id: int, config_name: str, peer_name: str, public_key: str, endpoint: str = None) -> bool:
        """Registra un nuevo peer creado por un operador"""
        try:
            data = self._load_db()
            user_id_str = str(user_id)
            
            logger.info(f"Registrando peer para operador {user_id_str}")
            logger.info(f"Datos antes de registrar: {data.get(user_id_str, [])}")
            
            peer_record = {
                'created_at': datetime.now().isoformat(),
                'config_name': config_name,
                'peer_name': peer_name,
                'public_key': public_key,
                'endpoint': endpoint,  # Guardar el endpoint
                'data_limit_gb': 1,
                'time_limit_hours': 24
            }
            
            if user_id_str not in data:
                data[user_id_str] = []
            
            data[user_id_str].append(peer_record)
            
            # Mantener solo los últimos 10 registros por usuario
            if len(data[user_id_str]) > 10:
                data[user_id_str] = data[user_id_str][-10:]
            
            self._save_db(data)
            
            # Verificar que se guardó correctamente
            saved_data = self._load_db()
            logger.info(f"Datos después de registrar: {saved_data.get(user_id_str, [])}")
            
            logger.info(f"Peer registrado exitosamente para operador {user_id}: {peer_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registrando peer de operador: {str(e)}", exc_info=True)
            return False
    
    def get_user_peers(self, user_id: int) -> List[Dict]:
        """Obtiene todos los peers creados por un operador"""
        data = self._load_db()
        user_id_str = str(user_id)
        
        return data.get(user_id_str, [])
    
    def get_user_peers(self, user_id: int) -> List[Dict]:
        """Obtiene todos los peers creados por un operador"""
        data = self._load_db()
        user_id_str = str(user_id)
        
        return data.get(user_id_str, [])
    
    def get_last_peer_info(self, user_id: int) -> Optional[Dict]:
        """Obtiene información del último peer creado por el operador"""
        user_peers = self.get_user_peers(user_id)
        if not user_peers:
            return None
        
        user_peers.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return user_peers[0]
    
    def get_peer_by_hash(self, user_id: int, peer_hash: str) -> Optional[Dict]:
        """Busca un peer por hash"""
        user_peers = self.get_user_peers(user_id)
        for peer in user_peers:
            # Generar hash temporal para comparación
            import hashlib
            check_hash = hashlib.md5(
                f"{peer['config_name']}:{peer['public_key']}:{peer['peer_name']}".encode()
            ).hexdigest()[:12]
            
            if check_hash == peer_hash:
                return peer
        return None

# Instancia global de la base de datos
operators_db = OperatorsDB()
