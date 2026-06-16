import requests
import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

RAPIDAPI_KEY = "e7ddbb8d15msh2d3a66faf7bcfd6p175ea8jsna0e072e97f40"
RAPIDAPI_HOST = "instagram-scraper-stable-api.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-host": RAPIDAPI_HOST,
    "x-rapidapi-key": RAPIDAPI_KEY,
}


RAPIDAPI_HOST2 = "instagram-public-bulk-scraper.p.rapidapi.com"
HEADERS2 = {
    "Content-Type": "application/json",
    "x-rapidapi-host": RAPIDAPI_HOST2,
    "x-rapidapi-key": RAPIDAPI_KEY,
}

def buscar_posts_nova_api(username, paginas=3):
    from datetime import datetime, timedelta
    url = f"https://{RAPIDAPI_HOST2}/v2/user_posts"
    todos = []
    cursor = None
    limite = datetime.now() - timedelta(days=730)
    for _ in range(paginas):
        params = {"username_or_id": username}
        if cursor:
            params["max_id"] = cursor
        r = requests.get(url, headers=HEADERS2, params=params, timeout=30)
        r.raise_for_status()
        data = r.json().get("data", {})
        items = data.get("items", [])
        for p in items:
            taken_at = p.get("taken_at") or p.get("device_timestamp")
            if taken_at:
                dt = datetime.fromtimestamp(taken_at)
                if dt < limite:
                    continue
            cap = p.get("caption", {})
            code = p.get("code", "")
            todos.append({
                "codigo": code,
                "link": f"https://instagram.com/p/{code}",
                "curtidas": p.get("like_count", 0) or 0,
                "comentarios": p.get("comment_count", 0) or 0,
                "texto": (cap.get("text","") if isinstance(cap,dict) else str(cap or ""))[:150],
                "taken_at": taken_at,
            })
        if not data.get("more_available"):
            break
        cursor = data.get("next_max_id") or data.get("items_cursor")
        if not cursor:
            break
        time.sleep(2)
    return sorted(todos, key=lambda x: x["curtidas"], reverse=True)

def buscar_historico_nova_api(username):
    from datetime import datetime, timedelta
    url = f"https://{RAPIDAPI_HOST2}/v2/user_posts"
    historico = {}
    cursor = None
    limite = datetime.now() - timedelta(days=730)
    paginas = 0
    while paginas < 20:
        params = {"username_or_id": username}
        if cursor:
            params["max_id"] = cursor
        try:
            r = requests.get(url, headers=HEADERS2, params=params, timeout=30)
            r.raise_for_status()
        except Exception as e:
            logger.error(f"Erro nova API {username}: {e}")
            break
        data = r.json().get("data", {})
        items = data.get("items", [])
        for p in items:
            taken_at = p.get("taken_at") or p.get("device_timestamp")
            if not taken_at:
                continue
            dt = datetime.fromtimestamp(taken_at)
            if dt < limite:
                continue
            chave = f"{dt.year}-{dt.month:02d}"
            if chave not in historico:
                historico[chave] = {"curtidas": 0, "posts": 0}
            historico[chave]["curtidas"] += p.get("like_count", 0) or 0
            historico[chave]["posts"] += 1
        if not data.get("more_available"):
            break
        cursor = data.get("next_max_id") or data.get("items_cursor")
        if not cursor:
            break
        paginas += 1
        time.sleep(2)
    return historico

