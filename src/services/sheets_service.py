import logging
from src.core.google_client import google_manager
from src.config import Config
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class SheetsService:
    """
    Servicio para leer y actualizar la hoja 'ANALISIS IA'.
    Mapeo de columnas:
    A (1): ID Cliente
    B (2): Nombre del cliente
    C (3): Link Dropbox
    D (4): PERMANENT BAR (Si/No)
    E (5): REFERENCIA (Nombre del documento)
    F (6): # DELITOS
    G (7): DELITOS (Lista)
    """
    
    COL_ID = 1
    COL_NOMBRE = 2
    COL_LINK = 3
    COL_PB = 4
    COL_REF = 5
    COL_NUM_DELITOS = 6
    COL_DELITOS = 7

    def __init__(self):
        self.client = google_manager.get_sheets_client()
        self.spreadsheet_id = Config.SPREADSHEET_ID
        self.sheet_name = Config.SHEET_NAME
        self._sheet = None

    @property
    def sheet(self):
        """Carga la hoja mediante Lazy Load para optimizar recursos."""
        if not self._sheet:
            try:
                sh = self.client.open_by_key(self.spreadsheet_id)
                self._sheet = sh.worksheet(self.sheet_name)
            except Exception as e:
                logger.error(f"Error conectando a la hoja '{self.sheet_name}': {e}")
                raise
        return self._sheet

    def get_pending_rows(self) -> list:
        """
        Obtiene las filas que tienen un link de Dropbox pero no tienen análisis previo
        (la columna D 'PERMANENT BAR' está vacía).
        """
        rows_data = []
        try:
            all_values = self.sheet.get_all_values()
            
            for i, row in enumerate(all_values):
                row_idx = i + 1  # gspread utiliza índices base 1
                if row_idx == 1: 
                    continue # Saltar encabezados

                # Validar que la fila tenga al menos la columna del link
                if len(row) >= self.COL_LINK:
                    link_dropbox = row[self.COL_LINK - 1].strip()
                    pb_status = row[self.COL_PB - 1].strip() if len(row) >= self.COL_PB else ""
                    
                    # Si hay link pero no hay status, está pendiente
                    if link_dropbox and not pb_status:
                        def get_col_val(col_idx):
                            return row[col_idx - 1].strip() if len(row) >= col_idx else ""

                        rows_data.append({
                            'row_idx': row_idx,
                            'id_cliente': get_col_val(self.COL_ID),
                            'nombre_cliente': get_col_val(self.COL_NOMBRE),
                            'link_dropbox': link_dropbox
                        })
            
            return rows_data

        except Exception as e:
            logger.error(f"Error leyendo filas pendientes en Sheets: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def update_analysis_results(self, row_idx: int, pb_status: str, referencia: str, num_delitos: str, delitos: str):
        """
        Escribe los resultados del análisis de la IA en las columnas correspondientes.
        Realiza la actualización en bloque (batch update) para minimizar llamadas a la API.
        """
        try:
            cell_range = f"D{row_idx}:G{row_idx}"
            values = [[pb_status, referencia, num_delitos, delitos]]
            self.sheet.update(range_name=cell_range, values=values)
            logger.info(f"Fila {row_idx} actualizada exitosamente con los resultados del análisis.")
        except Exception as e:
            logger.error(f"Error actualizando resultados en fila {row_idx}: {e}")
            raise

# Instancia global del servicio
sheets_service = SheetsService()