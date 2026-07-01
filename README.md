# Pipeline de Análisis Documental — VAWA / Permanent Bar

Automatización que lee casos de clientes desde **Google Sheets**, descarga sus documentos de **Dropbox**, los analiza con **Gemini (Vertex AI)** y escribe los resultados de vuelta en la hoja de cálculo.

---

## ¿Qué hace este proyecto?

Para cada cliente con un caso pendiente, el sistema determina automáticamente:

1. **¿Tiene Permanent Bar (barra permanente) con EUA?**
2. **¿Cuántos delitos tiene y cuáles son?**
3. **¿En qué documento se encontró la información?**

---

## Flujo de trabajo paso a paso

```
Google Sheets  →  Dropbox  →  Gemini AI  →  Google Sheets
(casos pendientes)  (descarga docs)  (analiza)  (escribe resultados)
```

### 1. Leer casos pendientes — `SheetsService`
- Se conecta a Google Sheets usando OAuth2.
- Lee todas las filas de la hoja `ANALISIS IA`.
- Una fila se considera **pendiente** si tiene un link de Dropbox en la columna C pero la columna D (PERMANENT BAR) está vacía.
- Retorna la lista de clientes a procesar.

### 2. Descargar documentos — `DropboxService`
- Recibe el link de carpeta compartida de Dropbox de cada cliente.
- Lista el contenido de la carpeta raíz vía la API HTTP de Dropbox.
- Busca subcarpetas cuyo nombre contenga `uscis`, `ucis` o `usis` — estas son las carpetas objetivo obligatorias.
- También descarga subcarpetas llamadas `supporting documents` si existen.
- Si no encuentra ninguna carpeta USCIS, omite al cliente y lo marca sin documentos.
- Descarga todos los archivos `.pdf`, `.jpg`, `.jpeg` y `.png` encontrados en esas subcarpetas a una carpeta temporal local (`temp_downloads/cliente_<fila>/`).

### 3. Procesar documentos — `DocumentProcessor`
- Lee cada archivo descargado en bytes crudos.
- Detecta su tipo MIME (PDF o imagen).
- Empaqueta los datos listos para enviarlos directamente a Gemini sin transformaciones.

### 4. Analizar con IA — `GeminiClient` (Vertex AI)
- Inicializa el modelo `gemini-3.5-flash` en Vertex AI.
- Construye un prompt con instrucciones precisas y adjunta todos los documentos de forma nativa (sin convertir a texto).
- Le pide a Gemini que responda **exclusivamente en JSON** con esta estructura:

```json
{
    "permanent_bar": "Si tiene PB" | "No tiene PB",
    "referencia": "nombre del documento fuente",
    "numero_delitos": "0",
    "delitos": "N/A"
}
```

- Temperatura baja (`0.1`) para minimizar alucinaciones.

### 5. Escribir resultados — `SheetsService`
- Toma el JSON de respuesta y escribe en las columnas D–G de la fila correspondiente:

| Columna | Dato |
|---------|------|
| D | Permanent Bar (Si/No) |
| E | Referencia (documento fuente) |
| F | Número de delitos |
| G | Lista de delitos |

- Usa reintentos automáticos (hasta 3 veces con backoff exponencial) ante errores de la API de Sheets.

### 6. Limpieza
- Al terminar cada cliente (con éxito o con error), se elimina la carpeta temporal local.

---

## Estructura del proyecto

```
main.py                          # Punto de entrada
src/
  config.py                      # Variables de entorno y validación
  core/
    ai_client.py                 # Cliente Gemini / Vertex AI
    google_client.py             # Autenticación OAuth Google
  services/
    dropbox_service.py           # Descarga de documentos desde Dropbox
    document_processor.py        # Lectura y preparación de archivos
    sheets_service.py            # Lectura y escritura en Google Sheets
  workflows/
    analysis_workflow.py         # Orquestador principal del flujo
```

---

## Configuración (`.env`)

```env
PROJECT_ID=<tu-proyecto-gcp>
LOCATION=us-east5
SPREADSHEET_ID=<id-de-la-hoja>
SHEET_NAME=ANALISIS IA
DROPBOX_TOKEN=<token-de-dropbox>
GOOGLE_OAUTH_CLIENT_SECRET=client_secret.json
GOOGLE_OAUTH_TOKEN=token.json
```

---

## Instalación y ejecución

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar el pipeline
python main.py
```

Los logs se escriben en consola y en el archivo `ejecucion.log`.

---

## Dependencias principales

| Librería | Uso |
|----------|-----|
| `gspread` | Leer y escribir en Google Sheets |
| `google-cloud-aiplatform` | Gemini via Vertex AI |
| `requests` | Llamadas HTTP crudas a la API de Dropbox |
| `tenacity` | Reintentos automáticos con backoff |
| `python-dotenv` | Carga de variables de entorno |
