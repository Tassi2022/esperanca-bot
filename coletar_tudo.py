import time
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    filename='/home/tassi/esperanca_bot/coleta.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s'
)

def log(msg):
    logging.info(msg)
    print(msg)

from src.monitor_concorrentes import (
    buscar_historico_mensal, salvar_historico,
    buscar_posts_e_curtidas_24meses, salvar_curtidas,
    CONCORRENTES
)
import sqlite3

DB_PATH = Path('/home/tassi/esperanca_bot/esperanca.db')

log("=== INICIO COLETA AUTOMATICA ===")

# 1. Historico mensal
log("--- HISTORICO MENSAL ---")
for c in CONCORRENTES:
    try:
        log(f"Historico: {c['username']}")
        hist = buscar_historico_mensal(c['username'])
        log(f"Meses encontrados: {len(hist)}")
        if hist:
            salvar_historico(c['nome'], c['username'], hist)
            log(f"Salvo: {c['username']}")
    except Exception as e:
        log(f"Erro {c['username']}: {e}")
    time.sleep(90)

log("Aguardando 10min antes de coletar curtidas...")
time.sleep(600)

# 2. Curtidas e posts 24 meses
log("--- CURTIDAS E POSTS ---")
for c in CONCORRENTES:
    try:
        log(f"Curtidas: {c['username']}")
        posts24, curtidas24 = buscar_posts_e_curtidas_24meses(c['username'])
        log(f"Posts: {posts24} | Curtidas: {curtidas24}")
        salvar_curtidas({'username': c['username'], 'nome': c['nome'], 'total_curtidas': curtidas24})
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('UPDATE concorrentes SET posts=? WHERE username=? AND id=(SELECT MAX(id) FROM concorrentes WHERE username=?)',
            (posts24, c['username'], c['username']))
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"Erro {c['username']}: {e}")
    time.sleep(90)

log("=== COLETA FINALIZADA ===")
