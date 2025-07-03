from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from models.message import MessageRequest
from services.gemini_service import generate_response, gemini_service, generate_embedding
from services.redis_service import get_context, save_context, redis_service
from services.pdf_service import extract_text_from_pdf, pdf_service
from services.qdrant_service import qdrant_service, init_collection, upsert_document, semantic_search
from services.whatsapp_service import whatsapp_service, verify_webhook, send_whatsapp_message, process_whatsapp_webhook
from services.database_service import database_service
import os
import uuid
from typing import List
from dotenv import load_dotenv
import re

load_dotenv()
load_dotenv("config.env")

app = FastAPI(
    title="TerraInnova AI Chatbot Microservice",
    description="Microservicio de IA para chatbot omnicanal con soporte para WhatsApp, web, PDF y búsqueda semántica",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "TerraInnova AI Chatbot Microservice",
        "version": "1.0.0",
        "status": "running",
        "features": ["chat", "pdf_processing", "semantic_search", "whatsapp_webhook"]
    }

@app.get("/health")
async def health_check():
    redis_healthy = redis_service.health_check()
    qdrant_healthy = qdrant_service.health_check()
    whatsapp_healthy = whatsapp_service.health_check()
    database_healthy = database_service.health_check()
    
    return {
        "status": "healthy" if redis_healthy and qdrant_healthy and whatsapp_healthy and database_healthy else "degraded",
        "services": {
            "redis": "healthy" if redis_healthy else "unhealthy",
            "qdrant": "healthy" if qdrant_healthy else "unhealthy",
            "gemini": "configured" if os.getenv("GEMINI_API_KEY") else "not_configured",
            "whatsapp": "configured" if whatsapp_healthy else "not_configured",
            "database": "healthy" if database_healthy else "unhealthy"
        }
    }

# --- NUEVO: función para obtener imagen de producto relevante ---
def obtener_imagen_producto(msg, reply):
    """Busca la imagen de un producto relevante según el mensaje o la respuesta."""
    productos = database_service.get_productos()
    mensaje = msg.message.lower()
    respuesta = reply.lower() if reply else ""
    # Buscar por nombre de producto en el mensaje o respuesta
    for producto in productos:
        if producto.nombre and (producto.nombre.lower() in mensaje or producto.nombre.lower() in respuesta):
            return producto.imagenUrl
    # Buscar por ID de producto en el mensaje
    match = re.search(r'producto\s+(\d+)', mensaje)
    if match:
        producto_id = int(match.group(1))
        producto = database_service.get_producto_by_id(producto_id)
        if producto and producto.imagenUrl:
            return producto.imagenUrl
    return None

