"""
src/groq_ifood.py
Usa a API Groq (já configurada no projeto) para extrair dados do iFood
que o scraping direto não consegue (taxa de entrega, tempo, preço de pizza).

Estratégia:
  1. Busca o HTML público da página do restaurante no iFood via httpx
  2. Envia o texto limpo para o Groq extrair os dados estruturados
  3. Retorna JSON com taxa, tempo e preço da pizza 8 pedaços
"""

import json
import logging
import os
import re
import time

import httpx
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = "llama-3.1-8b-instant"

HEADERS_BROWSER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# ---------------------------------------------------------------------------
# 1. Busca HTML da página do restaurante
# ---------------------------------------------------------------------------

def _buscar_html_ifood(uuid: str, slug: str) -> str:
    """
    Tenta buscar o HTML da página do restaurante no iFood.
    Retorna texto limpo (sem tags) para enviar ao Groq.
    """
    url = f"https://www.ifood.com.br/delivery/{slug}"
    try:
        r = httpx.get(url, headers=HEADERS_BROWSER, timeout=20, follow_redirects=True)
        if r.status_code == 200:
            # Remove tags HTML, mantém só texto
            texto = re.sub(r"<script[^>]*>.*?</script>", " ", r.text, flags=re.S)
            texto = re.sub(r"<style[^>]*>.*?</style>", " ", texto, flags=re.S)
            texto = re.sub(r"<[^>]+>", " ", texto)
            texto = re.sub(r"\s+", " ", texto).strip()
            # Limita tamanho para não estourar contexto do Groq
            return texto[:4000]
        logger.warning(f"iFood HTML: status {r.status_code} para {url}")
    except Exception as e:
        logger.warning(f"Erro ao buscar HTML do iFood: {e}")

    # Fallback: retorna string vazia (Groq vai inferir com os dados disponíveis)
    return ""


# ---------------------------------------------------------------------------
# 2. Chama Groq para extrair dados estruturados
# ---------------------------------------------------------------------------

def _chamar_groq(prompt: str) -> dict:
    """Chama a API Groq no mesmo padrão do gerador_resposta.py."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": "Bearer " + GROQ_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,      # baixo — queremos dados precisos, não criatividade
        "max_tokens": 300,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        texto = r.json()["choices"][0]["message"]["content"].strip()
        # Remove possíveis blocos markdown ```json ... ```
        texto = re.sub(r"```json|```", "", texto).strip()
        return json.loads(texto)
    except json.JSONDecodeError:
        logger.warning(f"Groq retornou texto não-JSON: {texto}")
        return {}
    except Exception as e:
        logger.error(f"Erro Groq: {e}")
        return {}


# ---------------------------------------------------------------------------
# 3. Extração principal
# ---------------------------------------------------------------------------

def extrair_dados_ifood(nome: str, uuid: str, slug: str) -> dict:
    """
    Extrai taxa de entrega, tempo e preço de pizza 8 pedaços
    de um restaurante no iFood usando Groq.

    Retorna dict com:
        taxa_entrega    (float ou None)
        taxa_gratis     (bool)
        tempo_min       (int ou None)
        tempo_max       (int ou None)
        preco_pizza_8   (float ou None)  ← preço pizza 8 pedaços/fatias
        pedido_minimo   (float ou None)
        fonte           (str) 'html' ou 'inferido'
    """
    logger.info(f"Groq extraindo dados de: {nome}")

    html_texto = _buscar_html_ifood(uuid, slug)

    if html_texto:
        prompt = f"""
Você é um extrator de dados de delivery. Analise o texto abaixo da página do restaurante "{nome}" no iFood e extraia as informações solicitadas.

TEXTO DA PÁGINA:
{html_texto}

Extraia e retorne APENAS um JSON válido com estes campos (use null se não encontrar):
{{
  "taxa_entrega": <número em reais, ex: 5.99, ou 0 se grátis>,
  "taxa_gratis": <true ou false>,
  "tempo_min": <número inteiro em minutos, ex: 30>,
  "tempo_max": <número inteiro em minutos, ex: 45>,
  "preco_pizza_8": <preço da pizza de 8 pedaços/fatias em reais, ex: 89.90>,
  "pedido_minimo": <valor mínimo do pedido em reais, ex: 60.0>,
  "fonte": "html"
}}

Retorne SOMENTE o JSON, sem explicações.
"""
    else:
        # Sem HTML — pede ao Groq para inferir com base no nome/categoria
        prompt = f"""
Você é um especialista em delivery de pizzas em São Paulo.
Para o restaurante "{nome}" (pizzaria em São Paulo - Saúde/Vila Mariana),
estime os valores típicos e retorne APENAS um JSON:
{{
  "taxa_entrega": null,
  "taxa_gratis": false,
  "tempo_min": null,
  "tempo_max": null,
  "preco_pizza_8": null,
  "pedido_minimo": null,
  "fonte": "sem_dados"
}}

Retorne SOMENTE o JSON, sem explicações.
"""

    dados = _chamar_groq(prompt)

    # Normaliza os valores
    resultado = {
        "taxa_entrega":  _to_float(dados.get("taxa_entrega")),
        "taxa_gratis":   bool(dados.get("taxa_gratis", False)),
        "tempo_min":     _to_int(dados.get("tempo_min")),
        "tempo_max":     _to_int(dados.get("tempo_max")),
        "preco_pizza_8": _to_float(dados.get("preco_pizza_8")),
        "pedido_minimo": _to_float(dados.get("pedido_minimo")),
        "fonte":         dados.get("fonte", "desconhecido"),
    }

    if resultado["taxa_gratis"]:
        resultado["taxa_entrega"] = 0.0

    logger.info(
        f"✅ {nome} | taxa: {resultado['taxa_entrega']} | "
        f"tempo: {resultado['tempo_min']}-{resultado['tempo_max']}min | "
        f"pizza 8: R${resultado['preco_pizza_8']} | fonte: {resultado['fonte']}"
    )
    return resultado


def _to_float(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def _to_int(val) -> int | None:
    try:
        return int(val) if val is not None else None
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# 4. Coleta em lote para todos os concorrentes
# ---------------------------------------------------------------------------

def enriquecer_concorrentes(restaurantes: list) -> list:
    """
    Recebe a lista de RESTAURANTES_IFOOD e enriquece cada um
    com taxa, tempo e preço de pizza via Groq.

    restaurantes = [
        {"nome": "A EsperancA", "uuid": "...", "slug": "sao-paulo-sp/pizzaria-..."},
        ...
    ]
    """
    resultados = []
    for rest in restaurantes:
        try:
            dados = extrair_dados_ifood(
                nome=rest["nome"],
                uuid=rest["uuid"],
                slug=rest.get("slug", ""),
            )
            dados["nome"] = rest["nome"]
            dados["uuid"] = rest["uuid"]
            resultados.append(dados)
        except Exception as e:
            logger.error(f"Erro ao enriquecer {rest['nome']}: {e}")

        time.sleep(2)   # delay entre chamadas Groq

    return resultados


# ---------------------------------------------------------------------------
# Teste direto no terminal
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Testa com a A EsperancA
    dados = extrair_dados_ifood(
        nome="A EsperancA",
        uuid="0417766b-1fd7-4fc2-aa00-b9f8a1c19199",
        slug="sao-paulo-sp/pizzaria-a-esperanca---saude-bosque-da-saude/0417766b-1fd7-4fc2-aa00-b9f8a1c19199",
    )
    print("\nResultado:")
    print(json.dumps(dados, indent=2, ensure_ascii=False))
