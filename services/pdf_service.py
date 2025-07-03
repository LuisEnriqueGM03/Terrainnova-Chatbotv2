import io
from typing import Optional
from PyPDF2 import PdfReader
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFService:
    """
    Servicio para extraer texto de archivos PDF
    """
    
    def __init__(self):
        self.supported_extensions = ['.pdf']
    
    def extract_text_from_pdf(self, pdf_file: bytes) -> str:
        """
        Extrae el contenido de texto plano de un archivo PDF
        
        Args:
            pdf_file: Contenido binario del archivo PDF
            
        Returns:
            str: Texto extraído del PDF concatenado, o string vacío si falla
        """
        try:
            # Crear un buffer de memoria con el contenido del PDF
            pdf_buffer = io.BytesIO(pdf_file)
            
            # Crear el lector de PDF
            pdf_reader = PdfReader(pdf_buffer)
            
            # Verificar que el PDF no esté vacío
            if len(pdf_reader.pages) == 0:
                logger.warning("El archivo PDF está vacío o no contiene páginas")
                return ""
            
            # Extraer texto de todas las páginas
            extracted_text = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text.append(page_text.strip())
                    else:
                        logger.warning(f"No se pudo extraer texto de la página {page_num + 1}")
                except Exception as e:
                    logger.error(f"Error al extraer texto de la página {page_num + 1}: {str(e)}")
                    continue
            
            # Concatenar todo el texto extraído
            full_text = "\n\n".join(extracted_text)
            
            logger.info(f"Extracción exitosa: {len(pdf_reader.pages)} páginas procesadas")
            return full_text
            
        except Exception as e:
            logger.error(f"Error al procesar el archivo PDF: {str(e)}")
            return ""
    
    def extract_text_from_pdf_path(self, pdf_path: str) -> str:
        """
        Extrae texto de un PDF desde una ruta de archivo
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            str: Texto extraído del PDF
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_content = file.read()
                return self.extract_text_from_pdf(pdf_content)
        except FileNotFoundError:
            logger.error(f"Archivo no encontrado: {pdf_path}")
            return ""
        except Exception as e:
            logger.error(f"Error al leer el archivo PDF: {str(e)}")
            return ""
    
    def get_pdf_info(self, pdf_file: bytes) -> dict:
        """
        Obtiene información básica del PDF
        
        Args:
            pdf_file: Contenido binario del archivo PDF
            
        Returns:
            dict: Información del PDF (páginas, título, etc.)
        """
        try:
            pdf_buffer = io.BytesIO(pdf_file)
            pdf_reader = PdfReader(pdf_buffer)
            
            info = {
                "pages": len(pdf_reader.pages),
                "title": pdf_reader.metadata.get('/Title', 'Sin título') if pdf_reader.metadata else 'Sin título',
                "author": pdf_reader.metadata.get('/Author', 'Sin autor') if pdf_reader.metadata else 'Sin autor',
                "subject": pdf_reader.metadata.get('/Subject', 'Sin asunto') if pdf_reader.metadata else 'Sin asunto'
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error al obtener información del PDF: {str(e)}")
            return {
                "pages": 0,
                "title": "Error",
                "author": "Error",
                "subject": "Error"
            }
    
    def is_valid_pdf(self, pdf_file: bytes) -> bool:
        """
        Verifica si el archivo es un PDF válido
        
        Args:
            pdf_file: Contenido binario del archivo
            
        Returns:
            bool: True si es un PDF válido
        """
        try:
            pdf_buffer = io.BytesIO(pdf_file)
            pdf_reader = PdfReader(pdf_buffer)
            return len(pdf_reader.pages) > 0
        except Exception:
            return False
    
    def get_text_length(self, pdf_file: bytes) -> int:
        """
        Obtiene la longitud del texto extraído
        
        Args:
            pdf_file: Contenido binario del archivo PDF
            
        Returns:
            int: Número de caracteres en el texto extraído
        """
        text = self.extract_text_from_pdf(pdf_file)
        return len(text)

# Instancia global del servicio
pdf_service = PDFService()

def extract_text_from_pdf(pdf_file: bytes) -> str:
    """
    Función de conveniencia para extraer texto de PDF
    """
    return pdf_service.extract_text_from_pdf(pdf_file) 