import psycopg
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
load_dotenv("config.env")

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Producto:
    """Modelo de producto desde la base de datos"""
    id: int
    nombre: str
    descripcion: str
    precio: float
    stock: int
    imagenUrl: Optional[str]
    categoria_id: int
    categoria_nombre: Optional[str] = None

@dataclass
class Categoria:
    """Modelo de categoria desde la base de datos"""
    id: int
    nombre: str

class DatabaseService:
    """
    Servicio para conectar con la base de datos PostgreSQL del backend
    """
    
    def __init__(self):
        # Configuración de PostgreSQL desde variables de entorno
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'dbname': os.getenv('DB_NAME', 'terrainnova'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password')
        }
        
        # Verificar configuración
        if not all([self.db_config['host'], self.db_config['dbname'], 
                   self.db_config['user'], self.db_config['password']]):
            logger.error("Configuración de PostgreSQL incompleta. Revisa las variables de entorno DB_*")
            self.available = False
        else:
            logger.info(f"Configuración PostgreSQL: {self.db_config['user']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['dbname']}")
            self.available = True
            
        # Probar conexión
        self.test_connection()
    
    def test_connection(self) -> bool:
        """Prueba la conexión a la base de datos PostgreSQL"""
        if not self.available:
            return False
            
        try:
            with psycopg.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
                    tables = cursor.fetchall()
                    logger.info(f"Tablas encontradas: {[table[0] for table in tables]}")
            return True
        except Exception as e:
            logger.error(f"Error conectando a la base de datos PostgreSQL: {e}")
            self.available = False
            return False
    
    def get_productos(self) -> List[Producto]:
        """Obtiene todos los productos de la base de datos"""
        if not self.available:
            return []
            
        try:
            with psycopg.connect(**self.db_config) as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cursor:
                    query = """
                        SELECT p.id, p.nombre, p.descripcion, p.precio, p.stock, p."imagenUrl", p."categoriaId", c.nombre as categoria_nombre
                        FROM producto p
                        LEFT JOIN categoria c ON p."categoriaId" = c.id
                        ORDER BY p.nombre
                    """
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    
                    productos = []
                    for row in rows:
                        producto = Producto(
                            id=row['id'],
                            nombre=row['nombre'],
                            descripcion=row['descripcion'],
                            precio=float(row['precio']),
                            stock=row['stock'],
                            imagenUrl=row['imagenUrl'],
                            categoria_id=row['categoriaId'],
                            categoria_nombre=row['categoria_nombre']
                        )
                        productos.append(producto)
            
            logger.info(f"Cargados {len(productos)} productos desde la base de datos")
            return productos
                
        except Exception as e:
            logger.error(f"Error obteniendo productos: {e}")
            return []
    
    def get_producto_by_id(self, producto_id: int) -> Optional[Producto]:
        """Obtiene un producto específico por ID"""
        if not self.available:
            return None
            
        try:
            with psycopg.connect(**self.db_config) as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cursor:
                    query = """
                        SELECT p.id, p.nombre, p.descripcion, p.precio, p.stock, p."imagenUrl", p."categoriaId", c.nombre as categoria_nombre
                        FROM producto p
                        LEFT JOIN categoria c ON p."categoriaId" = c.id
                        WHERE p.id = %s
                    """
                    cursor.execute(query, (producto_id,))
                    row = cursor.fetchone()
            
            if row:
                return Producto(
                    id=row['id'],
                    nombre=row['nombre'],
                    descripcion=row['descripcion'],
                    precio=float(row['precio']),
                    stock=row['stock'],
                    imagenUrl=row['imagenUrl'],
                    categoria_id=row['categoriaId'],
                    categoria_nombre=row['categoria_nombre']
                )
            return None
                
        except Exception as e:
            logger.error(f"Error obteniendo producto {producto_id}: {e}")
            return None
    
    def search_productos(self, query: str) -> List[Producto]:
        """Busca productos por nombre o descripción"""
        if not self.available:
            return []
            
        try:
            with psycopg.connect(**self.db_config) as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cursor:
                    search_query = f"%{query.lower()}%"
                    sql_query = """
                        SELECT p.id, p.nombre, p.descripcion, p.precio, p.stock, p."imagenUrl", p."categoriaId", c.nombre as categoria_nombre
                        FROM producto p
                        LEFT JOIN categoria c ON p."categoriaId" = c.id
                        WHERE LOWER(p.nombre) LIKE %s OR LOWER(p.descripcion) LIKE %s OR LOWER(c.nombre) LIKE %s
                        ORDER BY p.nombre
                    """
                    cursor.execute(sql_query, (search_query, search_query, search_query))
                    rows = cursor.fetchall()
            
            productos = []
            for row in rows:
                producto = Producto(
                    id=row['id'],
                    nombre=row['nombre'],
                    descripcion=row['descripcion'],
                    precio=float(row['precio']),
                    stock=row['stock'],
                    imagenUrl=row['imagenUrl'],
                    categoria_id=row['categoriaId'],
                    categoria_nombre=row['categoria_nombre']
                )
                productos.append(producto)
            
            logger.info(f"Encontrados {len(productos)} productos para '{query}'")
            return productos
                
        except Exception as e:
            logger.error(f"Error buscando productos: {e}")
            return []
    
    def get_productos_by_categoria(self, categoria_id: int) -> List[Producto]:
        """Obtiene productos de una categoría específica"""
        if not self.available:
            return []
            
        try:
            with psycopg.connect(**self.db_config) as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cursor:
                    query = """
                        SELECT p.id, p.nombre, p.descripcion, p.precio, p.stock, p."imagenUrl", p."categoriaId", c.nombre as categoria_nombre
                        FROM producto p
                        LEFT JOIN categoria c ON p."categoriaId" = c.id
                        WHERE p."categoriaId" = %s
                        ORDER BY p.nombre
                    """
                    cursor.execute(query, (categoria_id,))
                    rows = cursor.fetchall()
            
            productos = []
            for row in rows:
                producto = Producto(
                    id=row['id'],
                    nombre=row['nombre'],
                    descripcion=row['descripcion'],
                    precio=float(row['precio']),
                    stock=row['stock'],
                    imagenUrl=row['imagenUrl'],
                    categoria_id=row['categoriaId'],
                    categoria_nombre=row['categoria_nombre']
                )
                productos.append(producto)
            
            return productos
                
        except Exception as e:
            logger.error(f"Error obteniendo productos de categoría {categoria_id}: {e}")
            return []
    
    def get_productos_by_presupuesto(self, presupuesto_max: float) -> List[Producto]:
        """Obtiene productos dentro de un presupuesto"""
        if not self.available:
            return []
            
        try:
            with psycopg.connect(**self.db_config) as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cursor:
                    query = """
                        SELECT p.id, p.nombre, p.descripcion, p.precio, p.stock, p."imagenUrl", p."categoriaId", c.nombre as categoria_nombre
                        FROM producto p
                        LEFT JOIN categoria c ON p."categoriaId" = c.id
                        WHERE p.precio <= %s
                        ORDER BY p.precio DESC
                    """
                    cursor.execute(query, (presupuesto_max,))
                    rows = cursor.fetchall()
            
            productos = []
            for row in rows:
                producto = Producto(
                    id=row['id'],
                    nombre=row['nombre'],
                    descripcion=row['descripcion'],
                    precio=float(row['precio']),
                    stock=row['stock'],
                    imagenUrl=row['imagenUrl'],
                    categoria_id=row['categoriaId'],
                    categoria_nombre=row['categoria_nombre']
                )
                productos.append(producto)
            
            return productos
                
        except Exception as e:
            logger.error(f"Error obteniendo productos por presupuesto: {e}")
            return []
    
    def get_categorias(self) -> List[Categoria]:
        """Obtiene todas las categorías"""
        if not self.available:
            return []
            
        try:
            with psycopg.connect(**self.db_config) as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cursor:
                    cursor.execute("SELECT id, nombre FROM categoria ORDER BY nombre")
                    rows = cursor.fetchall()
            
            categorias = []
            for row in rows:
                categoria = Categoria(
                    id=row['id'],
                    nombre=row['nombre']
                )
                categorias.append(categoria)
            
            return categorias
                
        except Exception as e:
            logger.error(f"Error obteniendo categorías: {e}")
            return []
    
    def health_check(self) -> bool:
        """Verifica la salud de la conexión a la base de datos"""
        return self.available and self.test_connection()
    
    def format_producto_para_chatbot(self, producto: Producto) -> str:
        """Formatea un producto para mostrar en el chatbot"""
        stock_text = "✅ En stock" if producto.stock > 0 else "❌ Agotado"
        
        return f"""
🌱 **{producto.nombre}**
💰 Precio: {producto.precio:,.0f} Bs
📦 Stock: {stock_text}
🏷️ Categoría: {producto.categoria_nombre or 'Sin categoría'}
📝 Descripción: {producto.descripcion}
"""
    
    def get_productos_recomendados(self, limit: int = 5) -> List[Producto]:
        """Obtiene productos recomendados (con stock disponible)"""
        if not self.available:
            return []
            
        try:
            with psycopg.connect(**self.db_config) as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cursor:
                    query = """
                        SELECT p.id, p.nombre, p.descripcion, p.precio, p.stock, p."imagenUrl", p."categoriaId", c.nombre as categoria_nombre
                        FROM producto p
                        LEFT JOIN categoria c ON p."categoriaId" = c.id
                        WHERE p.stock > 0
                        ORDER BY p.precio DESC
                        LIMIT %s
                    """
                    cursor.execute(query, (limit,))
                    rows = cursor.fetchall()
            
            productos = []
            for row in rows:
                producto = Producto(
                    id=row['id'],
                    nombre=row['nombre'],
                    descripcion=row['descripcion'],
                    precio=float(row['precio']),
                    stock=row['stock'],
                    imagenUrl=row['imagenUrl'],
                    categoria_id=row['categoriaId'],
                    categoria_nombre=row['categoria_nombre']
                )
                productos.append(producto)
            
            return productos
                
        except Exception as e:
            logger.error(f"Error obteniendo productos recomendados: {e}")
            return []

