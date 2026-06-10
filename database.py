import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "esperanca.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS oportunidades (
        id TEXT PRIMARY KEY, usuario TEXT, texto TEXT,
        hashtag TEXT, link TEXT, resposta TEXT,
        urgente INTEGER DEFAULT 0, respondida INTEGER DEFAULT 0, criado_em TEXT
    )""")
    conn.commit()
    conn.close()

def salvar_oportunidade(post, resposta):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO oportunidades (id,usuario,texto,hashtag,link,resposta,urgente,respondida,criado_em) VALUES (?,?,?,?,?,?,?,?,?)",
        (post["id"], post.get("usuario","@usuario"), post["texto"], post["hashtag_origem"],
         post["link"], resposta, 1 if post.get("urgente") else 0, 0,
         datetime.now().strftime("%d/%m %H:%M")))
    conn.commit()
    conn.close()

def listar_datas():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT substr(criado_em,1,5) as dia FROM oportunidades ORDER BY dia DESC")
    datas = [r[0] for r in c.fetchall()]
    conn.close()
    return datas

def listar_oportunidades(filtro="todas", data=""):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    filtro_data = f" AND criado_em LIKE '{data}%'" if data else ""
    if filtro == "urgentes":
        c.execute(f"SELECT * FROM oportunidades WHERE urgente=1 AND respondida=0{filtro_data} ORDER BY criado_em DESC")
    elif filtro == "pendentes":
        c.execute(f"SELECT * FROM oportunidades WHERE respondida=0{filtro_data} ORDER BY criado_em DESC")
    elif filtro == "respondidas":
        c.execute(f"SELECT * FROM oportunidades WHERE respondida=1{filtro_data} ORDER BY criado_em DESC")
    else:
        c.execute(f"SELECT * FROM oportunidades WHERE 1=1{filtro_data} ORDER BY urgente DESC, criado_em DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def marcar_respondida(op_id, valor):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE oportunidades SET respondida=? WHERE id=?", (valor, op_id))
    conn.commit()
    conn.close()

def stats(data=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    filtro_data = f" AND criado_em LIKE '{data}%'" if data else ""
    c.execute(f"SELECT COUNT(*) FROM oportunidades WHERE 1=1{filtro_data}"); total = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM oportunidades WHERE urgente=1 AND respondida=0{filtro_data}"); urgentes = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM oportunidades WHERE respondida=1{filtro_data}"); respondidas = c.fetchone()[0]
    conn.close()
    taxa = round((respondidas / total * 100)) if total > 0 else 0
    return {"total": total, "urgentes": urgentes, "respondidas": respondidas, "taxa": taxa}

init_db()
