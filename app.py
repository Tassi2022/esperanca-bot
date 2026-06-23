from flask import Flask, render_template, jsonify, request
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from database import listar_oportunidades, marcar_respondida, stats, listar_datas
from src.monitor_concorrentes import (
    listar_concorrentes_atual, coletar_concorrentes, buscar_perfil,
    buscar_user_id, listar_curtidas_concorrentes, salvar_curtidas,
    listar_curtidas_atual, buscar_posts_perfil, buscar_posts_e_curtidas_24meses
)

app = Flask(__name__)

# =============================================================================
# ROTAS — Dashboard e Instagram
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
    pizzaria_id = request.json.get("pizzaria_id", "esperanca_saude") if request.json else "esperanca_saude"
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
# ROTAS iFOOD
# Rating: coleta automática semanal (Tasks) via GraphQL — sem bloqueio
# Taxa/tempo/status: script local rodado no PC (coletar_ifood_local.py) — 2x/dia
# Preço pizza/desconto: cadastro manual (único bloqueio real do iFood)
# =============================================================================

def _esta_aberto_fallback():
    """Fallback por horário, usado só se ainda não tiver dado real do iFood."""
    try:
        from datetime import datetime
        import pytz
        sp = pytz.timezone('America/Sao_Paulo')
        agora = datetime.now(sp)
        dia = agora.weekday()
        hora = agora.hour + agora.minute / 60
        if dia == 6:
            return False
        if dia in (4, 5):
            return 18 <= hora < 23.5
        return 18 <= hora < 23
    except Exception:
        return False


def _get_db():
    import sqlite3
    db = Path(__file__).parent / "esperanca.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


RESTAURANTES_IFOOD = [
    {"nome": "A EsperancA",     "uuid": "0417766b-1fd7-4fc2-aa00-b9f8a1c19199", "nos": True},
    {"nome": "1900 Pizzeria",   "uuid": "b779bdec-2108-4ed4-93ad-24bb5a73c714", "nos": False},
    {"nome": "Cezanne",         "uuid": "d14fc179-a92a-48d8-b0e0-bad9002d6e41", "nos": False},
    {"nome": "SalaVip",         "uuid": "8847d86f-7cec-4407-8b57-14dd12427bf6", "nos": False},
    {"nome": "Forno e Orégano", "uuid": "8d3ffb5a-337e-45b7-baec-d46897e3c381", "nos": False},
    {"nome": "Veridiana",       "uuid": "65f84e1b-90ec-4753-8cb0-a6330539cc38", "nos": False},
]


@app.route("/ifood")
def ifood():
    return render_template("ifood.html")


@app.route("/api/ifood/completo")
def api_ifood_completo():
    """
    Combina:
      - rating (coleta automática semanal via Tasks, GraphQL)
      - taxa/tempo/status real (script local rodado no PC, 2x/dia)
      - preço pizza/desconto (cadastro manual)
    """
    conn = _get_db()
    c = conn.cursor()

    c.execute("""
        SELECT * FROM ifood_restaurantes
        WHERE id IN (SELECT MAX(id) FROM ifood_restaurantes GROUP BY uuid)
    """)
    automaticos = {r["uuid"]: dict(r) for r in c.fetchall()}

    c.execute("SELECT * FROM ifood_manual")
    manuais = {r["uuid"]: dict(r) for r in c.fetchall()}
    conn.close()

    resultado = []
    for rest in RESTAURANTES_IFOOD:
        uuid = rest["uuid"]
        auto   = automaticos.get(uuid, {})
        manual = manuais.get(uuid, {})

        # Status: usa o real do iFood (script local) se existir, senão calcula por horário
        aberto_real = manual.get("aberto_real")
        aberto = bool(aberto_real) if aberto_real is not None else _esta_aberto_fallback()

        resultado.append({
            "uuid":            uuid,
            "nome":            rest["nome"],
            "nos":             rest["nos"],
            "rating":          auto.get("rating"),
            "total_avaliacoes":auto.get("total_avaliacoes"),
            "categoria":       auto.get("categoria") or "Pizza",
            "pedido_minimo":   manual.get("pedido_minimo") or auto.get("pedido_minimo"),
            "aberto":          aberto,
            "coletado_em":     auto.get("coletado_em"),
            "taxa_entrega":    manual.get("taxa_entrega"),
            "taxa_gratis":     bool(manual.get("taxa_gratis")),
            "tempo_min":       manual.get("tempo_min"),
            "tempo_max":       manual.get("tempo_max"),
            "preco_pizza_8":   manual.get("preco_pizza_8"),
            "desconto_texto":  manual.get("desconto_texto"),
            "desconto_valor":  manual.get("desconto_valor"),
            "atualizado_em":   manual.get("atualizado_em"),
        })
    return jsonify(resultado)


