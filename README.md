# 🤖 TerraInnova AI Chatbot Microservice

Microservicio de inteligencia artificial para chatbot omnicanal con soporte para WhatsApp, análisis de PDF y búsqueda semántica.

## 🎯 Características Principales

- **🔗 Integración WhatsApp Business API**: Webhook verificado por Meta
- **🧠 IA Conversacional**: Gemini AI con contexto empresarial
- **📊 Base de Datos**: PostgreSQL para productos y categorías
- **📄 Análisis PDF**: Extracción de texto y generación de embeddings
- **🔍 Búsqueda Semántica**: Qdrant para similitud vectorial
- **💾 Gestión de Sesiones**: Redis con fallback en memoria
- **🚀 API REST**: FastAPI con endpoints optimizados

## 🏗️ Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WhatsApp      │    │   Web Client    │    │   PDF Upload    │
│   Business API  │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼──────────────┐
                    │                            │
                    │  TerraInnova AI Service    │
                    │                            │
                    └─────────────┬──────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
    ┌─────▼─────┐        ┌────────▼────────┐      ┌──────▼──────┐
    │  Gemini   │        │   PostgreSQL    │      │   Qdrant    │
    │    AI     │        │   (Productos)   │      │ (Vectores)  │
    └───────────┘        └─────────────────┘      └─────────────┘
                                  │
                         ┌────────▼────────┐
                         │      Redis      │
                         │   (Sesiones)    │
                         └─────────────────┘
```

## 🛠️ Tecnologías

| Componente | Tecnología | Propósito |
|------------|------------|-----------|
| **Framework** | FastAPI | API REST rápida y moderna |
| **IA** | Google Gemini | Procesamiento de lenguaje natural |
| **Base de Datos** | PostgreSQL | Almacenamiento de productos |
| **Cache/Sesiones** | Redis | Contexto de conversaciones |
| **Búsqueda Vectorial** | Qdrant | Similitud semántica |
| **PDF** | PyPDF2 | Extracción de texto |
| **Mensajería** | WhatsApp Business API | Canal principal |

## 📋 Configuración

### 1. Variables de Entorno

Copia `config.env.example` a `config.env` y configura:

```env
# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=terrainnova
DB_USER=postgres
DB_PASSWORD=your_password_here

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_VERIFY_TOKEN=your_verify_token
WHATSAPP_APP_SECRET=your_app_secret

# Servicios Opcionales
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333

# Servidor
HOST=0.0.0.0
PORT=3000
```

### 2. Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor
python main.py
```

## 🌐 Endpoints API

### Core
- `GET /` - Información del servicio
- `GET /health` - Estado de todos los servicios

### Chat
- `POST /chat` - Conversación con IA
- `DELETE /chat/{user_id}/context` - Limpiar contexto
- `GET /chat/{user_id}/context` - Obtener contexto

### Productos (PostgreSQL)
- `GET /productos` - Listar todos los productos
- `GET /productos/buscar?q=term` - Buscar productos
- `GET /categorias` - Listar categorías

### PDF
- `POST /upload-pdf` - Subir y analizar PDF
- `POST /search-documents` - Búsqueda semántica

### WhatsApp
- `GET /webhook` - Verificación Meta
- `POST /webhook` - Recibir mensajes
- `POST /whatsapp/send-message` - Enviar mensaje manual

## 🤖 Contexto de IA

El chatbot incluye conocimiento sobre:

### Empresa
- **Nombre**: TerraINNOVA
- **Ubicación**: Santa Cruz de la Sierra, Bolivia
- **Misión**: Soluciones sostenibles para residuos orgánicos
- **Productos**: Compost, lombricompost, kits de jardinería

### Capacidades
- Consulta de productos en tiempo real desde PostgreSQL
- Búsqueda inteligente por nombre, descripción o categoría
- Recomendaciones por presupuesto
- Educación ambiental y sostenibilidad
- Soporte en español

## 🔄 Flujo de Trabajo

### 1. Mensaje WhatsApp
```
Usuario → WhatsApp → Meta → Webhook → Procesamiento
```

### 2. Procesamiento IA
```
Mensaje → Contexto (Redis) → Productos (PostgreSQL) → Gemini → Respuesta
```

### 3. Búsqueda de Productos
```
Consulta → Base de Datos → Filtros → Formato Chatbot → Usuario
```

### 4. Análisis PDF
```
PDF → Extracción Texto → Embedding (Gemini) → Qdrant → Búsqueda
```

## 🎯 Casos de Uso

### Para Clientes
- "¿Qué productos tienen disponibles?"
- "Busco compost para mi jardín"
- "Tengo presupuesto de $300, ¿qué me recomiendan?"
- "¿Cómo uso el lombricompost?"

### Para Administradores
- Subir manuales PDF de productos
- Consultar contexto de conversaciones
- Monitorear estado de servicios
- Gestionar productos vía PostgreSQL

## 🚨 Estados de Servicio

### Health Check Response
```json
{
  "status": "healthy|degraded",
  "services": {
    "redis": "healthy|unhealthy",
    "qdrant": "healthy|unhealthy", 
    "gemini": "configured|not_configured",
    "whatsapp": "configured|not_configured",
    "database": "healthy|unhealthy"
  }
}
```

### Tolerancia a Fallos
- **Redis**: Fallback a memoria temporal
- **Qdrant**: Desactiva búsqueda semántica
- **PostgreSQL**: Error en consultas de productos
- **Gemini**: Mensaje de servicio no disponible

## 🔐 Seguridad

- ✅ Verificación de webhook WhatsApp
- ✅ Variables de entorno para credenciales
- ✅ Validación de signatures Meta
- ⚠️ Falta: Autenticación de usuarios

## 📈 Monitoreo

### Logs Incluidos
- Conexiones a bases de datos
- Verificaciones de webhook
- Errores de procesamiento
- Estado de servicios

### Métricas Disponibles
- Número de mensajes procesados
- Tiempo de respuesta IA
- Estado de conexiones
- Uso de contexto por usuario

## 🚀 Despliegue

### Desarrollo
```bash
python main.py
```

### Producción (Docker)
```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
```

### Kubernetes (Pendiente)
- Configuración de pods
- Service discovery
- Escalabilidad horizontal
- Health checks automáticos

---

## 📞 Soporte

**TerraINNOVA Tech Team**
- Email: terrainnova@gmail.com
- Versión: 1.0.0
- Última actualización: 2024 