@app.post("/chat")
async def chat_endpoint(msg: MessageRequest):
    try:
        if not msg.message.strip():
            raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")
        
        context = get_context(msg.user_id)
        reply = generate_response(msg.message, context)
        save_context(msg.user_id, msg.message, reply)

        # Modular: Si el usuario pide una foto o imagen, o si la respuesta es de producto, busca la imagen
        imagen_url = None
        if any(word in msg.message.lower() for word in ["foto", "imagen", "muéstrame una foto", "ver foto"]):
            imagen_url = obtener_imagen_producto(msg, reply)
        else:
            # También busca imagen si el mensaje es sobre producto por ID
            imagen_url = obtener_imagen_producto(msg, reply)

        return {
            "reply": reply,
            "user_id": msg.user_id,
            "context_length": len(context) + 2,
            "imagenUrl": imagen_url
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    doc_name: str = Form(None)
):
    """
    Endpoint para subir y procesar archivos PDF
    
    Args:
        file: Archivo PDF a procesar
        user_id: ID del usuario que sube el archivo
        doc_name: Nombre opcional del documento
        
    Returns:
        JSON con el texto extraído y metadatos
    """
    try:
        # Validar tipo de archivo
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
        
        # Leer contenido del archivo
        pdf_content = await file.read()
        
        # Validar que es un PDF válido
        if not pdf_service.is_valid_pdf(pdf_content):
            raise HTTPException(status_code=400, detail="El archivo no es un PDF válido")
        
        # Extraer texto del PDF
        extracted_text = extract_text_from_pdf(pdf_content)
        
        if not extracted_text:
            raise HTTPException(status_code=400, detail="No se pudo extraer texto del PDF")
        
        # Obtener información del PDF
        pdf_info = pdf_service.get_pdf_info(pdf_content)
        
        # Generar ID único para el documento
        doc_id = str(uuid.uuid4())
        
        # Guardar en Qdrant (si está disponible)
        qdrant_success = False
        if qdrant_service.health_check():
            try:
                # Generar embedding real del texto usando Gemini
                embedding = generate_embedding(extracted_text)
                
                qdrant_success = upsert_document(
                    doc_id=doc_id,
                    content=extracted_text,
                    embedding=embedding,  # Embedding real generado
                    metadata={
                        "user_id": user_id,
                        "filename": file.filename,
                        "doc_name": doc_name or file.filename,
                        "pages": pdf_info["pages"],
                        "upload_timestamp": str(uuid.uuid4())  # Placeholder para timestamp
                    }
                )
            except Exception as e:
                print(f"Error al guardar en Qdrant: {e}")
        
        return {
            "doc_id": doc_id,
            "filename": file.filename,
            "doc_name": doc_name or file.filename,
            "text_length": len(extracted_text),
            "pages": pdf_info["pages"],
            "extracted_text": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
            "qdrant_saved": qdrant_success,
            "user_id": user_id,
            "embedding_generated": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando PDF: {str(e)}")

@app.post("/search-documents")
async def search_documents(query: str, top_k: int = 3):
    """
    Endpoint para búsqueda semántica en documentos
    
    Args:
        query: Consulta de búsqueda
        top_k: Número máximo de resultados
        
    Returns:
        JSON con los documentos más relevantes
    """
    try:
        if not qdrant_service.health_check():
            raise HTTPException(status_code=503, detail="Servicio de búsqueda no disponible")
        
        # Validar que la consulta no esté vacía
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="La consulta no puede estar vacía")
        
        # Generar embedding real de la consulta usando Gemini
        query_embedding = generate_embedding(query.strip())
        
        # Realizar búsqueda semántica
        results = semantic_search(query_embedding, top_k)
        
        return {
            "query": query,
            "results": results,
            "total_results": len(results),
            "embedding_generated": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")

@app.get("/documents/{user_id}")
async def get_user_documents(user_id: str):
    """
    Obtiene los documentos de un usuario
    
    Args:
        user_id: ID del usuario
        
    Returns:
        JSON con la lista de documentos del usuario
    """
    try:
        if not qdrant_service.health_check():
            raise HTTPException(status_code=503, detail="Servicio de documentos no disponible")
        
        # Aquí implementarías la búsqueda de documentos por usuario
        # Por ahora, retornamos un placeholder
        return {
            "user_id": user_id,
            "documents": [],
            "message": "Funcionalidad en desarrollo"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo documentos: {str(e)}")

@app.get("/productos")
async def get_productos():
    """
    Obtiene todos los productos desde la base de datos
    
    Returns:
        JSON con la lista de productos disponibles
    """
    try:
        if not database_service.health_check():
            raise HTTPException(status_code=503, detail="Servicio de base de datos no disponible")
        
        productos = database_service.get_productos()
        productos_json = []
        
        for producto in productos:
            productos_json.append({
                "id": producto.id,
                "nombre": producto.nombre,
                "descripcion": producto.descripcion,
                "precio": producto.precio,
                "stock": producto.stock,
                "imagenUrl": producto.imagenUrl,
                "categoria_id": producto.categoria_id,
                "categoria_nombre": producto.categoria_nombre
            })
        
        return {
            "productos": productos_json,
            "total": len(productos_json),
            "mensaje": f"Se encontraron {len(productos_json)} productos"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo productos: {str(e)}")

@app.get("/productos/buscar")
async def buscar_productos(q: str):
    """
    Busca productos por término de búsqueda
    
    Args:
        q: Término de búsqueda
        
    Returns:
        JSON con los productos encontrados
    """
    try:
        if not database_service.health_check():
            raise HTTPException(status_code=503, detail="Servicio de base de datos no disponible")
        
        if not q or len(q.strip()) < 2:
            raise HTTPException(status_code=400, detail="El término de búsqueda debe tener al menos 2 caracteres")
        
        productos = database_service.search_productos(q.strip())
        productos_json = []
        
        for producto in productos:
            productos_json.append({
                "id": producto.id,
                "nombre": producto.nombre,
                "descripcion": producto.descripcion,
                "precio": producto.precio,
                "stock": producto.stock,
                "imagenUrl": producto.imagenUrl,
                "categoria_id": producto.categoria_id,
                "categoria_nombre": producto.categoria_nombre
            })
        
        return {
            "productos": productos_json,
            "total": len(productos_json),
            "consulta": q,
            "mensaje": f"Se encontraron {len(productos_json)} productos para '{q}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error buscando productos: {str(e)}")

@app.get("/categorias")
async def get_categorias():
    """
    Obtiene todas las categorías desde la base de datos
    
    Returns:
        JSON con la lista de categorías disponibles
    """
    try:
        if not database_service.health_check():
            raise HTTPException(status_code=503, detail="Servicio de base de datos no disponible")
        
        categorias = database_service.get_categorias()
        categorias_json = []
        
        for categoria in categorias:
            categorias_json.append({
                "id": categoria.id,
                "nombre": categoria.nombre
            })
        
        return {
            "categorias": categorias_json,
            "total": len(categorias_json),
            "mensaje": f"Se encontraron {len(categorias_json)} categorías"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo categorías: {str(e)}")

@app.delete("/chat/{user_id}/context")
async def clear_chat_context(user_id: str):
    """
    Limpia el contexto de conversación de un usuario
    
    Args:
        user_id: ID del usuario
        
    Returns:
        JSON confirmando la limpieza
    """
    try:
        success = redis_service.clear_context(user_id)
        if success:
            return {"message": f"Contexto limpiado para el usuario {user_id}"}
        else:
            raise HTTPException(status_code=500, detail="Error al limpiar el contexto")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.get("/chat/{user_id}/context")
async def get_chat_context(user_id: str):
    """
    Obtiene el contexto de conversación de un usuario
    
    Args:
        user_id: ID del usuario
        
    Returns:
        JSON con el contexto de conversación
    """
    try:
        context = get_context(user_id)
        return {
            "user_id": user_id,
            "context": context,
            "message_count": len(context)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.post("/whatsapp/send-message")
async def send_whatsapp_message_endpoint(request: Request):
    """
    Envía un mensaje manual a WhatsApp
    
    Body:
        to: Número de teléfono del destinatario
        message: Texto del mensaje
        
    Returns:
        JSON con el resultado del envío
    """
    try:
        data = await request.json()
        to = data.get("to")
        message = data.get("message")
        
        if not to or not message:
            raise HTTPException(status_code=400, detail="Los campos 'to' y 'message' son requeridos")
        
        # Enviar mensaje usando el servicio de WhatsApp
        result = send_whatsapp_message(to, message)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=f"Error enviando mensaje: {result['error']}")
        
        return {
            "status": "sent",
            "to": to,
            "message": message,
            "whatsapp_response": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.post("/whatsapp/send-media")
async def send_whatsapp_media_endpoint(request: Request):
    """
    Envía un mensaje con media (imagen, video, documento) a WhatsApp
    
    Body:
        to: Número de teléfono del destinatario
        media_type: Tipo de media (image, video, document)
        media_url: URL del archivo
        caption: Texto adicional (opcional)
        
    Returns:
        JSON con el resultado del envío
    """
    try:
        data = await request.json()
        to = data.get("to")
        media_type = data.get("media_type")
        media_url = data.get("media_url")
        caption = data.get("caption", "")
        
        if not all([to, media_type, media_url]):
            raise HTTPException(status_code=400, detail="Los campos 'to', 'media_type' y 'media_url' son requeridos")
        
        if media_type not in ["image", "video", "document"]:
            raise HTTPException(status_code=400, detail="media_type debe ser 'image', 'video' o 'document'")
        
        # Enviar media usando el servicio de WhatsApp
        result = whatsapp_service.send_media_message(to, media_type, media_url, caption)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=f"Error enviando media: {result['error']}")
        
        return {
            "status": "sent",
            "to": to,
            "media_type": media_type,
            "media_url": media_url,
            "caption": caption,
            "whatsapp_response": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(request: Request):
    try:
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        
        challenge_response = verify_webhook(mode, token, challenge)
        
        if challenge_response:
            return int(challenge_response)
        else:
            raise HTTPException(status_code=403, detail="Forbidden")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verificando webhook: {str(e)}")

@app.get("/webhook")
async def webhook_verify_main(request: Request):
    try:
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        
        print(f"Verificación webhook - Mode: {mode}, Token: {token}, Challenge: {challenge}")
        
        challenge_response = verify_webhook(mode, token, challenge)
        
        if challenge_response:
            print(f"Webhook verificado correctamente, enviando challenge: {challenge_response}")
            return int(challenge_response)
        else:
            print("Webhook verificación falló - token incorrecto")
            raise HTTPException(status_code=403, detail="Forbidden")
            
    except Exception as e:
        print(f"Error verificando webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error verificando webhook: {str(e)}")

@app.post("/webhook/whatsapp")
async def whatsapp_webhook_receive(request: Request):
    """
    Webhook para recibir mensajes de WhatsApp Business API
    """
    try:
        # Verificar firma del webhook (si está configurada)
        signature = request.headers.get("X-Hub-Signature-256", "")
        raw_body = await request.body()
        
        if signature and not whatsapp_service.verify_signature(raw_body, signature):
            raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Obtener datos del webhook
        data = await request.json()
        
        # Procesar el mensaje usando el servicio de WhatsApp
        message_info = process_whatsapp_webhook(data)
        
        if message_info and message_info.get("type") == "text":
            # Extraer información del mensaje
            from_number = message_info.get("from")
            message_text = message_info.get("message_data", {}).get("body", "")
            contact_name = message_info.get("contact", {}).get("name", "Usuario")
            
            if message_text and from_number:
                # Obtener contexto previo del usuario
                context = get_context(from_number)
                
                # Generar respuesta usando Gemini
                ai_response = generate_response(message_text, context)
                
                # Guardar el nuevo contexto en Redis
                save_context(from_number, message_text, ai_response)
                
                # Enviar respuesta de vuelta a WhatsApp
                whatsapp_response = send_whatsapp_message(from_number, ai_response)
                
                return {
                    "status": "processed",
                    "message_id": message_info.get("id"),
                    "from": from_number,
                    "contact_name": contact_name,
                    "message": message_text,
                    "ai_response": ai_response,
                    "whatsapp_sent": "error" not in whatsapp_response,
                    "context_length": len(context) + 2
                }
        
        # Si no es un mensaje de texto o no se pudo procesar
        return {"status": "received_but_not_processed", "data": data}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando webhook: {str(e)}")

@app.post("/webhook")
async def webhook_receive_main(request: Request):
    """
    Webhook principal para recibir mensajes de WhatsApp Business API
    """
    try:
        # Verificar firma del webhook (si está configurada)
        signature = request.headers.get("X-Hub-Signature-256", "")
        raw_body = await request.body()
        
        print(f"Webhook POST recibido - Signature: {signature[:20] if signature else 'N/A'}...")
        
        if signature and not whatsapp_service.verify_signature(raw_body, signature):
            raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Obtener datos del webhook
        data = await request.json()
        print(f"Datos del webhook: {data}")
        
        # Procesar el mensaje usando el servicio de WhatsApp
        message_info = process_whatsapp_webhook(data)
        
        if message_info and message_info.get("type") == "text":
            # Extraer información del mensaje
            from_number = message_info.get("from")
            message_text = message_info.get("message_data", {}).get("body", "")
            contact_name = message_info.get("contact", {}).get("name", "Usuario")
            
            print(f"Mensaje recibido de {from_number} ({contact_name}): {message_text}")
            
            if message_text and from_number:
                # Obtener contexto previo del usuario
                context = get_context(from_number)
                
                # Generar respuesta usando Gemini
                ai_response = generate_response(message_text, context)
                
                # Guardar el nuevo contexto en Redis
                save_context(from_number, message_text, ai_response)
                
                # Enviar respuesta de vuelta a WhatsApp
                whatsapp_response = send_whatsapp_message(from_number, ai_response)
                
                print(f"Respuesta enviada: {ai_response}")
                
                return {
                    "status": "processed",
                    "message_id": message_info.get("id"),
                    "from": from_number,
                    "contact_name": contact_name,
                    "message": message_text,
                    "ai_response": ai_response,
                    "whatsapp_sent": "error" not in whatsapp_response,
                    "context_length": len(context) + 2
                }
        
        # Si no es un mensaje de texto o no se pudo procesar
        print("Mensaje recibido pero no procesado")
        return {"status": "received_but_not_processed", "data": data}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error procesando webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error procesando webhook: {str(e)}")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Manejador global de excepciones"""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error interno del servidor: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    
    # Obtener configuración del servidor desde variables de entorno
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 3000))
    
    print(f"🚀 Iniciando servidor TerraInnova AI en {host}:{port}")
    print(f"📍 Endpoints disponibles:")
    print(f"   • GET  {host}:{port}/")
    print(f"   • GET  {host}:{port}/health")
    print(f"   • POST {host}:{port}/chat")
    print(f"   • GET  {host}:{port}/webhook")
    print(f"   • POST {host}:{port}/webhook")
    print(f"   • GET  {host}:{port}/webhook/whatsapp")
    print(f"   • POST {host}:{port}/webhook/whatsapp")
    
    # Configuración para desarrollo
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
