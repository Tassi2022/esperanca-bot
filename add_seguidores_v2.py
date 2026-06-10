html_section = """
  <!-- EVOLUCAO SEGUIDORES -->
  <div class="section-title">👥 Evolução de Seguidores</div>
  <div class="box-full" style="margin-bottom:20px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <div>
        <div class="chart-label">Comparativo de crescimento</div>
        <div class="chart-sub">Seguidores coletados em cada data — colete semanalmente para acompanhar a evolução</div>
      </div>
      <button onclick="coletarSeguidores()" class="btn-coletar" id="btn-seg-coletar" style="font-size:11px;padding:6px 12px">↻ Coletar Agora</button>
    </div>
    <div class="table-scroll">
      <table class="eng-table" id="seg-hist-table">
        <thead id="seg-hist-thead"></thead>
        <tbody id="seg-hist-tbody"></tbody>
      </table>
    </div>
  </div>
"""

js_section = """
// ===== EVOLUCAO SEGUIDORES =====
async function carregarSeguidoresHist(){
  try{
    const rows = await fetch("/api/concorrentes/seguidores-historico").then(r=>r.json());
    renderSeguidoresHist(rows);
  }catch(e){ console.log("Erro seg hist:", e); }
}

async function coletarSeguidores(){
  const btn = document.getElementById("btn-seg-coletar");
  btn.textContent = "Coletando..."; btn.disabled = true;
  try{
    await fetch("/api/concorrentes/coletar", {method:"POST"});
    showToast("Coleta iniciada! Aguarde e atualize.");
    setTimeout(()=>carregarSeguidoresHist(), 8000);
  }catch(e){ showToast("Erro ao coletar"); }
  setTimeout(()=>{ btn.textContent="Coletar Agora"; btn.disabled=false; }, 5000);
}

function renderSeguidoresHist(rows){
  if(!rows || !rows.length) return;

  // Agrupa por pizzaria e data
  const pizzMap = {};
  const datasSet = new Set();
  rows.forEach(r => {
    if(!pizzMap[r.nome]) pizzMap[r.nome] = {};
    const dataKey = r.coletado_em;
    datasSet.add(dataKey);
    pizzMap[r.nome][dataKey] = r.seguidores;
  });

  // Datas ordenadas
  const datas = [...datasSet].sort();

  // Header
  let headerHtml = '<tr><th>Pizzaria</th>';
  datas.forEach(d => { headerHtml += '<th>' + d + '</th>'; });
  if(datas.length > 1) headerHtml += '<th>Variacao Total</th>';
  headerHtml += '</tr>';
  document.getElementById("seg-hist-thead").innerHTML = headerHtml;

  // Rows
  const nomes = Object.keys(pizzMap).sort();
  const cores = {"A EsperancA":"var(--verde)","1900 Pizzeria":"#c0392b","Cezanne":"#8e44ad","SalaVip":"#e67e22","Forno e Oregano":"#2980b9","Babbo Giovanni":"#16a085"};

  let bodyHtml = '';
  nomes.forEach(nome => {
    const isNos = nome === 'A EsperancA';
    bodyHtml += '<tr class="' + (isNos?'nos-row':'') + '">';
    bodyHtml += '<td><strong>' + nome + '</strong>' + (isNos?' <span class="badge-nos">NOS</span>':'') + '</td>';

    const valores = datas.map(d => pizzMap[nome][d] || null);

    datas.forEach((d, i) => {
      const val = valores[i];
      let cell = val ? fmt(val) : '—';

      // Variacao entre datas consecutivas
      if(i > 0 && val && valores[i-1]) {
        const diff = val - valores[i-1];
        const sinal = diff > 0 ? '+' : '';
        const cor = diff > 0 ? 'color:#27ae60' : diff < 0 ? 'color:var(--vermelho)' : 'color:#999';
        cell += ' <span style="font-size:10px;' + cor + '">(' + sinal + fmt(diff) + ')</span>';
      }
      bodyHtml += '<td>' + cell + '</td>';
    });

    // Variacao total
    if(datas.length > 1) {
      const primeiro = valores.find(v => v !== null);
      const ultimo = [...valores].reverse().find(v => v !== null);
      if(primeiro && ultimo) {
        const diff = ultimo - primeiro;
        const sinal = diff > 0 ? '+' : '';
        const cor = diff > 0 ? 'color:#27ae60;font-weight:700' : diff < 0 ? 'color:var(--vermelho);font-weight:700' : 'color:#999';
        bodyHtml += '<td style="' + cor + '">' + sinal + fmt(diff) + '</td>';
      } else {
        bodyHtml += '<td>—</td>';
      }
    }

    bodyHtml += '</tr>';
  });
  document.getElementById("seg-hist-tbody").innerHTML = bodyHtml;
}
"""

with open('/home/tassi/esperanca_bot/templates/concorrentes.html', 'r') as f:
    content = f.read()

# Remove secao antiga de seguidores se existir
if '<!-- HISTORICO SEGUIDORES -->' in content:
    import re
    content = re.sub(r'\s*<!-- HISTORICO SEGUIDORES -->.*?</div>\n', '', content, flags=re.DOTALL)

# Remove JS antigo se existir
if '// ===== HISTORICO SEGUIDORES =====' in content:
    import re
    content = re.sub(r'// ===== HISTORICO SEGUIDORES =====.*?(?=// =====|\ncarregar)', '', content, flags=re.DOTALL)

# Remove chamada antiga
content = content.replace('\ncarregarSeguidoresHist();', '')

# Adiciona nova secao HTML antes do historico mensal
content = content.replace(
    '  <!-- HISTORICO MENSAL -->',
    html_section + '\n  <!-- HISTORICO MENSAL -->', 1)

# Adiciona novo JS antes do historico mensal
content = content.replace(
    '// ===== HISTORICO =====',
    js_section + '\n// ===== HISTORICO =====', 1)

# Adiciona chamada
content = content.replace(
    'carregarHistorico();',
    'carregarSeguidoresHist();\ncarregarHistorico();', 1)

with open('/home/tassi/esperanca_bot/templates/concorrentes.html', 'w') as f:
    f.write(content)

print('OK - tamanho:', len(content))
