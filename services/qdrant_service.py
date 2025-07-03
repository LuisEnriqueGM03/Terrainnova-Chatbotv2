import os
from typing import List, Dict, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QdrantService:
    """
    Servicio para interactuar con Qdrant para búsqueda semántica
    """
    
    def __init__(self):
        # Obtener configuración desde variables de entorno
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection_name = os.getenv("QDRANT_COLLECTION", "documents")
        self.vector_size = int(os.getenv("QDRANT_VECTOR_SIZE", "1536"))  # OpenAI ada-002 embedding size
        
        # Inicializar cliente Qdrant
        try:
            self.client = QdrantClient(self.qdrant_url)
            logger.info(f"Conectado a Qdrant en: {self.qdrant_url}")
        except Exception as e:
            logger.error(f"Error al conectar con Qdrant: {str(e)}")
            self.client = None
    
    def init_collection(self) -> bool:
        """
        Crea una colección si no existe
        
        Returns:
            bool: True si la colección se creó o ya existe
        """
        try:
            if not self.client:
                logger.error("Cliente Qdrant no disponible")
                return False
            
            # Verificar si la colección ya existe
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name in collection_names:
                logger.info(f"Colección '{self.collection_name}' ya existe")
                return True
            
            # Crear nueva colección
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"Colección '{self.collection_name}' creada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al inicializar colección: {str(e)}")
            return False
    
    def upsert_document(self, doc_id: str, content: str, embedding: List[float], metadata: Dict = None) -> bool:
        """
        Guarda un documento con su vector de embedding
        
        Args:
            doc_id: ID único del documento
            content: Contenido del documento
            embedding: Vector de embedding del documento
            metadata: Metadatos adicionales del documento
            
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            if not self.client:
                logger.error("Cliente Qdrant no disponible")
                return False
            
            # Verificar que la colección existe
            if not self._collection_exists():
                if not self.init_collection():
                    return False
            
            # Preparar metadatos
            doc_metadata = {
                "content": content,
                "doc_id": doc_id,
                "content_length": len(content)
            }
            
            if metadata:
                doc_metadata.update(metadata)
            
            # Crear punto para Qdrant
            point = PointStruct(
                id=doc_id,
                vector=embedding,
                payload=doc_metadata
            )
            
            # Insertar o actualizar el documento
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Documento '{doc_id}' guardado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al guardar documento '{doc_id}': {str(e)}")
            return False
    
    def semantic_search(self, query_embedding: List[float], top_k: int = 3, score_threshold: float = 0.7) -> List[Dict]:
        """
        Busca los documentos más similares a una consulta
        
        Args:
            query_embedding: Vector de embedding de la consulta
            top_k: Número máximo de resultados
            score_threshold: Umbral mínimo de similitud (0-1)
            
        Returns:
            List[Dict]: Lista de documentos encontrados con sus scores
        """
        try:
            if not self.client:
                logger.error("Cliente Qdrant no disponible")
                return []
            
            # Realizar búsqueda
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold
            )
            
            # Formatear resultados
            results = []
            for result in search_results:
                results.append({
                    "doc_id": result.payload.get("doc_id"),
                    "content": result.payload.get("content"),
                    "score": result.score,
                    "metadata": {k: v for k, v in result.payload.items() 
                               if k not in ["doc_id", "content"]}
                })
            
            logger.info(f"Búsqueda semántica completada: {len(results)} resultados")
            return results
            
        except Exception as e:
            logger.error(f"Error en búsqueda semántica: {str(e)}")
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Elimina un documento de la colección
        
        Args:
            doc_id: ID del documento a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            if not self.client:
                logger.error("Cliente Qdrant no disponible")
                return False
            
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[doc_id]
            )
            
            logger.info(f"Documento '{doc_id}' eliminado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al eliminar documento '{doc_id}': {str(e)}")
            return False
    
    def get_collection_info(self) -> Dict:
        """
        Obtiene información de la colección
        
        Returns:
            Dict: Información de la colección
        """
        try:
            if not self.client:
                return {"error": "Cliente Qdrant no disponible"}
            
            info = self.client.get_collection(self.collection_name)
            return {
                "name": info.name,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance,
                "points_count": info.points_count
            }
            
        except Exception as e:
            logger.error(f"Error al obtener información de la colección: {str(e)}")
            return {"error": str(e)}
    
    def clear_collection(self) -> bool:
        """
        Limpia toda la colección
        
        Returns:
            bool: True si se limpió correctamente
        """
        try:
            if not self.client:
                logger.error("Cliente Qdrant no disponible")
                return False
            
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="doc_id",
                            match=MatchValue(value="*")
                        )
                    ]
                )
            )
            
            logger.info(f"Colección '{self.collection_name}' limpiada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al limpiar colección: {str(e)}")
            return False
    
    def health_check(self) -> bool:
        """
        Verifica la conectividad con Qdrant
        
        Returns:
            bool: True si Qdrant está disponible
        """
        try:
            if not self.client:
                return False
            
            # Intentar obtener información de la colección
            self.client.get_collections()
            return True
            
        except Exception:
            return False
    
    def _collection_exists(self) -> bool:
        """
        Verifica si la colección existe
        
        Returns:
            bool: True si la colección existe
        """
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            return self.collection_name in collection_names
        except Exception:
            return False

# Instancia global del servicio
qdrant_service = QdrantService()

def init_collection() -> bool:
    """
    Función de conveniencia para inicializar colección
    """
    return qdrant_service.init_collection()

def upsert_document(doc_id: str, content: str, embedding: List[float], metadata: Dict = None) -> bool:
    """
    Función de conveniencia para guardar documento
    """
    return qdrant_service.upsert_document(doc_id, content, embedding, metadata)

def semantic_search(query_embedding: List[float], top_k: int = 3) -> List[Dict]:
    """
    Función de conveniencia para búsqueda semántica
    """
    return qdrant_service.semantic_search(query_embedding, top_k) 