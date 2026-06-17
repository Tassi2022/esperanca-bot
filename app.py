from flask import Flask, render_template, jsonify, request
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import listar_oportunidades, marcar_respondida, stats, listar_datas
from src.monitor_concorrentes import (
    listar_concorrentes_atual, coletar_concorrentes, buscar_perfil,
    buscar_user_id, listar_curtidas_concorrentes, salvar_curtidas,
    listar_curtidas_atual, buscar_posts_perfil, buscar_posts_e_curtidas_24meses
)
# ── iFood ─────────────────────────────────────────────────────────────────────
from src.monitor_ifood import (
    coletar_todos_concorrentes, coletar_por_categoria,
    listar_ifood_atual, listar_ifood_historico,
    listar_categoria_atual, salvar_categoria,
    init_ifood_db, RESTAURANTES_IFOOD
)

app = Flask(__name__)
init_ifood_db()   # cria as tabelas do iFood se não existirem

# =============================================================================
# ROTAS EXISTENTES — Dashboard e Instagram
# =============================================================================

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/pizzarias")
def api_pizzarias():
    import sqlite3
    db = Path(__file__).parent / "esperanca.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, nome, bairro FROM pizzarias ORDER BY nome")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/concorrentes")
def concorrentes():
    return render_template("concorrentes.html")

@app.route("/api/oportunidades")
def api_oportunidades():
    filtro = request.args.get("filtro", "todas")
    data = request.args.get("data", "")
    pizzaria_id = request.args.get("pizzaria", "")
    return jsonify(listar_oportunidades(filtro, data, pizzaria_id))

@app.route("/api/stats")
def api_stats():
    data = request.args.get("data", "")
    pizzaria_id = request.args.get("pizzaria", "")
    return jsonify(stats(data, pizzaria_id))

@app.route("/api/datas")
def api_datas():
    return jsonify(listar_datas())

@app.route("/api/responder/<op_id>", methods=["POST"])
def api_responder(op_id):
    valor = request.json.get("valor", 1)
    marcar_respondida(op_id, valor)
    return jsonify({"ok": True})

@app.route("/api/concorrentes")
def api_concorrentes():
    pizzaria_id = request.args.get("pizzaria", "")
    return jsonify(listar_concorrentes_atual(pizzaria_id if pizzaria_id else None))

@app.route("/api/concorrentes/coletar", methods=["POST"])
def api_coletar_concorrentes():
    pizzaria_id = request.json.get("pizzaria_id", "esperanca") if request.json else "esperanca"
    resultados = coletar_concorrentes(pizzaria_id)
    return jsonify({"ok": True, "total": len(resultados)})

@app.route("/api/concorrentes/posts/<username>")
def api_posts_concorrente(username):
    from src.monitor_concorrentes import buscar_posts_nova_api
    try:
        posts = buscar_posts_nova_api(username, paginas=2)
        if posts:
            return jsonify(posts)
    except Exception as e:
        pass
    posts = buscar_posts_perfil(username, count=12)
    return jsonify(posts)

@app.route("/api/concorrentes/curtidas")
def api_curtidas_concorrentes():
    return jsonify(listar_curtidas_atual())

@app.route("/api/concorrentes/curtidas/coletar", methods=["POST"])
def api_coletar_curtidas():
    import threading
    from src.monitor_concorrentes import buscar_total_curtidas, CONCORRENTES
    def coletar():
        import time, sqlite3
        from pathlib import Path
        for conc in CONCORRENTES:
            posts24, curtidas24 = buscar_posts_e_curtidas_24meses(conc["username"])
            salvar_curtidas({"username": conc["username"], "nome": conc["nome"], "total_curtidas": curtidas24})
            db = Path(__file__).parent / "esperanca.db"
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute(
                "UPDATE concorrentes SET posts=? WHERE username=? AND id=(SELECT MAX(id) FROM concorrentes WHERE username=?)",
                (posts24, conc["username"], conc["username"])
            )
            conn.commit()
            conn.close()
            time.sleep(15)
    threading.Thread(target=coletar, daemon=True).start()
    return jsonify({"ok": True, "msg": "Coleta iniciada em background"})

@app.route("/api/precos", methods=["GET"])
def api_get_precos():
    import sqlite3
    db = Path(__file__).parent / "esperanca.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM precos_pizzarias")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/api/precos", methods=["POST"])
