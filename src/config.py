import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    """Configuración centralizada del proyecto de análisis VAWA."""
    
    # Rutas Base
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # Cargar variables de entorno
    load_dotenv(BASE_DIR / ".env")

    # Configuración Vertex AI
    PROJECT_ID = os.getenv("PROJECT_ID")
    LOCATION = os.getenv("LOCATION", "us-east5")
    
    # Configuración Sheets
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
    SHEET_NAME = os.getenv("SHEET_NAME")
    
    # Configuración Dropbox
    DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")

    # Archivos de credenciales OAuth
    OAUTH_CREDENTIALS_FILE = BASE_DIR / os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "client_secret.json")
    TOKEN_FILE = BASE_DIR / os.getenv("GOOGLE_OAUTH_TOKEN", "token.json")

    # Permisos (Scopes) para Google
    # Solo solicitamos acceso a Google Sheets por ahora.
    OAUTH_SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets'
    ]

    @classmethod
    def validate(cls):
        """Valida que las variables críticas existan antes de arrancar el sistema."""
        missing = []
        if not cls.PROJECT_ID: missing.append("PROJECT_ID")
        if not cls.SPREADSHEET_ID: missing.append("SPREADSHEET_ID")
        if not cls.DROPBOX_TOKEN: missing.append("DROPBOX_TOKEN")
        
        if missing:
            raise ValueError(f"Faltan variables críticas en el archivo .env: {', '.join(missing)}")

# Ejecutamos la validación al importar el módulo
Config.validate()