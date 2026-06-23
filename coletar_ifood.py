"""
coletar_ifood.py
Script para coleta automática semanal dos concorrentes iFood.

Configure no PythonAnywhere:
  Tasks → Add a new scheduled task
  Command: python /home/tassi/esperanca_bot/coletar_ifood.py
  Frequency: Weekly (toda segunda-feira às 08:00)
"""

import sys
import logging
from pathlib import Path

# Garante que o projeto está no PATH
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 50)
    logger.info("Iniciando coleta automática iFood...")

    from src.monitor_ifood import coletar_todos_concorrentes, init_ifood_db

    init_ifood_db()
    resultados = coletar_todos_concorrentes()

    logger.info(f"Coleta finalizada: {len(resultados)} restaurantes")
    for r in resultados:
        taxa = "Grátis" if r.get("taxa_gratis") else f"R$ {r.get('taxa_entrega') or '?'}"
        logger.info(f"  {r['nome']:20} | ★{r.get('rating') or '—'} | {taxa}")

    logger.info("=" * 50)


if __name__ == "__main__":
    main()