# Concorrentes por pizzaria
CONCORRENTES_POR_PIZZARIA = {
    "esperanca": [
        {"nome": "1900 Pizzeria",    "username": "1900pizzeria"},
        {"nome": "Cezanne",          "username": "pizzeria_cezanne"},
        {"nome": "Veridiana",        "username": "veridianapizzaria"},
        {"nome": "Braz",             "username": "brazpizzaria"},
        {"nome": "Sala VIP",         "username": "salavip_pizzabar"},
        {"nome": "Forno e Oregano",  "username": "fornoeoregano"},
    ],
    "alphaville": [
        {"nome": "Casa da Pizza",    "username": "casadapizza.com.br"},
        {"nome": "Soggiorno",        "username": "pizzariasoggiorno"},
        {"nome": "Tarantella",       "username": "tarantellapizzaria"},
        {"nome": "La Fiorella",      "username": "lafiorella"},
        {"nome": "Braz",             "username": "brazpizzaria"},
    ],
    "brooklin": [
        {"nome": "Veridiana",        "username": "veridianapizzaria"},
        {"nome": "Braz",             "username": "brazpizzaria"},
        {"nome": "Camelo",           "username": "pizzariacamelo"},
        {"nome": "Micheluccio",      "username": "michelucciopizzaria"},
        {"nome": "1900 Pizzeria",    "username": "1900pizzeria"},
        {"nome": "Casa da Pizza",    "username": "casadapizza.com.br"},
    ],
    "itaim": [
        {"nome": "Veridiana",        "username": "veridianapizzaria"},
        {"nome": "Braz",             "username": "brazpizzaria"},
        {"nome": "Camelo",           "username": "pizzariacamelo"},
        {"nome": "Micheluccio",      "username": "michelucciopizzaria"},
        {"nome": "1900 Pizzeria",    "username": "1900pizzeria"},
        {"nome": "Casa da Pizza",    "username": "casadapizza.com.br"},
    ],
    "morumbi": [
        {"nome": "Micheluccio",      "username": "michelucciopizzaria"},
        {"nome": "Bella Italia",     "username": "bellaitaliapizzaria"},
        {"nome": "Casa da Pizza",    "username": "casadapizza.com.br"},
        {"nome": "1900 Pizzeria",    "username": "1900pizzeria"},
    ],
    "saude": [
        {"nome": "1900 Pizzeria",    "username": "1900pizzeria"},
        {"nome": "Cezanne",          "username": "pizzeria_cezanne"},
        {"nome": "Veridiana",        "username": "veridianapizzaria"},
        {"nome": "Braz",             "username": "brazpizzaria"},
        {"nome": "Sala VIP",         "username": "salavip_pizzabar"},
        {"nome": "Forno e Oregano",  "username": "fornoeoregano"},
    ],
    "vl_madalena": [
        {"nome": "Braz",             "username": "brazpizzaria"},
        {"nome": "Veridiana",        "username": "veridianapizzaria"},
        {"nome": "1900 Pizzeria",    "username": "1900pizzeria"},
        {"nome": "Casa da Pizza",    "username": "casadapizza.com.br"},
        {"nome": "Rascal",           "username": "rascalrestaurante"},
    ],
    "vl_mariana": [
        {"nome": "Veridiana",        "username": "veridianapizzaria"},
        {"nome": "Cezanne",          "username": "pizzeria_cezanne"},
        {"nome": "Braz",             "username": "brazpizzaria"},
        {"nome": "Micheluccio",      "username": "michelucciopizzaria"},
        {"nome": "Pizza da Mooca",   "username": "pizzadamooca"},
        {"nome": "1900 Pizzeria",    "username": "1900pizzeria"},
    ],
}

# Lista padrão (compatibilidade)
CONCORRENTES = CONCORRENTES_POR_PIZZARIA.get("esperanca", [])

DB_PATH = Path(__file__).parent.parent / "esperanca.db"