# Instancia global del servicio
database_service = DatabaseService()

# Funciones de conveniencia
def get_productos_info() -> str:
    """Obtiene información formateada de todos los productos para el chatbot"""
    productos = database_service.get_productos()
    if not productos:
        return "No hay productos disponibles en este momento."
    
    info = "🛍️ **PRODUCTOS DISPONIBLES EN TERRAINNOVA:**\n\n"
    for producto in productos:
        info += database_service.format_producto_para_chatbot(producto)
        info += "\n---\n"
    
    return info

def buscar_productos_chatbot(query: str) -> str:
    """Busca productos y devuelve información formateada para el chatbot"""
    productos = database_service.search_productos(query)
    if not productos:
        return f"No encontré productos relacionados con '{query}'. ¿Puedes ser más específico?"
    
    info = f"🔍 **Encontré {len(productos)} producto(s) para '{query}':**\n\n"
    for producto in productos:
        info += database_service.format_producto_para_chatbot(producto)
        info += "\n---\n"
    
    return info

def get_productos_por_presupuesto_chatbot(presupuesto: float) -> str:
    """Obtiene productos dentro de un presupuesto y devuelve información formateada"""
    productos = database_service.get_productos_by_presupuesto(presupuesto)
    if not productos:
        return f"No encontré productos dentro del presupuesto de ${presupuesto:,.0f}."
    
    info = f"💰 **Productos dentro de tu presupuesto de ${presupuesto:,.0f}:**\n\n"
    for producto in productos:
        info += database_service.format_producto_para_chatbot(producto)
        info += "\n---\n"
    
    return info 