def api_save_precos():
    import sqlite3
    from datetime import datetime
    db = Path(__file__).parent / "esperanca.db"
    dados = request.json
    conn = sqlite3.connect(db)
    c = conn.cursor()
    for p in dados:
        c.execute("""INSERT INTO precos_pizzarias (username,nome,mussarela,calabresa,obs,atualizado_em)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(username) DO UPDATE SET
            nome=excluded.nome, mussarela=excluded.mussarela,
            calabresa=excluded.calabresa, obs=excluded.obs,
            atualizado_em=excluded.atualizado_em""",
            (p["username"], p["nome"], p.get("mussarela"), p.get("calabresa"),
             p.get("obs", ""), datetime.now().strftime("%d/%m %H:%M")))
    conn.commit()
    conn.close()

@app.route("/api/concorrentes/historico")
def api_historico():
    from src.monitor_concorrentes import listar_historico_mensal
    return jsonify(listar_historico_mensal())

@app.route("/api/concorrentes/historico/coletar", methods=["POST"])
def api_coletar_historico():
    import threading
    from src.monitor_concorrentes import buscar_historico_mensal, salvar_historico, CONCORRENTES
    def coletar():
        import time
        for c in CONCORRENTES:
            hist = buscar_historico_mensal(c["username"])
            salvar_historico(c["nome"], c["username"], hist)
            time.sleep(3)
    threading.Thread(target=coletar, daemon=True).start()
    return jsonify({"ok": True, "msg": "Coleta iniciada!"})

@app.route("/api/concorrentes/seguidores-historico")
def api_seguidores_historico():
    import sqlite3
    db = Path(__file__).parent / "esperanca.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT nome, seguidores, coletado_em FROM concorrentes ORDER BY coletado_em")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)


# =============================================================================
# ROTAS iFood — NOVAS
# =============================================================================

@app.route("/ifood")
def ifood():
    """Painel iFood — mesmo estilo do concorrentes.html."""
    return render_template("ifood.html")

@app.route("/api/ifood/concorrentes")
def api_ifood_concorrentes():
    """Snapshot mais recente de cada concorrente no iFood."""
    return jsonify(listar_ifood_atual())

@app.route("/api/ifood/concorrentes/coletar", methods=["POST"])
def api_ifood_coletar():
    """Dispara coleta de todos os concorrentes em background."""
    import threading
    dados = request.json or {}
    cidade = dados.get("cidade", "sao-bernardo-do-campo-sp")

    def coletar():
        coletar_todos_concorrentes(cidade)

    threading.Thread(target=coletar, daemon=True).start()
    return jsonify({
        "ok": True,
        "msg": f"Coleta iniciada para {len(RESTAURANTES_IFOOD)} restaurantes. Aguarde ~2 min e clique em Atualizar."
    })

@app.route("/api/ifood/historico")
def api_ifood_historico():
    """Histórico de rating e taxa ao longo do tempo."""
    return jsonify(listar_ifood_historico())

@app.route("/api/ifood/categoria", methods=["POST"])
def api_ifood_categoria():
    """
    Coleta restaurantes por categoria e cidade.
    Body: { "categoria": "pizza", "cidade": "sao-bernardo-do-campo-sp", "max_itens": 15 }
    """
    import threading
    dados = request.json or {}
    categoria = dados.get("categoria", "pizza")
    cidade    = dados.get("cidade", "sao-bernardo-do-campo-sp")
    max_itens = int(dados.get("max_itens", 15))

    def coletar():
        itens = coletar_por_categoria(categoria, cidade, max_itens)
        salvar_categoria(itens, categoria, cidade)

    threading.Thread(target=coletar, daemon=True).start()
    return jsonify({"ok": True, "msg": f"Buscando '{categoria}' em '{cidade}'..."})

@app.route("/api/ifood/categoria/<categoria>")
def api_ifood_categoria_dados(categoria):
    """Retorna dados da última coleta de uma categoria."""
    return jsonify(listar_categoria_atual(categoria))
# =============================================================================
# Cole estas rotas no app.py, antes do if __name__ == "__main__"
# =============================================================================

@app.route("/api/ifood/manual")
def api_ifood_manual():
    """Retorna dados manuais (taxa, tempo, preço pizza)."""
    import sqlite3
    db = Path(__file__).parent / "esperanca.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM ifood_manual ORDER BY nome")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/ifood/manual", methods=["POST"])
