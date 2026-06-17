"""
src/monitor_ifood.py
Coleta dados dos concorrentes no iFood via API oficial (marketplace.ifood.com.br).
Funciona 100% no PythonAnywhere free tier.
"""

import json
import logging
import random
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "esperanca.db"

# ---------------------------------------------------------------------------
# Restaurantes monitorados — UUID vem da URL do iFood
# ---------------------------------------------------------------------------
RESTAURANTES_IFOOD = [
    {"nome": "A EsperancA",     "uuid": "0417766b-1fd7-4fc2-aa00-b9f8a1c19199", "nos": True},
    {"nome": "1900 Pizzeria",   "uuid": "b779bdec-2108-4ed4-93ad-24bb5a73c714", "nos": False},
    {"nome": "Cezanne",         "uuid": "d14fc179-a92a-48d8-b0e0-bad9002d6e41", "nos": False},
    {"nome": "SalaVip",         "uuid": "8847d86f-7cec-4407-8b57-14dd12427bf6", "nos": False},
    {"nome": "Forno e Orégano", "uuid": "8d3ffb5a-337e-45b7-baec-d46897e3c381", "nos": False},
    {"nome": "Veridiana",       "uuid": "65f84e1b-90ec-4753-8cb0-a6330539cc38", "nos": False},
]

# Coordenadas do bairro Saúde — São Paulo
LAT = "-23.6012"
LON = "-46.6358"

API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://www.ifood.com.br",
    "Referer": "https://www.ifood.com.br/",
    "accept": "application/json",
    "platform": "Desktop",
    "browser": "Chrome",
    "app_version": "9.50.3",
}

API_PARAMS = {
    "latitude": LAT,
    "longitude": LON,
    "channel": "IFOOD",
}

# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