def init_db_concorrentes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS concorrentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT, nome TEXT, seguidores INTEGER,
        seguindo INTEGER, posts INTEGER, coletado_em TEXT
    )""")
    conn.commit()
    conn.close()

def buscar_perfil(username):
    url_posts = f"https://{RAPIDAPI_HOST}/get_ig_user_posts.php"
    url_media = f"https://{RAPIDAPI_HOST}/get_media_data.php"
    try:
        # Pega o codigo do primeiro post
        r = requests.post(url_posts, headers=HEADERS, data={"username_or_url": username}, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) or not data.get("posts"):
            return None
        code = data["posts"][0]["node"]["code"]

        # Busca dados do perfil via post
        r2 = requests.get(url_media, headers=HEADERS, params={"reel_post_code_or_url": code, "type": "post"}, timeout=30)
        r2.raise_for_status()
        info = r2.json()
        owner = info.get("owner", {})
        return {
            "username": username,
            "seguidores": owner.get("edge_followed_by", {}).get("count", 0),
            "seguindo": 0,
            "posts": owner.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "nome": owner.get("full_name", username),
        }
    except Exception as e:
        logger.error(f"Erro ao buscar {username}: {e}")
        return None


def buscar_posts_e_curtidas_24meses(username):
    from datetime import datetime, timedelta
    url = f"https://{RAPIDAPI_HOST}/get_ig_user_posts.php"
    total_curtidas = 0
    total_posts = 0
    pagination_token = None
    limite = datetime.now() - timedelta(days=730)
    paginas = 0
    try:
        while paginas < 20:
            data = {"username_or_url": username}
            if pagination_token:
                data["pagination_token"] = pagination_token
            r = requests.post(url, headers=HEADERS, data=data, timeout=30)
            r.raise_for_status()
            result = r.json()
            if isinstance(result, list):
                break
            posts = result.get("posts", [])
            if not posts:
                break
            for post in posts:
                node = post.get("node", {})
                taken_at = node.get("taken_at")
                if not taken_at:
                    continue
                dt = datetime.fromtimestamp(taken_at)
                if dt < limite:
                    continue
                total_curtidas += node.get("like_count", 0) or 0
                total_posts += 1
            pagination_token = result.get("pagination_token")
            paginas += 1
            if not pagination_token:
                break
            time.sleep(2)
    except Exception as e:
        logger.error(f"Erro posts24 {username}: {e}")
    return total_posts, total_curtidas

def salvar_concorrente(dados):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO concorrentes (username,nome,seguidores,seguindo,posts,coletado_em) VALUES (?,?,?,?,?,?)",
        (dados["username"], dados["nome"], dados["seguidores"],
         dados["seguindo"], dados["posts"], datetime.now().strftime("%d/%m %H:%M")))
    conn.commit()
    conn.close()

def coletar_concorrentes():
    init_db_concorrentes()
    resultados = []
    for c in CONCORRENTES:
        logger.info(f"Buscando {c['username']}...")
        dados = buscar_perfil(c["username"])
        if dados:
            dados["nome"] = c["nome"]
            salvar_concorrente(dados)
            resultados.append(dados)
    return resultados

def listar_concorrentes_atual(pizzaria_id=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if pizzaria_id:
        c.execute("""
            SELECT c1.* FROM concorrentes c1
            INNER JOIN (
                SELECT username, MAX(id) as max_id FROM concorrentes WHERE pizzaria_id=? GROUP BY username
            ) c2 ON c1.username = c2.username AND c1.id = c2.max_id
            ORDER BY seguidores DESC
        """, (pizzaria_id,))
    else:
        c.execute("""
            SELECT c1.* FROM concorrentes c1
            INNER JOIN (
                SELECT username, MAX(id) as max_id FROM concorrentes GROUP BY username
            ) c2 ON c1.username = c2.username AND c1.id = c2.max_id
            ORDER BY seguidores DESC
        """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def buscar_user_id(username):
    url = f"https://{RAPIDAPI_HOST}/profile"
    try:
        r = requests.get(url, headers=HEADERS, params={"username": username}, timeout=30)
        r.raise_for_status()
        return str(r.json().get("id", ""))
    except Exception as e:
        logger.error(f"Erro ao buscar ID de {username}: {e}")
        return ""

def buscar_posts_perfil(username, count=12):
    from datetime import datetime, timedelta
    url = f"https://{RAPIDAPI_HOST}/get_ig_user_posts.php"
    todos_posts = []
    pagination_token = None
    limite = datetime.now() - timedelta(days=730)
    paginas = 0
    try:
        while paginas < 3:
            data = {"username_or_url": username}
            if pagination_token:
                data["pagination_token"] = pagination_token
            r = requests.post(url, headers=HEADERS, data=data, timeout=30)
            r.raise_for_status()
            result = r.json()
            if isinstance(result, list):
                break
            posts = result.get("posts", [])
            if not posts:
                break
            for item in posts:
                node = item.get("node", {})
                taken_at = node.get("taken_at")
                if taken_at:
                    dt = datetime.fromtimestamp(taken_at)
                    if dt < limite:
                        continue
                caption = node.get("caption") or {}
                code = node.get("code", "")
                todos_posts.append({
                    "codigo": code,
                    "link": f"https://instagram.com/p/{code}",
                    "curtidas": node.get("like_count", 0) or 0,
                    "comentarios": node.get("comment_count", 0) or 0,
                    "texto": caption.get("text", "")[:150] if caption else "",
                })
            pagination_token = result.get("pagination_token")
            paginas += 1
            if not pagination_token:
                break
            time.sleep(1)
    except Exception as e:
        logger.error(f"Erro ao buscar posts {username}: {e}")
    return sorted(todos_posts, key=lambda x: x["curtidas"], reverse=True)[:count]


def buscar_total_curtidas(username):
    from datetime import datetime, timedelta
    url = f"https://{RAPIDAPI_HOST}/get_ig_user_posts.php"
    total = 0
    pagination_token = None
    limite = datetime.now() - timedelta(days=730)
    paginas = 0
    try:
        while paginas < 20:
            data = {"username_or_url": username}
            if pagination_token:
                data["pagination_token"] = pagination_token
            r = requests.post(url, headers=HEADERS, data=data, timeout=30)
            r.raise_for_status()
            result = r.json()
            if isinstance(result, list):
                break
            posts = result.get("posts", [])
            if not posts:
                break
            for post in posts:
                node = post.get("node", {})
                taken_at = node.get("taken_at")
                if not taken_at:
                    continue
                dt = datetime.fromtimestamp(taken_at)
                if dt < limite:
                    continue
                total += node.get("like_count", 0) or 0
            pagination_token = result.get("pagination_token")
            paginas += 1
            if not pagination_token:
                break
            time.sleep(2)
    except Exception as e:
        logger.error(f"Erro curtidas {username}: {e}")
    return total

def salvar_curtidas(dados):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO curtidas_concorrentes (username,nome,total_curtidas,coletado_em) VALUES (?,?,?,?)",
        (dados["username"], dados["nome"], dados["total_curtidas"],
         datetime.now().strftime("%d/%m %H:%M")))
    conn.commit()
    conn.close()

def listar_curtidas_atual():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT c1.* FROM curtidas_concorrentes c1
        INNER JOIN (
            SELECT username, MAX(id) as max_id FROM curtidas_concorrentes GROUP BY username
        ) c2 ON c1.username = c2.username AND c1.id = c2.max_id
        ORDER BY total_curtidas DESC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def listar_curtidas_concorrentes():
    resultados = []
    for c in CONCORRENTES:
        total = buscar_total_curtidas(c["username"])
        resultados.append({
            "nome": c["nome"],
            "username": c["username"],
            "total_curtidas": total
        })
    return resultados




def salvar_historico(nome, username, historico):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM historico_mensal WHERE username=?", (username,))
    for ano_mes, dados in historico.items():
        c.execute("INSERT INTO historico_mensal (username,nome,ano_mes,curtidas,posts,coletado_em) VALUES (?,?,?,?,?,?)",
            (username, nome, ano_mes, dados["curtidas"], dados["posts"],
             datetime.now().strftime("%d/%m %H:%M")))
    conn.commit()
    conn.close()

def listar_historico_mensal():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM historico_mensal ORDER BY username, ano_mes")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows




def buscar_historico_mensal(username):
    from datetime import datetime, timedelta
    url = f"https://{RAPIDAPI_HOST}/get_ig_user_posts.php"
    historico = {}
    pagination_token = None
    limite = datetime.now() - timedelta(days=730)
    paginas = 0
    try:
        while paginas < 30:
            data = {"username_or_url": username}
            if pagination_token:
                data["pagination_token"] = pagination_token
            r = requests.post(url, headers=HEADERS, data=data, timeout=30)
            r.raise_for_status()
            result = r.json()
            if isinstance(result, list):
                break
            posts = result.get("posts", [])
            if not posts:
                break
            for post in posts:
                node = post.get("node", {})
                taken_at = node.get("taken_at")
                if not taken_at:
                    continue
                dt = datetime.fromtimestamp(taken_at)
                if dt < limite:
                    continue
                chave = f"{dt.year}-{dt.month:02d}"
                if chave not in historico:
                    historico[chave] = {"curtidas": 0, "posts": 0}
                historico[chave]["curtidas"] += node.get("like_count", 0) or 0
                historico[chave]["posts"] += 1
            pagination_token = result.get("pagination_token")
            paginas += 1
            if not pagination_token:
                break
            time.sleep(1)
    except Exception as e:
        logger.error(f"Erro historico {username}: {e}")
    return historico