def api_ifood_salvar_manual():
    """Salva dados manuais (taxa, tempo, preço pizza)."""
    import sqlite3
    from datetime import datetime
    db = Path(__file__).parent / "esperanca.db"
    dados = request.json or []
    conn = sqlite3.connect(db)
    c = conn.cursor()
    agora = datetime.now().strftime("%d/%m %H:%M")
    for item in dados:
        c.execute("""
            INSERT INTO ifood_manual (uuid, nome, taxa_entrega, taxa_gratis, tempo_min, tempo_max, preco_pizza_8, atualizado_em)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(uuid) DO UPDATE SET
                taxa_entrega=excluded.taxa_entrega,
                taxa_gratis=excluded.taxa_gratis,
                tempo_min=excluded.tempo_min,
                tempo_max=excluded.tempo_max,
                preco_pizza_8=excluded.preco_pizza_8,
                atualizado_em=excluded.atualizado_em
        """, (
            item.get("uuid"), item.get("nome"),
            item.get("taxa_entrega"), 1 if item.get("taxa_gratis") else 0,
            item.get("tempo_min"), item.get("tempo_max"),
            item.get("preco_pizza_8"), agora,
        ))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "msg": "Dados salvos!"})


@app.route("/api/ifood/completo")
def api_ifood_completo():
    """
    Combina dados automáticos (rating via API) com dados manuais (taxa, tempo, preço).
    Este é o endpoint principal que o painel ifood.html usa.
    """
    import sqlite3
    db = Path(__file__).parent / "esperanca.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Rating automático (último snapshot de cada restaurante)
    c.execute("""
        SELECT * FROM ifood_restaurantes
        WHERE id IN (SELECT MAX(id) FROM ifood_restaurantes GROUP BY uuid)
    """)
    automaticos = {r["uuid"]: dict(r) for r in c.fetchall()}

    # Dados manuais
    c.execute("SELECT * FROM ifood_manual")
    manuais = {r["uuid"]: dict(r) for r in c.fetchall()}

    conn.close()

    # Combina os dois
    RESTAURANTES = [
        {"nome": "A EsperancA",     "uuid": "0417766b-1fd7-4fc2-aa00-b9f8a1c19199", "nos": True},
        {"nome": "1900 Pizzeria",   "uuid": "b779bdec-2108-4ed4-93ad-24bb5a73c714", "nos": False},
        {"nome": "Cezanne",         "uuid": "d14fc179-a92a-48d8-b0e0-bad9002d6e41", "nos": False},
        {"nome": "SalaVip",         "uuid": "8847d86f-7cec-4407-8b57-14dd12427bf6", "nos": False},
        {"nome": "Forno e Orégano", "uuid": "8d3ffb5a-337e-45b7-baec-d46897e3c381", "nos": False},
        {"nome": "Veridiana",       "uuid": "65f84e1b-90ec-4753-8cb0-a6330539cc38", "nos": False},
    ]

    resultado = []
    for rest in RESTAURANTES:
        uuid = rest["uuid"]
        auto = automaticos.get(uuid, {})
        manual = manuais.get(uuid, {})
        resultado.append({
            "uuid": uuid,
            "nome": rest["nome"],
            "nos": rest["nos"],
            # Automático
            "rating": auto.get("rating"),
            "total_avaliacoes": auto.get("total_avaliacoes"),
            "categoria": auto.get("categoria") or "Pizza",
            "pedido_minimo": auto.get("pedido_minimo") or manual.get("pedido_minimo"),
            "aberto": _esta_aberto(),
            "coletado_em": auto.get("coletado_em"),
            # Manual
            "taxa_entrega": manual.get("taxa_entrega"),
            "taxa_gratis": bool(manual.get("taxa_gratis")),
            "tempo_min": manual.get("tempo_min"),
            "tempo_max": manual.get("tempo_max"),
            "preco_pizza_8": manual.get("preco_pizza_8"),
            "atualizado_em": manual.get("atualizado_em"),
        })

    return jsonify(resultado)

# =============================================================================
if __name__ == "__main__":
    app.run(debug=True)
