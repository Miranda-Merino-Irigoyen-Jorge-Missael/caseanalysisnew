import logging
import sys
from src.workflows.analysis_workflow import analysis_workflow

# Configuración profesional de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ejecucion.log", mode='a', encoding='utf-8')
    ]
)

logger = logging.getLogger("main")

def main():
    print("\n" + "="*60)
    print(" PIPELINE DE ANÁLISIS DOCUMENTAL (USCIS / PERMANENT BAR)")
    print("="*60 + "\n")

    try:
        # Detona el flujo de trabajo orquestado
        analysis_workflow.run()
        
    except KeyboardInterrupt:
        logger.warning("Proceso detenido manualmente por el usuario (Ctrl+C).")
    except Exception as e:
        logger.error(f"ERROR FATAL NO CONTROLADO: {e}", exc_info=True)
    finally:
        print("\n" + "="*60)
        print(" SISTEMA DETENIDO")
        print("="*60 + "\n")

if __name__ == "__main__":
    main()