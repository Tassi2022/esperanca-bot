from flask import Flask, render_template, jsonify, request
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from database import listar_oportunidades, marcar_respondida, stats, listar_datas
from src.monitor_concorrentes import listar_concorrentes_atual, coletar_concorrentes, buscar_perfil, buscar_user_id, listar_curtidas_concorrentes, salvar_curtidas, listar_curtidas_atual, buscar_posts_perfil, buscar_posts_e_curtidas_24meses
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/pizzarias")
def api_pizzarias():
    import sqlite3
    from pathlib import Path
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
            c.execute("UPDATE concorrentes SET posts=? WHERE username=? AND id=(SELECT MAX(id) FROM concorrentes WHERE username=?)", (posts24, conc["username"], conc["username"]))
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
             p.get("obs",""), datetime.now().strftime("%d/%m %H:%M")))
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
    from pathlib import Path
    db = Path(__file__).parent / "esperanca.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT nome, seguidores, coletado_em FROM concorrentes ORDER BY coletado_em")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

if __name__ == "__main__":
    app.run(debug=True)