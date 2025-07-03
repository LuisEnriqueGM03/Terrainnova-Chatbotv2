import os
import google.generativeai as genai
from typing import List, Dict, Any
from dotenv import load_dotenv
import logging
import sys
import json
import re

# Importar el servicio de base de datos
try:
    from .database_service import database_service, buscar_productos_chatbot, get_productos_info, get_productos_por_presupuesto_chatbot
except ImportError:
    # Fallback si no se puede importar
    database_service = None
    logger = logging.getLogger(__name__)
    logger.warning("No se pudo importar el servicio de base de datos")

load_dotenv()
load_dotenv("config.env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generar_system_prompt() -> str:
    prompt_base = """
Eres un asistente virtual especializado de TerraINNOVA, un emprendimiento ecológico boliviano líder en sostenibilidad ambiental.

📋 INFORMACIÓN DE LA EMPRESA:
• Nombre: TerraINNOVA  
• Ubicación: Santa Cruz de la Sierra, Bolivia
• Contacto: terrainnova@gmail.com
• Redes sociales: Instagram, Facebook, TikTok

🌱 QUÉ SOMOS:
TerraINNOVA es un emprendimiento ecológico boliviano que promueve la economía circular a través de la recolección, transformación y comercialización de residuos orgánicos en forma de compost 100% natural.

Somos una plataforma digital que conecta a hogares, viveros, agricultores e instituciones con soluciones sostenibles para el cuidado del suelo y del medio ambiente.

🎯 MISIÓN:
Ofrecer soluciones sostenibles para el manejo de residuos orgánicos mediante la producción y comercialización de compost 100% natural, a través de una plataforma digital que promueve la economía circular, fomenta la educación ambiental y facilita el acceso a productos ecológicos en Santa Cruz de la Sierra.

👁️ VISIÓN:
Ser una empresa reconocida como la entidad municipal líder en gestión integral de residuos sólidos de Bolivia, brindando servicios de calidad, con innovación tecnológica, sostenibilidad financiera, responsabilidad social y compromiso con las generaciones futuras.

✅ BENEFICIOS PARA CLIENTES:
• 🚚 Envío GRATIS en pedidos superiores a $300
• 🔒 Pago 100% seguro
• ↩️ Devolución garantizada en 30 días  
• 📞 Soporte técnico 24/7
• 🌱 Productos 100% naturales y ecológicos
"""

    if database_service and database_service.health_check():
        try:
            productos = database_service.get_productos()
            if productos:
                prompt_base += "\n🛍️ CATÁLOGO DE PRODUCTOS DISPONIBLES:\n"
                for producto in productos:
                    stock_text = "✅ Disponible" if producto.stock > 0 else "❌ Agotado"
                    prompt_base += f"\n• {producto.nombre} - {producto.precio:,.0f} Bs\n"
                    prompt_base += f"  Categoría: {producto.categoria_nombre or 'Sin categoría'}\n"
                    prompt_base += f"  Stock: {stock_text}\n"
                    prompt_base += f"  Descripción: {producto.descripcion}\n"
                    
                categorias = database_service.get_categorias()
                if categorias:
                    prompt_base += "\n🏷️ CATEGORÍAS DISPONIBLES:\n"
                    for categoria in categorias:
                        prompt_base += f"• {categoria.nombre}\n"
        except Exception as e:
            logger.error(f"Error obteniendo productos de la base de datos: {e}")
            prompt_base += "\n🛍️ CATÁLOGO: Productos disponibles (consulta en tiempo real)\n"
    else:
        prompt_base += "\n🛍️ CATÁLOGO: Productos disponibles (consulta en tiempo real)\n"
    
    # Agregar preguntas frecuentes básicas
    prompt_base += """
❓ PREGUNTAS FRECUENTES:

P: ¿Qué es el compost?
R: El compost es un abono orgánico que se obtiene de la descomposición controlada de residuos orgánicos como restos de comida, hojas y otros materiales naturales. Es rico en nutrientes y mejora la estructura del suelo.

P: ¿Cómo uso el compost en mi jardín?
R: Mezcla el compost con la tierra existente en proporción 1:3 (una parte de compost por tres de tierra). Para macetas, puedes usar hasta 50% compost. Aplica en primavera y otoño para mejores resultados.

P: ¿Para qué plantas sirve el compost?
R: Nuestro compost es universal y sirve para todo tipo de plantas: hortalizas, frutales, ornamentales, césped, plantas de interior. Es especialmente beneficioso para tomates, lechugas, rosas y plantas aromáticas.

P: ¿Cuánto tiempo dura el compost?
R: Nuestro compost puede durar hasta 2 años almacenado en lugar seco y ventilado. Una vez aplicado al suelo, sus beneficios duran entre 6-12 meses, mejorando gradualmente la fertilidad.
"""
    
    # Instrucciones para responder
    prompt_base += """
🎯 INSTRUCCIONES PARA RESPONDER:
1. Siempre mantén un tono amigable, profesional y orientado a la sostenibilidad
2. Prioriza la educación ambiental en tus respuestas
3. Destaca los beneficios ecológicos de nuestros productos
4. Cuando menciones productos, incluye precios y beneficios específicos
5. Si preguntan por productos similares, compara opciones disponibles
6. Para consultas de presupuesto, recomienda la mejor opción en ese rango
7. Promueve la economía circular y prácticas sostenibles
8. Responde en español (somos una empresa boliviana)
9. Si no tienes información específica, ofrece contactar con nuestro equipo

🎨 EJEMPLOS DE RESPUESTAS IDEALES:

Para consulta de productos:
"¡Hola! 👋 Para tu jardín te recomiendo nuestro Compost Premium TerraInnova (250 Bs) que mejora la estructura del suelo y aporta nutrientes esenciales. Es perfecto para jardines domésticos y huertos urbanos. Si buscas una opción más económica, tenemos el Compost Básico (150 Bs) ideal para áreas grandes. ¿Cuál se adapta mejor a tu proyecto?"

Para educación ambiental:
"¡Excelente pregunta! 🌱 El compostaje es fundamental para la economía circular. Al usar nuestro compost, no solo nutres tus plantas, sino que también contribuyes a reducir residuos orgánicos urbanos. En TerraINNOVA transformamos esos residuos en este abono 100% natural que regenera la tierra."

Para consultas de presupuesto:
"Con un presupuesto de 200 Bs, te recomiendo nuestro Compost Básico (150 Bs) que te permite cubrir más área, ideal para empezar tu jardín ecológico. Si puedes aumentar un poco, el Compost Premium (250 Bs) te dará resultados superiores y además calificas para envío gratis."
"""
    
    return prompt_base

SYSTEM_PROMPT = generar_system_prompt()

class GeminiService:
    def __init__(self):
        self.model = "gemini-1.5-flash"
        self.max_tokens = 1000
        self.temperature = 0.7
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "AIzaSyDSZ-hjz_PYfQlr_QBLmlbDW-mg5wSooK8":
            logger.error("GEMINI_API_KEY no está configurada. Por favor, configura tu clave en config.env")
            self.client = None
        else:
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.model)
            logger.info("Cliente Gemini configurado correctamente con contexto de TerraINNOVA")
    
    def generate_response(self, message: str, context: List[Dict[str, str]] = None) -> str:
        """
        Genera una respuesta usando la API de Google Gemini con contexto de TerraINNOVA y datos de la base de datos
        
        Args:
            message: El mensaje del usuario
            context: Lista de mensajes previos para mantener contexto
            
        Returns:
            str: La respuesta generada por la IA con conocimiento de TerraINNOVA
        """
        if not self.client:
            return "⚠️ Disculpa, nuestro asistente está temporalmente fuera de servicio. Por favor, contáctanos directamente en terrainnova@gmail.com"
        
        try:
            # Procesar consultas específicas de productos usando la base de datos
            enhanced_message = self._enhance_message_with_product_data(message)
            
            # Preparar el historial de conversación
            chat_history = []
            
            # Agregar el prompt del sistema al inicio
            chat_history.append({
                "role": "user", 
                "parts": [SYSTEM_PROMPT + "\n\nUsuario: " + enhanced_message]
            })
            
            # Agregar contexto previo si existe (últimos 10 mensajes para no sobrecargar)
            if context:
                recent_context = context[-10:] if len(context) > 10 else context
                for msg in recent_context:
                    if msg.get("role") == "user":
                        chat_history.append({"role": "user", "parts": [msg.get("content", "")]})
                    elif msg.get("role") == "assistant":
                        chat_history.append({"role": "assistant", "parts": [msg.get("content", "")]})
            
            # Si tenemos contexto, creamos chat con historial
            if len(chat_history) > 1:
                chat = self.client.start_chat(history=chat_history[1:])  # Excluir el prompt del sistema
                response = chat.send_message(SYSTEM_PROMPT + "\n\nUsuario: " + enhanced_message)
            else:
                # Primera interacción, enviar mensaje con prompt del sistema
                response = self.client.generate_content(SYSTEM_PROMPT + "\n\nUsuario: " + enhanced_message)
            
            # Extraer y retornar la respuesta
            generated_text = response.text.strip()
            
            # Validar que la respuesta no esté vacía
            if not generated_text:
                return "🤖 Disculpa, estoy procesando tu consulta. ¿Podrías reformular la pregunta? Si necesitas ayuda inmediata, contáctanos en terrainnova@gmail.com"
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Error generando respuesta: {str(e)}")
            return f"🔧 Disculpa, hubo un problema técnico. Para asistencia inmediata, contáctanos en terrainnova@gmail.com o llámanos para soporte 24/7."
    
    def _enhance_message_with_product_data(self, message: str) -> str:
        """
        Mejora el mensaje del usuario con datos específicos de productos desde la base de datos
        """
        if not database_service or not database_service.health_check():
            return message
        
        try:
            message_lower = message.lower()
            enhanced_message = message
            
            # Detectar consultas de búsqueda de productos
            search_patterns = [
                r'busco?\s+(.+)',
                r'quiero\s+(.+)',
                r'necesito\s+(.+)',
                r'tienes?\s+(.+)',
                r'productos?\s+de\s+(.+)',
                r'me\s+recomiendan?\s+(.+)',
                r'(.+)\s+disponible',
            ]
            
            for pattern in search_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    search_term = match.group(1).strip()
                    # Filtrar palabras comunes que no son útiles para búsqueda
                    if len(search_term) > 2 and search_term not in ['algo', 'ayuda', 'información', 'que', 'para']:
                        producto_info = buscar_productos_chatbot(search_term)
                        if "No encontré productos" not in producto_info:
                            enhanced_message += f"\n\n[PRODUCTOS ENCONTRADOS]: {producto_info}"
                        break
            
            # Detectar consultas de presupuesto
            budget_patterns = [
                r'presupuesto\s+de\s+\$?(\d+)',
                r'tengo\s+\$?(\d+)',
                r'hasta\s+\$?(\d+)',
                r'máximo\s+\$?(\d+)',
                r'con\s+\$?(\d+)',
            ]
            
            for pattern in budget_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    budget = float(match.group(1))
                    producto_info = get_productos_por_presupuesto_chatbot(budget)
                    enhanced_message += f"\n\n[PRODUCTOS EN PRESUPUESTO]: {producto_info}"
                    break
            
            # Detectar solicitudes de catálogo completo
            catalog_patterns = [
                r'productos?\s+disponibles?',
                r'qué\s+venden?',
                r'catálogo',
                r'lista\s+de\s+productos?',
                r'todo\s+lo\s+que\s+tienen?',
                r'productos?\s+que\s+ofrecen?'
            ]
            
            for pattern in catalog_patterns:
                if re.search(pattern, message_lower):
                    productos_info = get_productos_info()
                    enhanced_message += f"\n\n[CATÁLOGO COMPLETO]: {productos_info}"
                    break
            
            # Detectar consultas específicas por número/ID
            id_pattern = r'producto\s+(\d+)'
            match = re.search(id_pattern, message_lower)
            if match:
                producto_id = int(match.group(1))
                producto = database_service.get_producto_by_id(producto_id)
                if producto:
                    producto_info = database_service.format_producto_para_chatbot(producto)
                    enhanced_message += f"\n\n[PRODUCTO ESPECÍFICO]: {producto_info}"
            
            return enhanced_message
            
        except Exception as e:
            logger.error(f"Error mejorando mensaje con datos de productos: {e}")
            return message
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Genera un embedding vectorial para un texto usando Gemini
        
        Args:
            text: El texto para generar el embedding
            
        Returns:
            List[float]: Vector de embedding
        """
        if not self.client:
            logger.error("Gemini no está configurado para generar embeddings")
            return [0.0] * 768  # Vector de ceros como fallback
        
        try:
            # Validar que el texto no esté vacío
            if not text or not text.strip():
                logger.warning("Texto vacío proporcionado para generar embedding")
                return [0.0] * 768
            
            # Limpiar y truncar el texto si es muy largo
            cleaned_text = text.strip()
            if len(cleaned_text) > 8192:
                cleaned_text = cleaned_text[:8192]
                logger.info(f"Texto truncado a 8192 caracteres para generar embedding")
            
            # Generar embedding usando el modelo de embeddings de Gemini
            embedding_model = genai.get_model("models/embedding-001")
            result = embedding_model.embed_content(cleaned_text)
            
            # Extraer el vector de embedding
            embedding = result.embedding
            
            logger.info(f"Embedding generado exitosamente para texto de {len(cleaned_text)} caracteres")
            return embedding
            
        except Exception as e:
            logger.error(f"Error inesperado al generar embedding: {str(e)}")
            return [0.0] * 768
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para múltiples textos en una sola llamada
        
        Args:
            texts: Lista de textos para generar embeddings
            
        Returns:
            List[List[float]]: Lista de vectores de embedding
        """
        if not self.client:
            logger.error("Gemini no está configurado para generar embeddings")
            return [[0.0] * 768] * len(texts)
        
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
            
            # Generar embeddings usando el modelo de embeddings de Gemini
            embedding_model = genai.get_model("models/embedding-001")
            result = embedding_model.embed_content(processed_texts)
            
            # Extraer todos los embeddings
            embeddings = result.embedding
            
            logger.info(f"Embeddings generados exitosamente para {len(embeddings)} textos")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error al generar embeddings en batch: {str(e)}")
            return [[0.0] * 768] * len(texts)
    
    def set_model(self, model: str):
        """Cambiar el modelo de Gemini"""
        self.model = model
        if self.client:
            self.client = genai.GenerativeModel(self.model)
    
    def set_temperature(self, temperature: float):
        """Ajustar la temperatura de generación"""
        self.temperature = temperature
    
    def set_max_tokens(self, max_tokens: int):
        """Ajustar el número máximo de tokens"""
        self.max_tokens = max_tokens

# Instancia global del servicio
gemini_service = GeminiService()

def generate_response(message: str, context: List[Dict[str, str]] = None) -> str:
    """
    Función de conveniencia para generar respuestas
    """
    return gemini_service.generate_response(message, context)

def generate_embedding(text: str) -> List[float]:
    """
    Función de conveniencia para generar embeddings
    """
    return gemini_service.generate_embedding(text)

def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Función de conveniencia para generar embeddings en batch
    """
    return gemini_service.generate_embeddings_batch(texts) 