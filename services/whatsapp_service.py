import os
import requests
import hmac
import hashlib
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsAppService:
    """
    Servicio para interactuar con WhatsApp Business API
    """
    
    def __init__(self):
        # Configuración de WhatsApp Business API
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        self.app_secret = os.getenv("WHATSAPP_APP_SECRET")
        
        # URL base de la API
        self.api_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"
        
        # Verificar configuración
        if not all([self.access_token, self.phone_number_id, self.verify_token]):
            logger.error("Configuración de WhatsApp incompleta. Revisa las variables de entorno.")
            self.configured = False
        else:
            self.configured = True
            logger.info("Servicio de WhatsApp configurado correctamente")
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verifica el webhook de WhatsApp
        
        Args:
            mode: Modo de verificación
            token: Token de verificación
            challenge: Challenge code
            
        Returns:
            str: Challenge code si la verificación es exitosa, None en caso contrario
        """
        if mode == "subscribe" and token == self.verify_token:
            logger.info("Webhook verificado exitosamente")
            return challenge
        else:
            logger.warning("Verificación de webhook fallida")
            return None
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verifica la firma del webhook para seguridad
        
        Args:
            payload: Cuerpo del mensaje como bytes
            signature: Firma proporcionada por WhatsApp
            
        Returns:
            bool: True si la firma es válida
        """
        if not self.app_secret:
            logger.warning("APP_SECRET no configurado, saltando verificación de firma")
            return True
        
        try:
            # Crear firma HMAC
            expected_signature = hmac.new(
                self.app_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # WhatsApp envía la firma como "sha256=<hash>"
            signature_hash = signature.replace("sha256=", "")
            
            return hmac.compare_digest(expected_signature, signature_hash)
        except Exception as e:
            logger.error(f"Error verificando firma: {e}")
            return False
    
    def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        """
        Envía un mensaje de texto a WhatsApp
        
        Args:
            to: Número de teléfono del destinatario
            message: Texto del mensaje
            
        Returns:
            Dict: Respuesta de la API
        """
        if not self.configured:
            return {"error": "WhatsApp no está configurado"}
        
        url = f"{self.api_url}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Mensaje enviado exitosamente a {to}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error enviando mensaje a WhatsApp: {e}")
            return {"error": str(e)}
    
    def send_media_message(self, to: str, media_type: str, media_url: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """
        Envía un mensaje con media (imagen, video, documento)
        
        Args:
            to: Número de teléfono del destinatario
            media_type: Tipo de media (image, video, document)
            media_url: URL del archivo media
            caption: Texto adicional (opcional)
            
        Returns:
            Dict: Respuesta de la API
        """
        if not self.configured:
            return {"error": "WhatsApp no está configurado"}
        
        url = f"{self.api_url}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": media_type,
            media_type: {
                "link": media_url
            }
        }
        
        if caption and media_type in ["image", "video", "document"]:
            payload[media_type]["caption"] = caption
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Media {media_type} enviado exitosamente a {to}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error enviando media a WhatsApp: {e}")
            return {"error": str(e)}
    
    def send_template_message(self, to: str, template_name: str, language_code: str = "es") -> Dict[str, Any]:
        """
        Envía un mensaje de plantilla
        
        Args:
            to: Número de teléfono del destinatario
            template_name: Nombre de la plantilla
            language_code: Código de idioma
            
        Returns:
            Dict: Respuesta de la API
        """
        if not self.configured:
            return {"error": "WhatsApp no está configurado"}
        
        url = f"{self.api_url}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Plantilla {template_name} enviada exitosamente a {to}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error enviando plantilla a WhatsApp: {e}")
            return {"error": str(e)}
    
    def mark_message_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Marca un mensaje como leído
        
        Args:
            message_id: ID del mensaje
            
        Returns:
            Dict: Respuesta de la API
        """
        if not self.configured:
            return {"error": "WhatsApp no está configurado"}
        
        url = f"{self.api_url}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Mensaje {message_id} marcado como leído")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error marcando mensaje como leído: {e}")
            return {"error": str(e)}
    
    def process_webhook_message(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Procesa un mensaje entrante del webhook
        
        Args:
            webhook_data: Datos del webhook
            
        Returns:
            Dict: Información del mensaje procesado o None si no hay mensaje
        """
        try:
            # Verificar estructura del webhook
            if "entry" not in webhook_data:
                return None
            
            for entry in webhook_data["entry"]:
                if "changes" not in entry:
                    continue
                
                for change in entry["changes"]:
                    value = change.get("value", {})
                    
                    # Procesar mensajes
                    if "messages" in value:
                        for message in value["messages"]:
                            # Extraer información del mensaje
                            message_info = {
                                "id": message.get("id"),
                                "from": message.get("from"),
                                "timestamp": message.get("timestamp"),
                                "type": message.get("type"),
                                "message_data": {}
                            }
                            
                            # Extraer contenido según el tipo
                            if message["type"] == "text":
                                message_info["message_data"] = {
                                    "body": message.get("text", {}).get("body", "")
                                }
                            elif message["type"] == "image":
                                message_info["message_data"] = {
                                    "caption": message.get("image", {}).get("caption", ""),
                                    "media_id": message.get("image", {}).get("id", "")
                                }
                            elif message["type"] == "document":
                                message_info["message_data"] = {
                                    "caption": message.get("document", {}).get("caption", ""),
                                    "filename": message.get("document", {}).get("filename", ""),
                                    "media_id": message.get("document", {}).get("id", "")
                                }
                            elif message["type"] == "voice":
                                message_info["message_data"] = {
                                    "media_id": message.get("voice", {}).get("id", "")
                                }
                            
                            # Extraer información de contacto
                            if "contacts" in value:
                                contact = value["contacts"][0]
                                message_info["contact"] = {
                                    "name": contact.get("profile", {}).get("name", ""),
                                    "wa_id": contact.get("wa_id", "")
                                }
                            
                            # Marcar mensaje como leído
                            if message_info["id"]:
                                self.mark_message_as_read(message_info["id"])
                            
                            return message_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error procesando mensaje del webhook: {e}")
            return None
    
    def health_check(self) -> bool:
        """
        Verifica la conectividad con WhatsApp Business API
        
        Returns:
            bool: True si la configuración es válida
        """
        return self.configured

# Instancia global del servicio
whatsapp_service = WhatsAppService()

# Funciones de conveniencia
def verify_webhook(mode: str, token: str, challenge: str) -> Optional[str]:
    """Función de conveniencia para verificar webhook"""
    return whatsapp_service.verify_webhook(mode, token, challenge)

def send_whatsapp_message(to: str, message: str) -> Dict[str, Any]:
    """Función de conveniencia para enviar mensaje"""
    return whatsapp_service.send_text_message(to, message)

def process_whatsapp_webhook(webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Función de conveniencia para procesar webhook"""
    return whatsapp_service.process_webhook_message(webhook_data) 