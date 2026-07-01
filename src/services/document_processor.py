import os
import logging
import mimetypes

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Servicio para preparar archivos locales y enviarlos de forma nativa a Vertex AI.
    Lee los bytes crudos sin transformaciones innecesarias.
    """

    def __init__(self):
        mimetypes.add_type('image/jpeg', '.jpg')
        mimetypes.add_type('image/jpeg', '.jpeg')
        mimetypes.add_type('image/png', '.png')
        mimetypes.add_type('application/pdf', '.pdf')

    def prepare_documents_for_ai(self, file_paths: list) -> tuple:
        """
        Lee los archivos y retorna sus bytes crudos junto con su tipo MIME.
        """
        documents_data = []

        if not file_paths:
            return "", documents_data

        for path in file_paths:
            if not os.path.exists(path):
                logger.warning(f"El archivo no existe: {path}")
                continue

            ext = os.path.splitext(path)[1].lower()
            filename = os.path.basename(path)
            
            if ext in ['.pdf', '.jpg', '.jpeg', '.png']:
                try:
                    logger.info(f"Preparando documento nativo: {filename}...")
                    
                    mime_type, _ = mimetypes.guess_type(path)
                    if not mime_type:
                        mime_type = "application/pdf" if ext == '.pdf' else "image/jpeg"

                    # Lectura directa de bytes
                    with open(path, "rb") as file:
                        raw_bytes = file.read()
                        
                    documents_data.append({
                        "filename": filename,
                        "mime_type": mime_type,
                        "data": raw_bytes
                    })
                except Exception as e:
                    logger.error(f"Error leyendo archivo {filename}: {e}")
            else:
                logger.warning(f"Extensión no soportada: {filename}")

        return "", documents_data

# Instancia global del servicio
document_processor = DocumentProcessor()