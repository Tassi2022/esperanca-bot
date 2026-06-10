from database import salvar_oportunidade, listar_oportunidades

posts_teste = [
    {"id": "teste001", "texto": "Gente to com uma vontade de comer pizza que nao e brincadeira! Alguem indica uma boa no jardim da saude?", "hashtag_origem": "jardimdasaude", "link": "https://www.instagram.com/p/teste001/", "urgente": True},
    {"id": "teste002", "texto": "Sexta + chuva + fome = pizza. Onde pedir uma boa pizza delivery aqui na zona sul hoje?", "hashtag_origem": "pizzasp", "link": "https://www.instagram.com/p/teste002/", "urgente": True},
    {"id": "teste003", "texto": "Quero muito pizza agora. Alguem me convence a pedir kkkk", "hashtag_origem": "pizzasaopaulo", "link": "https://www.instagram.com/p/teste003/", "urgente": False},
    {"id": "teste004", "texto": "Final de semana em familia merece pizza boa! Alguem indica delivery no jardim da saude?", "hashtag_origem": "pizzadeliverysp", "link": "https://www.instagram.com/p/teste004/", "urgente": True},
]

respostas = [
    "Aqui e a Pizzaria A EsperancA -- desde 1957 no Jardim da Saude! Pede pelo iFood: https://ifoodbr.onelink.me/F4X4/AEsperancaPizzaria",
    "Desde 1957 em SP e 25 anos no Jardim da Saude, a A EsperancA e sua melhor escolha! iFood: https://ifoodbr.onelink.me/F4X4/AEsperancaPizzaria",
    "Pede sim! A A EsperancA entrega no Jardim da Saude ha mais de 25 anos. iFood: https://ifoodbr.onelink.me/F4X4/AEsperancaPizzaria",
    "Familia italiana desde 1957 -- a A EsperancA e a escolha certa! iFood: https://ifoodbr.onelink.me/F4X4/AEsperancaPizzaria",
]

for post, resp in zip(posts_teste, respostas):
    salvar_oportunidade(post, resp)

ops = listar_oportunidades()
print(f"Banco com {len(ops)} oportunidades!")