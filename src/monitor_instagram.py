import requests
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

RAPIDAPI_KEY = "e7ddbb8d15msh2d3a66faf7bcfd6p175ea8jsna0e072e97f40"
RAPIDAPI_HOST = "instagram-looter2.p.rapidapi.com"

HEADERS = {
    "Content-Type": "application/json",
    "x-rapidapi-host": RAPIDAPI_HOST,
    "x-rapidapi-key": RAPIDAPI_KEY,
}


def buscar_posts_hashtag(hashtag: str, max_posts: int = 20) -> List[Dict]:
    url = f"https://{RAPIDAPI_HOST}/tag-feeds"
    params = {"query": hashtag}
    posts = []
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        edges = data.get("data", {}).get("hashtag", {}).get("edge_hashtag_to_media", {}).get("edges", [])
        if not edges:
            edges = data.get("data", {}).get("recent", {}).get("edges", [])
        if not edges:
            logger.warning(f"#{hashtag}: sem posts retornados")
            return []

        for edge in edges[:max_posts]:
            node = edge.get("node", {})
            shortcode = node.get("shortcode") or node.get("id", "")
            if not shortcode:
                continue
            caption = ""
            try:
                caption = (
                    node.get("edge_media_to_caption", {})
                        .get("edges", [{}])[0]
                        .get("node", {})
                        .get("text", "") or ""
                )
            except (IndexError, AttributeError):
                caption = ""
            owner = node.get("owner") or {}
            usuario = owner.get("username") or "@usuario"
            posts.append({
                "id": str(shortcode),
                "shortcode": str(shortcode),
                "link": f"https://www.instagram.com/p/{shortcode}/",
                "texto": caption[:400],
                "usuario": usuario,
                "timestamp": datetime.now().timestamp(),
                "hashtag_origem": hashtag,
            })
        logger.info(f"#{hashtag}: {len(posts)} posts encontrados")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Erro HTTP #{hashtag}: {e.response.status_code} - {e.response.text[:200]}")
    except Exception as e:
        logger.error(f"Erro #{hashtag}: {e}")
    return posts


def filtrar_posts_relevantes(posts, palavras_chave, palavras_urgentes):
    try:
        from config.settings import PALAVRAS_IGNORAR
    except ImportError:
        PALAVRAS_IGNORAR = []
    relevantes = []
    vistos = set()
    for post in posts:
        if post["id"] in vistos:
            continue
        vistos.add(post["id"])
        texto_lower = post["texto"].lower()
        if any(p.lower() in texto_lower for p in PALAVRAS_IGNORAR):
            continue
        if not any(p.lower() in texto_lower for p in palavras_chave):
            continue
        post["urgente"] = any(u.lower() in texto_lower for u in palavras_urgentes)
        post["timestamp_fmt"] = datetime.now().strftime("%d/%m %H:%M")
        relevantes.append(post)
    return relevantes


def coletar_todas_hashtags(hashtags, palavras_chave, palavras_urgentes):
    todos = []
    ids_vistos = set()
    for hashtag in hashtags:
        posts = buscar_posts_hashtag(hashtag)
        for post in filtrar_posts_relevantes(posts, palavras_chave, palavras_urgentes):
            if post["id"] not in ids_vistos:
                ids_vistos.add(post["id"])
                todos.append(post)
    todos.sort(key=lambda x: (not x["urgente"], -x["timestamp"]))
    logger.info(f"Total coletado: {len(todos)} posts relevantes")
    return todos
def buscar_historico_mensal(username):
    import time
    from datetime import datetime
    url = f"https://{RAPIDAPI_HOST}/get_ig_user_posts.php"
    historico = {}
    pagination_token = None
    try:
        while True:
            data = {"username_or_url": username}
            if pagination_token:
                data["pagination_token"] = pagination_token
            r = requests.post(url, headers=HEADERS, data=data, timeout=30)
            r.raise_for_status()
            result = r.json()
            if isinstance(result, list):
                break
            posts = result.get("posts", [])
            for post in posts:
                node = post.get("node", {})
                taken_at = node.get("taken_at")
                if not taken_at:
                    continue
                dt = datetime.fromtimestamp(taken_at)
                chave = f"{dt.year}-{dt.month:02d}"
                if chave not in historico:
                    historico[chave] = {"curtidas": 0, "posts": 0}
                historico[chave]["curtidas"] += node.get("like_count", 0) or 0
                historico[chave]["posts"] += 1
            pagination_token = result.get("pagination_token")
            if not pagination_token or not posts:
                break
            time.sleep(2)
    except Exception as e:
        logger.error(f"Erro ao buscar historico de {username}: {e}")
    return historico
