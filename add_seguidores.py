html_section = """
  <!-- HISTORICO SEGUIDORES -->
  <div class="section-title">👥 Evolução de Seguidores</div>
  <div class="box-full" style="margin-bottom:20px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <div>
        <div class="chart-label">Seguidores ao longo do tempo</div>
        <div class="chart-sub">Coletado semanalmente — quanto mais coletas, mais completo o histórico</div>
      </div>
      <button onclick="coletarSeguidores()" class="btn-coletar" id="btn-seg-coletar" style="font-size:11px;padding:6px 12px">↻ Coletar Agora</button>
    </div>
    <canvas id="chart-seg-hist" height="120"></canvas>
  </div>
"""

js_section = """
// ===== HISTORICO SEGUIDORES =====
let cSegHist = null;

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
    setTimeout(()=>carregarSeguidoresHist(), 5000);
  }catch(e){ showToast("Erro ao coletar"); }
  setTimeout(()=>{ btn.textContent="↻ Coletar Agora"; btn.disabled=false; }, 3000);
}

function renderSeguidoresHist(rows){
  if(!rows.length) return;

  // Agrupa por pizzaria
  const pizzMap = {};
  rows.forEach(r => {
    if(!pizzMap[r.nome]) pizzMap[r.nome] = [];
    pizzMap[r.nome].push({data: r.coletado_em, seguidores: r.seguidores});
  });

  // Pega todas as datas unicas ordenadas
  const todasDatas = [...new Set(rows.map(r=>r.coletado_em))].sort();
  const labels = todasDatas;

  const cores = ["#2d6a2d","#c0392b","#8e44ad","#e67e22","#2980b9","#16a085"];
  const nomes = Object.keys(pizzMap);

  const datasets = nomes.map((nome, i) => {
    const dataMap = {};
    pizzMap[nome].forEach(p => dataMap[p.data] = p.seguidores);
    return {
      label: nome,
      data: todasDatas.map(d => dataMap[d] || null),
      borderColor: cores[i % cores.length],
      backgroundColor: cores[i % cores.length] + '22',
      borderWidth: 2,
      pointRadius: 4,
      tension: 0.3,
      spanGaps: true
    };
  });

  if(cSegHist) cSegHist.destroy();
  cSegHist = new Chart(document.getElementById("chart-seg-hist"), {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 10 }, boxWidth: 12 } },
        tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': ' + fmt(ctx.raw) + ' seg.' } }
      },
      scales: {
        x: { ticks: { maxRotation: 45, font: { size: 9 } } },
        y: { beginAtZero: false, ticks: { font: { size: 9 } } }
      }
    }
  });
}
"""

with open('/home/tassi/esperanca_bot/templates/concorrentes.html', 'r') as f:
    content = f.read()

# Adiciona secao HTML antes do historico mensal
content = content.replace(
    '  <!-- HISTORICO MENSAL -->',
    html_section + '\n  <!-- HISTORICO MENSAL -->', 1)

# Adiciona JS antes do carregar()
content = content.replace(
    '// ===== HISTORICO =====',
    js_section + '\n// ===== HISTORICO =====', 1)

# Adiciona chamada
content = content.replace(
    'carregarHistorico();',
    'carregarHistorico();\ncarregarSeguidoresHist();', 1)

with open('/home/tassi/esperanca_bot/templates/concorrentes.html', 'w') as f:
    f.write(content)

print('OK - tamanho:', len(content))