# ── Rota iFood para Render (sem restrição de IP) ──────────────────────────────
@app.route("/api/ifood/coletar-render")
def api_ifood_coletar_render():
    """
    Rota que roda no Render (sem bloqueio de IP).
    Busca dados do iFood via GraphQL e retorna JSON.
    O PythonAnywhere chama esta rota e salva no banco local.
    """
    import httpx, json as json_lib

    RESTAURANTES = [
        {"nome": "A EsperancA",     "uuid": "0417766b-1fd7-4fc2-aa00-b9f8a1c19199"},
        {"nome": "1900 Pizzeria",   "uuid": "b779bdec-2108-4ed4-93ad-24bb5a73c714"},
        {"nome": "Cezanne",         "uuid": "d14fc179-a92a-48d8-b0e0-bad9002d6e41"},
        {"nome": "SalaVip",         "uuid": "8847d86f-7cec-4407-8b57-14dd12427bf6"},
        {"nome": "Forno e Oregano", "uuid": "8d3ffb5a-337e-45b7-baec-d46897e3c381"},
        {"nome": "Babbo Giovanni",  "uuid": "f1908a34-f549-48bc-af3a-e5fa3ab41efc"},
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.ifood.com.br",
        "Referer": "https://www.ifood.com.br/",
        "content-type": "application/json",
        "accept": "application/json",
    }

    query = """query M($id: String!) {
      merchant(merchantId: $id, required: true) {
        name userRating available minimumOrderValue distance
        mainCategory { name }
        deliveryFee { value originalValue type }
        deliveryMethods { minTime maxTime mode value originalValue }
      }
    }"""

    resultados = []
    for rest in RESTAURANTES:
        try:
            r = httpx.post(
                "https://www.ifood.com.br/site-api/v1/merchant-info/graphql"
                "?latitude=-23.6012&longitude=-46.6358&channel=IFOOD",
                headers=headers,
                json={"query": query, "variables": {"id": rest["uuid"]}},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json().get("data", {}).get("merchant", {})
                delivery = next((d for d in (data.get("deliveryMethods") or []) if d.get("mode") == "DELIVERY"), {})
                fee = data.get("deliveryFee") or {}
                resultados.append({
                    "nome": rest["nome"],
                    "uuid": rest["uuid"],
                    "rating": data.get("userRating"),
                    "categoria": (data.get("mainCategory") or {}).get("name"),
                    "taxa_entrega": fee.get("value"),
                    "taxa_gratis": fee.get("value") == 0,
                    "tempo_min": delivery.get("minTime"),
                    "tempo_max": delivery.get("maxTime"),
                    "pedido_minimo": data.get("minimumOrderValue"),
                    "aberto": data.get("available", True),
                    "distancia_km": data.get("distance"),
                })
            import time; time.sleep(1)
        except Exception as e:
            resultados.append({"nome": rest["nome"], "uuid": rest["uuid"], "erro": str(e)})

    return jsonify(resultados)

@app.route("/api/ifood/debug")
def api_ifood_debug():
    import httpx
    uuid = '0417766b-1fd7-4fc2-aa00-b9f8a1c19199'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.ifood.com.br",
        "Referer": "https://www.ifood.com.br/",
        "content-type": "application/json",
        "accept": "application/json",
    }
    query = "query M($id: String!) { merchant(merchantId: $id, required: true) { name userRating deliveryFee { value } deliveryMethods { minTime maxTime mode } minimumOrderValue } }"
    try:
        r = httpx.post(
            "https://www.ifood.com.br/site-api/v1/merchant-info/graphql?latitude=-23.6012&longitude=-46.6358&channel=IFOOD",
            headers=headers,
            json={"query": query, "variables": {"id": uuid}},
            timeout=20,
        )
        return jsonify({"status": r.status_code, "body": r.text[:500]})
    except Exception as e:
        return jsonify({"erro": str(e)})

def _esta_aberto():
    """Verifica se as pizzarias estão abertas agora (seg-sab 18h-23h30)."""
    try:
        from datetime import datetime
        import pytz
        sp = pytz.timezone('America/Sao_Paulo')
        agora = datetime.now(sp)
        dia = agora.weekday()  # 0=seg, 6=dom
        hora = agora.hour + agora.minute / 60
        if dia == 6:  # domingo fechado
            return False
        if dia in (4, 5):  # sex e sab até 23h30
            return 18 <= hora < 23.5
        return 18 <= hora < 23  # seg-qui até 23h
    except Exception:
        return False
