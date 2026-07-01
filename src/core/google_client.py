import os
import logging
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from src.config import Config

logger = logging.getLogger(__name__)

class GoogleClientManager:
    """
    Maneja las conexiones autenticadas a las APIs de Google usando OAuth 2.0.
    Implementa un patrón Singleton para evitar múltiples autenticaciones en la misma ejecución.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GoogleClientManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._oauth_creds = None
        self._sheets_client = None
        self._initialized = True

    def _get_oauth_creds(self):
        """Carga o genera las credenciales OAuth (token.json)."""
        if not self._oauth_creds:
            try:
                # 1. Intentar cargar el token existente
                if os.path.exists(Config.TOKEN_FILE):
                    self._oauth_creds = Credentials.from_authorized_user_file(
                        Config.TOKEN_FILE, Config.OAUTH_SCOPES
                    )
                    
                    # Refrescar el token si ha expirado
                    if self._oauth_creds and self._oauth_creds.expired and self._oauth_creds.refresh_token:
                        self._oauth_creds.refresh(Request())
                        with open(Config.TOKEN_FILE, 'w') as token:
                            token.write(self._oauth_creds.to_json())
                    elif not self._oauth_creds.valid:
                        self._oauth_creds = None

                # 2. Si no hay token válido, iniciar flujo de login en el navegador
                if not self._oauth_creds:
                    if not os.path.exists(Config.OAUTH_CREDENTIALS_FILE):
                        raise FileNotFoundError(
                            f"Falta el archivo de credenciales: {Config.OAUTH_CREDENTIALS_FILE}. "
                            "Asegúrate de descargarlo desde Google Cloud Console."
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        Config.OAUTH_CREDENTIALS_FILE, 
                        Config.OAUTH_SCOPES
                    )
                    self._oauth_creds = flow.run_local_server(port=0)
                    
                    # Guardar el token para futuras ejecuciones
                    with open(Config.TOKEN_FILE, 'w') as token:
                        token.write(self._oauth_creds.to_json())
                        
            except Exception as e:
                logger.error(f"Error en autenticación OAuth: {e}")
                raise
                
        return self._oauth_creds

    def get_sheets_client(self):
        """Retorna el cliente de gspread autorizado para manipular hojas de cálculo."""
        if not self._sheets_client:
            creds = self._get_oauth_creds()
            self._sheets_client = gspread.authorize(creds)
        return self._sheets_client

# Instancia global para importar en el resto del proyecto
google_manager = GoogleClientManager()