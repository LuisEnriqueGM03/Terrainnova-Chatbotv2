import os
from openai import OpenAI
from typing import List, Dict, Any
from dotenv import load_dotenv
import logging

# Cargar variables de entorno desde múltiples archivos
load_dotenv()  # Busca .env
load_dotenv("config.env")  # Busca config.env

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.model = "gpt-3.5-turbo"  # Puedes cambiar a gpt-4 si tienes acceso
        self.embedding_model = "text-embedding-ada-002"  # Modelo para embeddings
        self.max_tokens = 1000
        self.temperature = 0.7
        
        # Obtener API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            logger.error("OPENAI_API_KEY no está configurada. Por favor, configura tu clave en config.env")
            self.client = None
        else:
            # Configurar OpenAI
            self.client = OpenAI(api_key=api_key)
            logger.info("Cliente OpenAI configurado correctamente")
    
    def generate_response(self, message: str, context: List[Dict[str, str]] = None) -> str:
        """
        Genera una respuesta usando la API de OpenAI
        
        Args:
            message: El mensaje del usuario
            context: Lista de mensajes previos para mantener contexto
            
        Returns:
            str: La respuesta generada por la IA
        """
        if not self.client:
            return "Error: OpenAI no está configurado. Por favor, configura OPENAI_API_KEY en config.env"
        
        try:
            # Preparar el historial de conversación
            messages = []
            
            # Agregar contexto previo si existe
            if context:
                for msg in context:
                    if msg.get("role") == "user":
                        messages.append({"role": "user", "content": msg.get("content", "")})
                    elif msg.get("role") == "assistant":
                        messages.append({"role": "assistant", "content": msg.get("content", "")})
            
            # Agregar el mensaje actual
            messages.append({"role": "user", "content": message})
            
            # Realizar la llamada a OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Extraer y retornar la respuesta
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error inesperado: {str(e)}"
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Genera un embedding vectorial para un texto usando OpenAI
        
        Args:
            text: El texto para generar el embedding
            
        Returns:
            List[float]: Vector de embedding de 1536 dimensiones
        """
        if not self.client:
            logger.error("OpenAI no está configurado para generar embeddings")
            return [0.0] * 1536
        
        try:
            # Validar que el texto no esté vacío
            if not text or not text.strip():
                logger.warning("Texto vacío proporcionado para generar embedding")
                return [0.0] * 1536  # Vector de ceros como fallback
            
            # Limpiar y truncar el texto si es muy largo (límite de OpenAI)
            cleaned_text = text.strip()
            if len(cleaned_text) > 8192:  # Límite aproximado para text-embedding-ada-002
                cleaned_text = cleaned_text[:8192]
                logger.info(f"Texto truncado a 8192 caracteres para generar embedding")
            
            # Realizar la llamada a la API de embeddings
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=cleaned_text
            )
            
            # Extraer el vector de embedding
            embedding = response.data[0].embedding
            
            logger.info(f"Embedding generado exitosamente para texto de {len(cleaned_text)} caracteres")
            return embedding
            
        except Exception as e:
            logger.error(f"Error inesperado al generar embedding: {str(e)}")
            return [0.0] * 1536
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para múltiples textos en una sola llamada
        
        Args:
            texts: Lista de textos para generar embeddings
            
        Returns:
            List[List[float]]: Lista de vectores de embedding
        """
        if not self.client:
            logger.error("OpenAI no está configurado para generar embeddings")
            return [[0.0] * 1536] * len(texts)
        
        try:
            # Filtrar textos vacíos
            valid_texts = [text.strip() for text in texts if text and text.strip()]
            
            if not valid_texts:
                logger.warning("No hay textos válidos para generar embeddings")
                return []
            
            # Truncar textos muy largos
            processed_texts = []
            for text in valid_texts:
                if len(text) > 8192:
                    processed_texts.append(text[:8192])
                    logger.info(f"Texto truncado a 8192 caracteres")
                else:
                    processed_texts.append(text)
            
            # Realizar la llamada batch a la API
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=processed_texts
            )
            
            # Extraer todos los embeddings
            embeddings = [item.embedding for item in response.data]
            
            logger.info(f"Embeddings generados exitosamente para {len(embeddings)} textos")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error al generar embeddings en batch: {str(e)}")
            return [[0.0] * 1536] * len(texts)
    
    def set_model(self, model: str):
        """Cambiar el modelo de OpenAI"""
        self.model = model
    
    def set_embedding_model(self, embedding_model: str):
        """Cambiar el modelo de embedding"""
        self.embedding_model = embedding_model
    
    def set_temperature(self, temperature: float):
        """Ajustar la temperatura de generación"""
        self.temperature = temperature
    
    def set_max_tokens(self, max_tokens: int):
        """Ajustar el número máximo de tokens"""
        self.max_tokens = max_tokens

# Instancia global del servicio
openai_service = OpenAIService()

def generate_response(message: str, context: List[Dict[str, str]] = None) -> str:
    """
    Función de conveniencia para generar respuestas
    """
    return openai_service.generate_response(message, context)

def generate_embedding(text: str) -> List[float]:
    """
    Función de conveniencia para generar embeddings
    """
    return openai_service.generate_embedding(text)

def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Función de conveniencia para generar embeddings en batch
    """
    return openai_service.generate_embeddings_batch(texts) 