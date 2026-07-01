import os
import shutil
import logging
from src.services.sheets_service import sheets_service
from src.services.dropbox_service import dropbox_service
from src.services.document_processor import document_processor
from src.core.ai_client import ai_client

logger = logging.getLogger(__name__)

class AnalysisWorkflow:
    """
    Orquestador principal del proceso de análisis VAWA / Permanent Bar.
    """
    def __init__(self):
        self.base_temp_dir = "temp_downloads"

    def _cleanup_temp_dir(self, folder_path: str):
        """Elimina la carpeta temporal de un cliente después de procesarlo."""
        try:
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
        except Exception as e:
            logger.warning(f"No se pudo limpiar el directorio temporal {folder_path}: {e}")

    def run(self):
        logger.info("Iniciando el flujo de trabajo de Análisis de Documentos...")
        
        # 1. Obtener filas pendientes
        pending_rows = sheets_service.get_pending_rows()
        if not pending_rows:
            logger.info("No hay clientes pendientes de análisis en la hoja.")
            return

        logger.info(f"Se encontraron {len(pending_rows)} casos pendientes para procesar.")

        # 2. Procesar cada fila secuencialmente
        for row in pending_rows:
            row_idx = row['row_idx']
            client_name = row['nombre_cliente']
            dropbox_link = row['link_dropbox']
            
            logger.info(f"--- Procesando Fila {row_idx} | Cliente: {client_name} ---")
            client_temp_dir = os.path.join(self.base_temp_dir, f"cliente_{row_idx}")

            try:
                # Paso A: Descargar documentos objetivo
                logger.info("Buscando y descargando documentos desde Dropbox...")
                local_files = dropbox_service.extract_target_documents(dropbox_link, client_temp_dir)
                
                if not local_files:
                    logger.warning(f"No se descargaron documentos válidos para {client_name}. Saltando...")
                    # Podrías actualizar la hoja indicando que no se encontraron documentos
                    sheets_service.update_analysis_results(row_idx, "Sin documentos USCIS", "N/A", "0", "N/A")
                    continue

                # Paso B: Procesar documentos (Textos e Imágenes)
                logger.info("Procesando PDFs e Imágenes locales...")
                combined_text, images_data = document_processor.prepare_documents_for_ai(local_files)

                # Paso C: Análisis con Gemini
                logger.info("Ejecutando análisis de inteligencia artificial...")
                ai_results = ai_client.analyze_documents(combined_text, images_data)

                if not ai_results:
                    logger.error(f"Fallo en el análisis de IA para {client_name}. Saltando...")
                    sheets_service.update_analysis_results(row_idx, "Error IA", "N/A", "0", "N/A")
                    continue

                # Paso D: Actualizar Google Sheets
                pb_status = str(ai_results.get("permanent_bar", "No tiene PB"))
                referencia = str(ai_results.get("referencia", "N/A"))
                num_delitos = str(ai_results.get("numero_delitos", "0"))
                delitos = str(ai_results.get("delitos", "N/A"))

                logger.info(f"Resultados obtenidos: PB: {pb_status} | Delitos: {num_delitos}")
                
                sheets_service.update_analysis_results(
                    row_idx=row_idx,
                    pb_status=pb_status,
                    referencia=referencia,
                    num_delitos=num_delitos,
                    delitos=delitos
                )
                
                logger.info(f"--- Fila {row_idx} completada exitosamente ---")

            except Exception as e:
                logger.error(f"Error procesando al cliente {client_name} (Fila {row_idx}): {e}")
                
            finally:
                # Siempre limpiar la carpeta temporal al terminar con el cliente
                self._cleanup_temp_dir(client_temp_dir)

        logger.info("Flujo de trabajo finalizado.")

# Instancia global
analysis_workflow = AnalysisWorkflow()