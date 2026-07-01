import os
import json
import logging
import requests
from src.config import Config

logger = logging.getLogger(__name__)

class DropboxService:
    """
    Servicio para interactuar con Dropbox.
    Utiliza el microservicio en Cloud Run para obtener un token siempre válido,
    y peticiones HTTP crudas para interactuar con la API de Dropbox.
    """
    
    ALLOWED_EXTENSIONS = ('.pdf', '.jpg', '.jpeg', '.png')
    TARGET_KEYWORDS = ['uscis', 'ucis', 'usis']
    SUPPORTING_DOCS_KEYWORD = 'supporting documents'

    def __init__(self):
        # Ya no inicializamos el token aquí porque lo pediremos al vuelo
        pass

    def _get_valid_token(self) -> str:
        """
        Obtiene un token de acceso fresco desde el microservicio en Cloud Run.
        """
        try:
            headers = {"Content-Type": "application/json"}
            payload = {"signature": Config.DROPBOX_API_SECRET_KEY}
            
            logger.info("Solicitando token de Dropbox al servicio central...")
            response = requests.post(
                Config.DROPBOX_TOKEN_URL, 
                headers=headers, 
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Token obtenido correctamente (Renovado en esta petición: {data.get('refreshed')})")
                return data.get("access_token")
            else:
                logger.error(f"Error obteniendo token del servicio: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Excepción al conectar con el servicio de token de Dropbox: {e}")
            return None

    def _contains_keyword(self, name: str, keywords: list) -> bool:
        """Verifica si alguna palabra clave está en el nombre."""
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in keywords)

    def _list_folder_raw(self, path: str, shared_url: str, token: str) -> list:
        """Hace una petición HTTP cruda para listar el contenido de la carpeta."""
        url = "https://api.dropboxapi.com/2/files/list_folder"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "path": path,
            "shared_link": {"url": shared_url}
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            logger.error(f"Error en API cruda de Dropbox (Listar): {response.text}")
            return []
            
        return response.json().get("entries", [])

    def _download_file_raw(self, shared_url: str, remote_path: str, local_dest: str, token: str) -> bool:
        """Hace una petición HTTP cruda al endpoint de contenido para descargar el archivo."""
        url = "https://content.dropboxapi.com/2/sharing/get_shared_link_file"
        headers = {
            "Authorization": f"Bearer {token}",
            "Dropbox-API-Arg": json.dumps({
                "url": shared_url,
                "path": remote_path
            })
        }
        
        response = requests.post(url, headers=headers, stream=True)
        
        if response.status_code == 200:
            with open(local_dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            logger.error(f"Error en API cruda de Dropbox (Descarga): {response.text}")
            return False

    def extract_target_documents(self, shared_url: str, download_dir: str) -> list:
        """
        Navega la carpeta compartida, busca las carpetas objetivo y descarga.
        """
        # 1. Obtener un token fresco antes de iniciar el proceso
        token = self._get_valid_token()
        if not token:
            logger.error("No se pudo obtener un token de Dropbox válido. Abortando descarga para este cliente.")
            return []

        downloaded_files = []
        try:
            # Le pasamos el token a nuestras funciones crudas
            root_entries = self._list_folder_raw("", shared_url, token)
            
            target_folders = []
            found_uscis = False

            for entry in root_entries:
                if entry.get(".tag") == "folder":
                    folder_name = entry.get("name", "")
                    
                    is_uscis = self._contains_keyword(folder_name, self.TARGET_KEYWORDS)
                    is_supporting = self.SUPPORTING_DOCS_KEYWORD in folder_name.lower()
                    
                    if is_uscis:
                        found_uscis = True
                        target_folders.append(folder_name)
                    elif is_supporting:
                        target_folders.append(folder_name)

            if not found_uscis:
                logger.warning(f"No se encontró carpeta relacionada a USCIS en: {shared_url}")
                return []

            os.makedirs(download_dir, exist_ok=True)

            for folder_name in target_folders:
                logger.info(f"Explorando subcarpeta encontrada: '{folder_name}'...")
                subfolder_path = f"/{folder_name}"
                
                sub_entries = self._list_folder_raw(subfolder_path, shared_url, token)
                
                for item in sub_entries:
                    if item.get(".tag") == "file":
                        file_name = item.get("name", "")
                        ext = os.path.splitext(file_name)[1].lower()
                        
                        if ext in self.ALLOWED_EXTENSIONS:
                            local_path = os.path.join(download_dir, file_name)
                            logger.info(f"Descargando: {file_name}...")
                            
                            remote_file_path = f"{subfolder_path}/{file_name}"
                            success = self._download_file_raw(shared_url, remote_file_path, local_path, token)
                            
                            if success:
                                downloaded_files.append(local_path)

            logger.info(f"Proceso finalizado. Total de documentos descargados: {len(downloaded_files)}")
            return downloaded_files

        except Exception as e:
            logger.error(f"Error general accediendo al enlace de Dropbox ({shared_url}): {e}")
            return []

# Instancia global del servicio
dropbox_service = DropboxService()