@app.route("/api/ifood/manual")
def api_ifood_manual():
    conn = _get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM ifood_manual ORDER BY nome")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/ifood/manual", methods=["POST"])
def api_ifood_salvar_manual():
    """
    Recebe atualizações tanto do FORMULÁRIO WEB (só preco_pizza_8 e desconto)
    quanto do SCRIPT LOCAL (taxa, tempo, aberto_real, pedido_minimo).
    Nunca apaga um campo que não foi enviado — faz merge com o que já existe.
    """
    from datetime import datetime
    dados = request.json or []
    conn = _get_db()
    c = conn.cursor()
    agora = datetime.now().strftime("%d/%m %H:%M")

    for item in dados:
        uuid = item.get("uuid")

        c.execute("SELECT * FROM ifood_manual WHERE uuid = ?", (uuid,))
        atual = c.fetchone()
        atual = dict(atual) if atual else {}

        def manter_se_vazio(novo, campo):
            return novo if novo is not None else atual.get(campo)

        taxa_entrega   = manter_se_vazio(item.get("taxa_entrega"), "taxa_entrega")
        taxa_gratis    = item.get("taxa_gratis") if item.get("taxa_gratis") is not None else atual.get("taxa_gratis", 0)
        tempo_min      = manter_se_vazio(item.get("tempo_min"), "tempo_min")
        tempo_max      = manter_se_vazio(item.get("tempo_max"), "tempo_max")
        preco_pizza_8  = manter_se_vazio(item.get("preco_pizza_8"), "preco_pizza_8")
        desconto_texto = manter_se_vazio(item.get("desconto_texto"), "desconto_texto")
        desconto_valor = manter_se_vazio(item.get("desconto_valor"), "desconto_valor")
        pedido_minimo  = manter_se_vazio(item.get("pedido_minimo"), "pedido_minimo")
        aberto_real    = item.get("aberto_real")
        if aberto_real is None:
            aberto_real = atual.get("aberto_real")

        c.execute("""
            INSERT INTO ifood_manual
                (uuid, nome, taxa_entrega, taxa_gratis, tempo_min, tempo_max,
                 preco_pizza_8, desconto_texto, desconto_valor, atualizado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(uuid) DO UPDATE SET
                taxa_entrega=excluded.taxa_entrega,
                taxa_gratis=excluded.taxa_gratis,
                tempo_min=excluded.tempo_min,
                tempo_max=excluded.tempo_max,
                preco_pizza_8=excluded.preco_pizza_8,
                desconto_texto=excluded.desconto_texto,
                desconto_valor=excluded.desconto_valor,
                atualizado_em=excluded.atualizado_em
        """, (
            uuid, item.get("nome"),
            taxa_entrega, 1 if taxa_gratis else 0,
            tempo_min, tempo_max,
            preco_pizza_8, desconto_texto, desconto_valor,
            agora,
        ))

        try:
            c.execute(
                "UPDATE ifood_manual SET aberto_real = ?, pedido_minimo = ? WHERE uuid = ?",
                (1 if aberto_real else (0 if aberto_real is not None else None), pedido_minimo, uuid)
            )
        except Exception:
            pass

    conn.commit()
    conn.close()
    return jsonify({"ok": True, "msg": "Dados salvos com sucesso!"})


@app.route("/api/ifood/concorrentes")
def api_ifood_concorrentes():
    return api_ifood_completo()


@app.route("/api/ifood/concorrentes/coletar", methods=["POST"])
def api_ifood_coletar():
    """Coleta o RATING (único dado seguro de coletar do servidor, sem bloqueio)."""
    import threading
    def coletar():
        from src.monitor_ifood import coletar_todos_concorrentes, init_ifood_db
        init_ifood_db()
        coletar_todos_concorrentes()
    threading.Thread(target=coletar, daemon=True).start()
    return jsonify({"ok": True, "msg": f"Coleta de rating iniciada para {len(RESTAURANTES_IFOOD)} restaurantes."})


@app.route("/api/ifood/historico")
def api_ifood_historico():
    from src.monitor_ifood import listar_ifood_historico
    return jsonify(listar_ifood_historico())


# =============================================================================
if __name__ == "__main__":
    app.run(debug=True)