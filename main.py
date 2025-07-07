import os
import notion_client
from serpapi import GoogleSearch
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
# As chaves serão lidas das "Secrets" do GitHub, não diretamente aqui.
NOTION_KEY = os.getenv("NOTION_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# Inicializa os clientes das APIs
notion = notion_client.Client(auth=NOTION_KEY)
serpapi_client = GoogleSearch({"api_key": SERPAPI_API_KEY})

# --- DEFINIÇÃO DAS CATEGORIAS E BUSCAS ---
CATEGORIAS = {
    "Ferramentas de IA": {
        "termos": "\"ferramentas de IA\" OR \"lançamento IA\" OR \"plataforma de inteligência artificial\"",
        "fontes": ["google", "youtube"]
    },
    "Tendências para IA": {
        "termos": "\"tendências em IA\" OR \"futuro da IA\" OR \"IA generativa\"",
        "fontes": ["google", "reddit"]
    },
    "Atualizações sobre IA": {
        "termos": "\"atualização de modelo de IA\" OR \"OpenAI update\" OR \"Google AI update\"",
        "fontes": ["google", "twitter"]
    },
    "IA em Saúde e Medicina": {
        "termos": "\"IA na saúde\" OR \"inteligência artificial medicina\" OR \"diagnóstico por IA\"",
        "fontes": ["google_scholar", "google"]
    },
    "Inovações Médicas em IA": {
        "termos": "\"inovação médica IA\" OR \"IA descoberta de fármacos\" OR \"cirurgia robótica IA\"",
        "fontes": ["google_scholar", "youtube"]
    }
}

def busca_noticias(termo_busca, engine="google", dominio_site=None):
    """Realiza a busca de notícias usando a SerpApi."""
    print(f"Buscando em '{engine}' por: '{termo_busca}'...")
    params = {
        "q": termo_busca,
        "api_key": SERPAPI_API_KEY,
        "engine": engine,
    }

    # Filtro para notícias das últimas 24 horas
    if engine == "google":
        params.update({"tbm": "nws", "tbs": "qdr:d"}) # qdr:d = last 24 hours
    elif engine == "youtube":
        params.update({"sp": "CAI%3D"}) # sp: CAI%3D = Last 24 hours
    
    if dominio_site:
        params["q"] = f"{termo_busca} site:{dominio_site}"

    try:
        results = GoogleSearch(params).get_dict()
        
        if "news_results" in results:
            return results.get("news_results", [])
        if "video_results" in results:
            return results.get("video_results", [])
        if "organic_results" in results: # Para Twitter e Reddit
            return results.get("organic_results", [])
        if "scholar_articles" in results:
            return results.get("scholar_articles", [])

    except Exception as e:
        print(f"Erro ao buscar notícias para '{termo_busca}': {e}")
    return []


def adiciona_no_notion(titulo, resumo, link, categoria, fonte, data_publicacao_str):
    """Adiciona um item ao banco de dados do Notion."""
    try:
        # Tenta converter a data para o formato ISO 8601
        # A data da SerpApi pode vir em formatos variados
        try:
            data_obj = datetime.strptime(data_publicacao_str, "%Y-%m-%d")
            data_iso = data_obj.isoformat()
        except (ValueError, TypeError):
            # Se falhar, usa a data atual como fallback
            data_iso = datetime.now().isoformat()

        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Título": {"title": [{"text": {"content": titulo}}]},
                "Resumo": {"rich_text": [{"text": {"content": resumo}}]},
                "Link": {"url": link},
                "Categoria": {"select": {"name": categoria}},
                "Fonte": {"select": {"name": fonte.capitalize()}},
                "Data da Publicação": {"date": {"start": data_iso}}
            }
        )
        print(f"  -> Sucesso! Notícia '{titulo}' adicionada ao Notion.")
    except Exception as e:
        print(f"  -> ERRO ao adicionar '{titulo}' ao Notion: {e}")

def get_fonte_from_engine(engine):
    if engine == "google" or engine == "google_scholar":
        return "Portal"
    if engine == "twitter":
        return "X.com"
    return engine.capitalize()

# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    print("Iniciando o assistente de pesquisa de notícias de IA...")
    
    for categoria, config in CATEGORIAS.items():
        print(f"\n--- Processando Categoria: {categoria} ---")
        termos = config["termos"]
        
        for fonte_engine in config["fontes"]:
            resultados = busca_noticias(termos, engine=fonte_engine)
            
            if not resultados:
                print(f"Nenhum resultado encontrado em '{fonte_engine}' para esta categoria.")
                continue

            # Pega os 2 primeiros resultados para não exceder o limite da API
            for item in resultados[:2]:
                try:
                    titulo = item.get("title")
                    link = item.get("link")
                    resumo = item.get("snippet", "Resumo não disponível.")
                    data_publicacao = item.get("date", datetime.now().strftime("%Y-%m-%d"))

                    if not all([titulo, link]):
                        continue
                    
                    fonte_nome = get_fonte_from_engine(fonte_engine)
                    adiciona_no_notion(titulo, resumo, link, categoria, fonte_nome, data_publicacao)

                except KeyError as e:
                    print(f"Item ignorado por falta de chave: {e}")
                    continue
    
    print("\nProcesso finalizado.")
