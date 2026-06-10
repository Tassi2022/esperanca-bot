import os
from dotenv import load_dotenv
load_dotenv()

import requests
import logging
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"

def gerar_resposta(post, pizzaria_nome, pizzaria_historia, pizzaria_ifood, pizzaria_bairro, gemini_api_key=None):
    prompt = (
        f"Voce e o social media da {pizzaria_nome}. "
        f"Historia: {pizzaria_historia} "
        f"Link iFood: {pizzaria_ifood} "
        f"Bairro: {pizzaria_bairro} "
        f"Post do Instagram: '{post['texto']}' "
        f"Escreva UMA resposta curta (max 3 linhas), simpatica e natural para comentar nesse post. "
        f"Mencione um dado real da historia (1957, familia italiana, 25 anos no bairro). "
        f"Inclua o link do iFood no final. Use 1 emoji. Portugues informal. "
        f"Apenas a resposta, sem explicacoes."
    )
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": "Bearer " + GROQ_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0.8,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        data = resp.json()
        resposta = data["choices"][0]["message"]["content"].strip()
        logger.info(f"Resposta gerada para {post.get('shortcode','')}")
        return resposta
    except Exception as e:
        logger.error(f"Erro Groq: {e}")
        return f"Aqui e a {pizzaria_nome} -- desde 1957 em SP e 25 anos no {pizzaria_bairro}! Pede: {pizzaria_ifood}"
