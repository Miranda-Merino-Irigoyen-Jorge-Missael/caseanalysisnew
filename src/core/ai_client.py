import json
import logging
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from src.config import Config

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Cliente para enviar peticiones a Gemini a través de Vertex AI.
    Soporta inyección nativa de PDFs e imágenes.
    """

    def __init__(self):
        try:
            vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
            self.model = GenerativeModel("gemini-3.5-flash")
            self._initialized = True
            logger.info(f"Vertex AI inicializado en {Config.LOCATION} con el modelo gemini-3.5-flash.")
        except Exception as e:
            logger.error(f"Error inicializando Vertex AI: {e}")
            self._initialized = False

    def _build_contents(self, documents_data: list, prompt_instructions: str) -> list:
        """Construye las partes del mensaje combinando el prompt y los documentos."""
        contents = [Part.from_text(prompt_instructions)]
        
        for doc in documents_data:
            contents.append(Part.from_text(f"--- INICIO DEL DOCUMENTO: {doc['filename']} ---"))
            
            # Inyección nativa del PDF o Imagen usando los bytes crudos
            part = Part.from_data(
                mime_type=doc["mime_type"],
                data=doc["data"]
            )
            contents.append(part)
            
        return contents

    def analyze_documents(self, combined_text: str, documents_data: list) -> dict:
        """
        Ejecuta el análisis de IA sobre los documentos nativos.
        """
        if not self._initialized:
            logger.error("Cliente Vertex AI no inicializado.")
            return None

        prompt_instructions = """
Con base en los siguientes documentos deberás de ir recabando si es que logras identificar que el cliente tenga permanent bar o barra permanente con EUA. Contarás si tiene delitos, cuántos y cuáles son. Solo limita el análisis a eso, no alucines.

INSTRUCCIONES DE FORMATO DE SALIDA (CRÍTICO):
Debes retornar tu respuesta ÚNICA Y EXCLUSIVAMENTE en un formato JSON válido.
No incluyas texto antes ni después del JSON, ni uses bloques de código markdown (```json).

El JSON debe tener exactamente la siguiente estructura:
{
    "permanent_bar": "Si tiene PB" o "No tiene PB" (si no encuentras mención, coloca "No tiene PB"),
    "referencia": "Coloca el nombre del documento exacto donde encontraste la información de la barra permanente o de los delitos. Si son varios, separalos por comas. Si no hay, coloca N/A.",
    "numero_delitos": "Número entero representando la cantidad de delitos (ej. 0, 1, 2)",
    "delitos": "Nombre de los delitos separados por comas. Si no hay, coloca N/A."
}
"""

        contents = self._build_contents(documents_data, prompt_instructions)

        try:
            logger.info("Enviando petición con documentos nativos a Gemini 3.5 Flash...")
            response = self.model.generate_content(
                contents,
                generation_config={
                    "temperature": 0.1, 
                    "response_mime_type": "application/json" 
                }
            )
            
            response_text = response.text.replace("```json", "").replace("```", "").strip()
            result_data = json.loads(response_text)
            
            logger.info("[✓] Análisis de Gemini completado.")
            return result_data

        except json.JSONDecodeError as json_err:
            logger.error(f"Error decodificando JSON: {json_err}\nRespuesta cruda: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Error en Vertex AI: {e}")
            return None

ai_client = GeminiClient()