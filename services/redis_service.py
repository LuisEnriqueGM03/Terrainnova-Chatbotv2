import os
import json
import redis
from typing import List, Dict, Optional
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

class RedisService:
    def __init__(self):
        # Obtener URL de Redis desde variables de entorno
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # Intentar conectar a Redis
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()  # Probar conexión
            self.redis_available = True
            print("INFO: Conectado a Redis exitosamente")
        except Exception as e:
            print(f"WARNING: Redis no disponible ({e}). Usando almacenamiento en memoria.")
            self.redis_available = False
            self.redis_client = None
            # Almacenamiento en memoria como fallback
            self.memory_storage = {}
        
        self.context_ttl = 3600 * 24 * 7  # 7 días de TTL por defecto
    
    def get_context(self, user_id: str) -> List[Dict[str, str]]:
        """
        Obtiene el contexto de conversación de un usuario
        
        Args:
            user_id: ID único del usuario
            
        Returns:
            List[Dict[str, str]]: Lista de mensajes del contexto
        """
        try:
            if self.redis_available and self.redis_client:
                # Usar Redis si está disponible
                key = f"chat_context:{user_id}"
                context_data = self.redis_client.get(key)
                
                if context_data:
                    return json.loads(context_data)
                else:
                    return []
            else:
                # Usar almacenamiento en memoria
                return self.memory_storage.get(user_id, [])
                
        except Exception as e:
            print(f"Error al obtener contexto: {e}")
            # Fallback a memoria
            return self.memory_storage.get(user_id, [])
    
    def save_context(self, user_id: str, user_message: str, ai_response: str) -> bool:
        """
        Guarda el contexto de conversación
        
        Args:
            user_id: ID único del usuario
            user_message: Mensaje del usuario
            ai_response: Respuesta de la IA
            
        Returns:
            bool: True si se guardó correctamente, False en caso contrario
        """
        try:
            # Obtener contexto existente
            current_context = self.get_context(user_id)
            
            # Agregar el nuevo intercambio de mensajes
            current_context.append({
                "role": "user",
                "content": user_message,
                "timestamp": self._get_timestamp()
            })
            
            current_context.append({
                "role": "assistant", 
                "content": ai_response,
                "timestamp": self._get_timestamp()
            })
            
            # Limitar el contexto a los últimos 20 mensajes para evitar que crezca demasiado
            if len(current_context) > 20:
                current_context = current_context[-20:]
            
            if self.redis_available and self.redis_client:
                # Guardar en Redis
                key = f"chat_context:{user_id}"
                self.redis_client.setex(
                    key,
                    self.context_ttl,
                    json.dumps(current_context)
                )
            else:
                # Guardar en memoria
                self.memory_storage[user_id] = current_context
            
            return True
            
        except Exception as e:
            print(f"Error al guardar contexto: {e}")
            # Fallback a memoria
            try:
                self.memory_storage[user_id] = current_context
                return True
            except:
                return False
    
    def clear_context(self, user_id: str) -> bool:
        """
        Limpia el contexto de conversación de un usuario
        
        Args:
            user_id: ID único del usuario
            
        Returns:
            bool: True si se limpió correctamente
        """
        try:
            if self.redis_available and self.redis_client:
                key = f"chat_context:{user_id}"
                self.redis_client.delete(key)
            else:
                # Limpiar de memoria
                if user_id in self.memory_storage:
                    del self.memory_storage[user_id]
            return True
        except Exception as e:
            print(f"Error al limpiar contexto: {e}")
            return False
    
    def get_context_length(self, user_id: str) -> int:
        """
        Obtiene la longitud del contexto de un usuario
        
        Args:
            user_id: ID único del usuario
            
        Returns:
            int: Número de mensajes en el contexto
        """
        context = self.get_context(user_id)
        return len(context)
    
    def set_context_ttl(self, ttl_seconds: int):
        """
        Establece el TTL para el contexto de conversación
        
        Args:
            ttl_seconds: Tiempo de vida en segundos
        """
        self.context_ttl = ttl_seconds
    
    def _get_timestamp(self) -> str:
        """
        Obtiene el timestamp actual en formato ISO
        """
        return datetime.now().isoformat()
    
    def health_check(self) -> bool:
        """
        Verifica la conectividad con Redis
        
        Returns:
            bool: True si Redis está disponible
        """
        if self.redis_available and self.redis_client:
            try:
                self.redis_client.ping()
                return True
            except:
                return False
        else:
            # Si Redis no está disponible, consideramos que el servicio está "saludable"
            # porque puede funcionar con almacenamiento en memoria
            return True

# Instancia global del servicio
redis_service = RedisService()

def get_context(user_id: str) -> List[Dict[str, str]]:
    """
    Función de conveniencia para obtener contexto
    """
    return redis_service.get_context(user_id)

def save_context(user_id: str, user_message: str, ai_response: str) -> bool:
    """
    Función de conveniencia para guardar contexto
    """
    return redis_service.save_context(user_id, user_message, ai_response) 