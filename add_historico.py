# Script para adicionar secao de historico no concorrentes.html
import re

html_section = """
  <!-- HISTORICO MENSAL -->
  <div class="section-title">📈 Histórico Mensal</div>
  <div class="box-full" style="margin-bottom:20px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <div>
        <div class="chart-label">Evolução por Mês</div>
        <div class="chart-sub">Curtidas e posts publicados nos últimos 24 meses</div>
      </div>
      <div style="display:flex;gap:6px">
        <button onclick="toggleHistorico('curtidas')" id="btn-curtidas" class="btn-toggle-hist ativo">❤️ Curtidas</button>
        <button onclick="toggleHistorico('posts')" id="btn-posts" class="btn-toggle-hist">📸 Posts</button>
        <button onclick="coletarHistorico()" class="btn-coletar" id="btn-hist-coletar" style="font-size:11px;padding:6px 12px">↻ Coletar</button>
      </div>
    </div>
    <canvas id="chart-historico" height="120"></canvas>
  </div>
"""

js_section = """
// ===== HISTORICO =====
let cHistorico = null;
let modoHistorico = 'curtidas';
let dadosHistorico = [];

async function carregarHistorico(){
  try{
    const rows = await fetch("/api/concorrentes/historico").then(r=>r.json());
    dadosHistorico = rows;
    renderHistorico();
  }catch(e){ console.log("Erro historico:", e); }
}

function toggleHistorico(modo){
  modoHistorico = modo;
  document.getElementById("btn-curtidas").classList.toggle("ativo", modo==="curtidas");
  document.getElementById("btn-posts").classList.toggle("ativo", modo==="posts");
  renderHistorico();
}

async function coletarHistorico(){
  const btn = document.getElementById("btn-hist-coletar");
  btn.textContent = "Coletando..."; btn.disabled = true;
  try{
    await fetch("/api/concorrentes/historico/coletar", {method:"POST"});
    showToast("Coleta iniciada! Aguarde ~15 min e atualize.");
  }catch(e){ showToast("Erro ao coletar"); }
  setTimeout(()=>{ btn.textContent="↻ Coletar"; btn.disabled=false; }, 3000);
}

function renderHistorico(){
  if(!dadosHistorico.length) return;

  // Agrupa por pizzaria
  const pizzMap = {};
  dadosHistorico.forEach(r => {
    if(!pizzMap[r.nome]) pizzMap[r.nome] = {};
    pizzMap[r.nome][r.ano_mes] = {curtidas: r.curtidas, posts: r.posts};
  });

  // Pega todos os meses unicos ordenados
  const todosAnosMeses = [...new Set(dadosHistorico.map(r=>r.ano_mes))].sort();

  // Filtra ultimos 24 meses
  const labels = todosAnosMeses.slice(-24).map(m => {
    const [ano, mes] = m.split('-');
    const meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
    return meses[parseInt(mes)-1] + '/' + ano.slice(2);
  });
  const chaves = todosAnosMeses.slice(-24);

  const cores = ["#2d6a2d","#c0392b","#8e44ad","#e67e22","#2980b9","#16a085"];
  const nomes = Object.keys(pizzMap);

  const datasets = nomes.map((nome, i) => ({
    label: nome,
    data: chaves.map(k => pizzMap[nome][k] ? pizzMap[nome][k][modoHistorico] : null),
    borderColor: cores[i % cores.length],
    backgroundColor: cores[i % cores.length] + '22',
    borderWidth: 2,
    pointRadius: 3,
    tension: 0.3,
    spanGaps: true
  }));

  if(cHistorico) cHistorico.destroy();
  cHistorico = new Chart(document.getElementById("chart-historico"), {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 10 }, boxWidth: 12 } },
        tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': ' + fmt(ctx.raw) } }
      },
      scales: {
        x: { ticks: { maxRotation: 45, font: { size: 9 } } },
        y: { beginAtZero: true, ticks: { font: { size: 9 } } }
      }
    }
  });
}
"""

css_section = """
.btn-toggle-hist{background:var(--creme);border:1px solid var(--borda);color:var(--texto-muted);padding:6px 12px;border-radius:16px;font-size:11px;cursor:pointer;font-family:"DM Sans",sans-serif}
.btn-toggle-hist.ativo{background:var(--verde);color:white;border-color:var(--verde)}
"""

with open('/home/tassi/esperanca_bot/templates/concorrentes.html', 'r') as f:
    content = f.read()

# Adiciona CSS antes do fechamento do style
content = content.replace('</style>', css_section + '</style>', 1)

# Adiciona secao HTML antes de "Posts com Mais Curtidas"  
content = content.replace('<div class="section-title">Posts com Mais Curtidas</div>', 
                           html_section + '\n  <div class="section-title">Posts com Mais Curtidas</div>', 1)

# Adiciona JS antes do carregar()
content = content.replace('carregar();\nrenderTabs();', 
                           js_section + '\ncarregar();\nrenderTabs();', 1)

# Adiciona chamada carregarHistorico
content = content.replace('carregarPrecos();', 'carregarPrecos();\ncarregarHistorico();', 1)

with open('/home/tassi/esperanca_bot/templates/concorrentes.html', 'w') as f:
    f.write(content)

print('OK - tamanho:', len(content))