def init_ifood_db():
    """Cria as tabelas do iFood se não existirem."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS ifood_restaurantes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nome             TEXT,
            uuid             TEXT,
            rating           REAL,
            total_avaliacoes INTEGER,
            categoria        TEXT,
            tempo_min        INTEGER,
            tempo_max        INTEGER,
            taxa_entrega     REAL,
            taxa_gratis      INTEGER DEFAULT 0,
            distancia_km     REAL,
            aberto           INTEGER DEFAULT 1,
            promocao         TEXT,
            price_range      TEXT,
            url              TEXT,
            coletado_em      TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS ifood_categoria (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria    TEXT,
            cidade       TEXT,
            nome         TEXT,
            uuid         TEXT,
            rating       REAL,
            tempo_min    INTEGER,
            taxa_entrega REAL,
            taxa_gratis  INTEGER DEFAULT 0,
            promocao     TEXT,
            coletado_em  TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Tabelas iFood inicializadas.")

# ---------------------------------------------------------------------------
# API iFood
# ---------------------------------------------------------------------------

def _buscar_merchant(uuid: str) -> Optional[dict]:
    """Busca dados de um restaurante pela API oficial do iFood."""
    url = f"https://marketplace.ifood.com.br/v1/merchants/{uuid}"
    for tentativa in range(1, 3):
        try:
            r = httpx.get(url, headers=API_HEADERS, params=API_PARAMS, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning(f"Tentativa {tentativa} falhou para {uuid}: {e}")
            if tentativa < 2:
                time.sleep(3)
    return None


def _buscar_delivery_info(uuid: str) -> Optional[dict]:
    """Busca taxa de entrega e tempo via endpoint de delivery info."""
    url = f"https://marketplace.ifood.com.br/v1/merchants/{uuid}/deliveryInfo"
    try:
        r = httpx.get(url, headers=API_HEADERS, params=API_PARAMS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.debug(f"deliveryInfo falhou para {uuid}: {e}")
    return None


def _parse_merchant(data: dict, nome_config: str, uuid: str) -> dict:
    """Converte resposta da API em dicionário padronizado."""
    # Rating
    rating = data.get("userRating") or data.get("rating")
    if rating:
        rating = round(float(rating), 1)

    # Categoria principal
    main_cat = data.get("mainCategory") or {}
    categoria = main_cat.get("name", "") if isinstance(main_cat, dict) else str(main_cat)

    # Preço range
    price_range = data.get("priceRange", "")
    price_map = {"CHEAPEST": "💰", "CHEAP": "💰💰", "MODERATE": "💰💰💰",
                 "EXPENSIVE": "💰💰💰💰", "MOST_EXPENSIVE": "💰💰💰💰💰"}
    price_range_fmt = price_map.get(price_range, price_range)

    # Tags / promoções
    tags = data.get("tags") or []
    promocao = None
    for tag in tags:
        if any(k in str(tag).upper() for k in ["DISC", "OFF", "PROMO", "FRETE", "GRATIS"]):
            promocao = str(tag)
            break

    # Aberto
    aberto = 1
    if data.get("closed") or data.get("available") is False:
        aberto = 0

    # URL
    slug = data.get("slug", "")
    url_rest = f"https://www.ifood.com.br/delivery/{slug}" if slug else ""

    return {
        "nome": nome_config,
        "uuid": uuid,
        "rating": rating,
        "total_avaliacoes": data.get("numRatings") or data.get("ratingCount"),
        "categoria": categoria,
        "price_range": price_range_fmt,
        "taxa_entrega": None,
        "taxa_gratis": 0,
        "tempo_min": None,
        "tempo_max": None,
        "distancia_km": None,
        "aberto": aberto,
        "promocao": promocao,
        "url": url_rest,
    }


def _enriquecer_delivery(dados: dict, uuid: str) -> dict:
    """Adiciona taxa e tempo de entrega aos dados do restaurante."""
    info = _buscar_delivery_info(uuid)
    if not info:
        return dados

    # Taxa de entrega
    fee = info.get("deliveryFee") or info.get("fee")
    if fee is not None:
        taxa = float(fee) / 100 if float(fee) > 100 else float(fee)
        dados["taxa_entrega"] = taxa
        dados["taxa_gratis"] = 1 if taxa == 0 else 0

    # Tempo de entrega
    dados["tempo_min"] = info.get("minTime") or info.get("deliveryTime")
    dados["tempo_max"] = info.get("maxTime")

    # Distância
    dist = info.get("distance")
    if dist:
        dados["distancia_km"] = round(float(dist) / 1000, 1) if float(dist) > 100 else float(dist)

    return dados

# ---------------------------------------------------------------------------
# Coleta principal
# ---------------------------------------------------------------------------

def coletar_restaurante(uuid: str, nome: str = "") -> Optional[dict]:
    """Coleta dados completos de um restaurante pelo UUID."""
    logger.info(f"Coletando: {nome or uuid}")
    data = _buscar_merchant(uuid)
    if not data:
        return None

    dados = _parse_merchant(data, nome or data.get("name", ""), uuid)
    dados = _enriquecer_delivery(dados, uuid)
    return dados


def coletar_todos_concorrentes() -> list:
    """Coleta dados de todos os restaurantes em RESTAURANTES_IFOOD."""
    init_ifood_db()
    resultados = []
    agora = datetime.now().strftime("%d/%m %H:%M")

    for rest in RESTAURANTES_IFOOD:
        dados = coletar_restaurante(rest["uuid"], rest["nome"])
        if dados:
            dados["coletado_em"] = agora
            _salvar_restaurante(dados)
            resultados.append(dados)
            logger.info(f"✅ {rest['nome']} | rating: {dados.get('rating')} | taxa: {dados.get('taxa_entrega')}")
        else:
            logger.warning(f"❌ Sem dados para {rest['nome']}")

        time.sleep(random.uniform(1.5, 3.0))

    return resultados


def coletar_por_categoria(categoria: str, cidade: str = "sao-paulo-sp", max_itens: int = 20) -> list:
    """
    Busca restaurantes de uma categoria via API do iFood.
    categoria: código iFood — ex: 'PIZ' (pizza), 'HAM' (hambúrguer), 'JAP' (japonesa)
    """
    url = "https://marketplace.ifood.com.br/v1/merchants"
    params = {
        **API_PARAMS,
        "categoryCode": categoria.upper(),
        "size": max_itens,
        "alias": categoria.lower(),
    }
    try:
        r = httpx.get(url, headers=API_HEADERS, params=params, timeout=20)
        if r.status_code != 200:
            logger.warning(f"Categoria '{categoria}': status {r.status_code}")
            return []
        data = r.json()
        merchants = data if isinstance(data, list) else data.get("merchants", data.get("items", []))
        resultados = []
        for m in merchants[:max_itens]:
            uuid = m.get("id") or m.get("uuid")
            nome = m.get("name") or m.get("displayName", "")
            rating = m.get("userRating") or m.get("rating")
            resultados.append({
                "nome": nome,
                "uuid": uuid,
                "rating": round(float(rating), 1) if rating else None,
                "categoria": categoria,
                "cidade": cidade,
                "taxa_entrega": None,
                "taxa_gratis": 0,
                "tempo_min": None,
                "coletado_em": datetime.now().strftime("%d/%m %H:%M"),
            })
        return resultados
    except Exception as e:
        logger.error(f"Erro ao buscar categoria '{categoria}': {e}")
        return []

# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------

def _salvar_restaurante(dados: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO ifood_restaurantes
            (nome, uuid, rating, total_avaliacoes, categoria, tempo_min, tempo_max,
             taxa_entrega, taxa_gratis, distancia_km, aberto, promocao, price_range, url, coletado_em)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        dados.get("nome"), dados.get("uuid"),
        dados.get("rating"), dados.get("total_avaliacoes"),
        dados.get("categoria"),
        dados.get("tempo_min"), dados.get("tempo_max"),
        dados.get("taxa_entrega"), dados.get("taxa_gratis", 0),
        dados.get("distancia_km"), dados.get("aberto", 1),
        dados.get("promocao"), dados.get("price_range"),
        dados.get("url"),
        dados.get("coletado_em", datetime.now().strftime("%d/%m %H:%M")),
    ))
    conn.commit()
    conn.close()


def salvar_categoria(itens: list, categoria: str, cidade: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    agora = datetime.now().strftime("%d/%m %H:%M")
    for item in itens:
        c.execute("""
            INSERT INTO ifood_categoria
                (categoria, cidade, nome, uuid, rating, tempo_min,
                 taxa_entrega, taxa_gratis, promocao, coletado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            categoria, cidade,
            item.get("nome"), item.get("uuid"),
            item.get("rating"), item.get("tempo_min"),
            item.get("taxa_entrega"), item.get("taxa_gratis", 0),
            item.get("promocao"), agora,
        ))
    conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# Queries para o Flask
# ---------------------------------------------------------------------------

def listar_ifood_atual() -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT * FROM ifood_restaurantes
        WHERE id IN (
            SELECT MAX(id) FROM ifood_restaurantes GROUP BY uuid
        )
        ORDER BY rating DESC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def listar_ifood_historico() -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT nome, rating, taxa_entrega, taxa_gratis,
               tempo_min, tempo_max, coletado_em
        FROM ifood_restaurantes
        ORDER BY id ASC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def listar_categoria_atual(categoria: str) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT * FROM ifood_categoria
        WHERE categoria = ?
        AND id IN (
            SELECT MAX(id) FROM ifood_categoria
            WHERE categoria = ? GROUP BY nome
        )
        ORDER BY rating DESC
    """, (categoria, categoria))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# Teste direto no terminal
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_ifood_db()
    print("Coletando todos os concorrentes...")
    resultados = coletar_todos_concorrentes()
    print(f"\nColetados: {len(resultados)} restaurantes")
    for r in resultados:
        taxa = "Grátis" if r.get("taxa_gratis") else f"R$ {r.get('taxa_entrega') or '?'}"
        print(f"  {r['nome']} | ★{r.get('rating')} | {taxa} | {r.get('tempo_min')}-{r.get('tempo_max')} min")