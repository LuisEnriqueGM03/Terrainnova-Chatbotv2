# 📱 Integración con WhatsApp Business API

Esta guía te ayudará a configurar completamente la integración con WhatsApp Business API para el chatbot de TerraInnova.

## 🔧 Configuración Requerida

### 1. Obtener Credenciales de WhatsApp Business API

#### Paso 1: Crear una aplicación en Meta for Developers

1. Ve a [Meta for Developers](https://developers.facebook.com/)
2. Inicia sesión con tu cuenta de Meta/Facebook
3. Haz clic en "Crear aplicación"
4. Selecciona "Empresa" como tipo de aplicación
5. Completa los datos de la aplicación

#### Paso 2: Configurar WhatsApp Business API

1. En el panel de tu aplicación, busca "WhatsApp" y haz clic en "Configurar"
2. Sigue las instrucciones para configurar WhatsApp Business API
3. Añade un número de teléfono para pruebas

#### Paso 3: Obtener las credenciales necesarias

Necesitarás estos valores para el archivo `config.env`:

- **ACCESS_TOKEN**: Token de acceso temporal desde la consola de Meta
- **PHONE_NUMBER_ID**: ID del número de teléfono de WhatsApp Business
- **VERIFY_TOKEN**: Token personalizado para verificar el webhook (puedes inventar uno)
- **APP_SECRET**: Secreto de la aplicación (opcional pero recomendado para producción)

### 2. Configurar Variables de Entorno

Actualiza tu archivo `config.env` con las credenciales:

```env
# Configuración de WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=1234567890123456
WHATSAPP_VERIFY_TOKEN=mi_token_secreto_webhook
WHATSAPP_APP_SECRET=tu_app_secret_opcional
```

### 3. Configurar el Webhook

#### Paso 1: Obtener URL pública

Tu servidor necesita una URL pública HTTPS. Para desarrollo local, puedes usar:

**Opción 1: ngrok (Recomendado para desarrollo)**
```bash
# Instalar ngrok
npm install -g ngrok

# Exponer puerto 8000
ngrok http 8000
```

**Opción 2: Servicio en la nube**
- Heroku
- Railway
- Digital Ocean
- AWS Lambda

#### Paso 2: Configurar webhook en Meta

1. En la consola de Meta, ve a WhatsApp > Configuración
2. En la sección "Webhooks", haz clic en "Configurar webhooks"
3. Ingresa tu URL: `https://tu-dominio.com/webhook/whatsapp`
4. Ingresa el token de verificación que definiste en `WHATSAPP_VERIFY_TOKEN`
5. Selecciona los eventos: `messages`
6. Haz clic en "Verificar y guardar"

## 🚀 Endpoints Disponibles

### 1. Webhook de WhatsApp

#### GET `/webhook/whatsapp`
Verificación del webhook (requerido por Meta)

#### POST `/webhook/whatsapp`
Recibe mensajes entrantes de WhatsApp

### 2. Envío Manual de Mensajes

#### POST `/whatsapp/send-message`
Envía un mensaje de texto a WhatsApp

**Body:**
```json
{
  "to": "573001234567",
  "message": "¡Hola! Este es un mensaje desde TerraInnova"
}
```

**Respuesta:**
```json
{
  "status": "sent",
  "to": "573001234567",
  "message": "¡Hola! Este es un mensaje desde TerraInnova",
  "whatsapp_response": {
    "messaging_product": "whatsapp",
    "contacts": [...],
    "messages": [...]
  }
}
```

#### POST `/whatsapp/send-media`
Envía un mensaje con media (imagen, video, documento)

**Body:**
```json
{
  "to": "573001234567",
  "media_type": "image",
  "media_url": "https://example.com/imagen.jpg",
  "caption": "Mira nuestros productos ecológicos"
}
```

### 3. Health Check

#### GET `/health`
Verifica el estado de todos los servicios, incluyendo WhatsApp

**Respuesta:**
```json
{
  "status": "healthy",
  "services": {
    "redis": "healthy",
    "qdrant": "healthy",
    "gemini": "configured",
    "whatsapp": "configured"
  }
}
```

## 🔄 Flujo de Funcionamiento

### Mensaje Entrante

1. **Usuario envía mensaje** → WhatsApp Business API
2. **WhatsApp envía webhook** → Tu servidor (`POST /webhook/whatsapp`)
3. **Servidor procesa mensaje** → Extrae texto y número
4. **Obtiene contexto** → Redis (conversaciones previas)
5. **Genera respuesta** → Gemini AI
6. **Guarda contexto** → Redis (nueva conversación)
7. **Envía respuesta** → WhatsApp Business API
8. **Usuario recibe respuesta** → WhatsApp

### Búsqueda de Documentos

Si el usuario pregunta algo específico, el sistema:
1. Genera embedding de la pregunta
2. Busca en Qdrant documentos relevantes
3. Incluye información encontrada en la respuesta de Gemini

## 🧪 Testing

### 1. Verificar configuración

```bash
curl -X GET "http://localhost:8000/health"
```

### 2. Enviar mensaje de prueba

```bash
curl -X POST "http://localhost:8000/whatsapp/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "tu_numero_de_prueba",
    "message": "🤖 Hola, soy el chatbot de TerraInnova. ¿En qué puedo ayudarte?"
  }'
```

### 3. Probar webhook localmente

```bash
# Simular webhook de WhatsApp
curl -X POST "http://localhost:8000/webhook/whatsapp" \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "id": "entry_id",
      "changes": [{
        "value": {
          "messaging_product": "whatsapp",
          "metadata": {
            "display_phone_number": "573001234567",
            "phone_number_id": "1234567890123456"
          },
          "contacts": [{
            "profile": {
              "name": "Usuario Prueba"
            },
            "wa_id": "573001234567"
          }],
          "messages": [{
            "from": "573001234567",
            "id": "wamid.test123",
            "timestamp": "1640995200",
            "text": {
              "body": "Hola, ¿qué productos tienen disponibles?"
            },
            "type": "text"
          }]
        },
        "field": "messages"
      }]
    }]
  }'
```

## 🔐 Seguridad

### Verificación de Firma (Recomendado para Producción)

El servicio automáticamente verifica la firma del webhook si tienes configurado `WHATSAPP_APP_SECRET`:

```env
WHATSAPP_APP_SECRET=tu_app_secret_desde_meta
```

### HTTPS Obligatorio

WhatsApp requiere HTTPS para webhooks. En desarrollo, ngrok proporciona HTTPS automáticamente.

## 🚨 Troubleshooting

### Error: "Webhook verification failed"

- Verifica que `WHATSAPP_VERIFY_TOKEN` sea correcto
- Asegúrate de que el endpoint GET esté funcionando
- Revisa que la URL sea accesible desde internet

### Error: "Invalid signature"

- Verifica `WHATSAPP_APP_SECRET`
- Asegúrate de que el cuerpo del webhook no se modifique

### Error: "Message not sent"

- Verifica `WHATSAPP_ACCESS_TOKEN`
- Confirma `WHATSAPP_PHONE_NUMBER_ID`
- Asegúrate de que el número esté en formato internacional sin +

### El bot no responde

- Verifica que Gemini esté configurado (`GEMINI_API_KEY`)
- Revisa los logs del servidor
- Confirma que Redis esté funcionando

### Número no válido

Los números deben estar en formato internacional sin el símbolo +:
- ✅ Correcto: `573001234567`
- ❌ Incorrecto: `+57 300 123 4567`

## 📊 Monitoreo y Logs

El servicio registra automáticamente:

- Mensajes recibidos y enviados
- Errores de API
- Verificaciones de webhook
- Respuestas de Gemini

Revisa los logs para diagnosticar problemas:

```bash
# Si usas Docker
docker logs container_name

# Si ejecutas directamente
# Los logs aparecen en la consola
```

## 📈 Escalabilidad

Para producción, considera:

1. **Webhook múltiples**: Configurar varios endpoints para balanceo
2. **Rate limiting**: Implementar límites de mensajes por usuario
3. **Queue system**: Usar Redis o RabbitMQ para procesar mensajes
4. **Monitoring**: Implementar métricas con Prometheus/Grafana
5. **Error handling**: Implementar reintentos automáticos

## 📝 Limitaciones

### WhatsApp Business API (Meta)

- Máximo 1000 conversaciones gratuitas por mes
- Solo puedes enviar plantillas a usuarios que no han iniciado conversación
- Mensajes de texto libre solo durante 24h después del último mensaje del usuario

### Números de Prueba

- Limitados a números verificados durante desarrollo
- Para producción necesitas verificación business de Meta

## 🎯 Próximos Pasos

Una vez configurado, puedes:

1. **Personalizar respuestas**: Modificar el prompt en `gemini_service.py`
2. **Agregar comandos**: Implementar comandos especiales (/help, /productos, etc.)
3. **Integrar con base de datos**: Conectar con el backend de TerraInnova
4. **Implementar plantillas**: Crear plantillas aprobadas por Meta
5. **Analytics**: Implementar métricas de conversación

¡Ya tienes WhatsApp completamente integrado! 🚀 