from apify_client import ApifyClient

TOKEN = "apify_api_IP6MOBXKU1FB41zfPqNnnYSobIokeH2ye8rP"
client = ApifyClient(TOKEN)

run_input = {
    "startUrls": [
        {"url": "https://www.ifood.com.br/delivery/sao-paulo-sp/pizzaria-a-esperanca---saude-bosque-da-saude/0417766b-1fd7-4fc2-aa00-b9f8a1c19199"}
    ],
    "maxCrawlPages": 1,
    "crawlerType": "playwright:chrome",
}

print("Iniciando run no Apify (pode levar 30-90s)...")
run = client.actor("apify/website-content-crawler").call(run_input=run_input)
print(f"Status: {run['status']}")

dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
print(f"Itens coletados: {len(dataset_items)}")

if dataset_items:
    item = dataset_items[0]
    text = item.get('text', '')
    print(f"Tamanho do texto: {len(text)} chars")
    print("--- Primeiros 1500 chars ---")
    print(text[:1500])
    if "Just a moment" in text or "Cloudflare" in text[:500]:
        print("\nBLOQUEADO PELO CLOUDFLARE")
    elif "esperança" in text.lower() or "Pizzaria" in text:
        print("\nPASSOU! Conseguiu acessar o conteudo real do iFood!")
else:
    print("Sem itens. Run completo:")
    print(run)
