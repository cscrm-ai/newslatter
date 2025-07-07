import os
import notion_client
from serpapi import GoogleSearch
from datetime import datetime

# --- CONFIGURAÇÃO ---
NOTION_KEY = os.getenv("NOTION_KEY")
# NOVO: ID da página principal onde as páginas diárias serão criadas.
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# Inicializa os clientes das APIs
notion = notion_client.Client(auth=NOTION_KEY)

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

def busca_noticias(termo_busca, engine="google"):
    """Realiza a busca de notícias usando a SerpApi."""
    print(f"Buscando em '{engine}' por: '{termo_busca}'...")
    params = {
        "q": termo_busca,
        "api_key": SERPAPI_API_KEY,
        "engine": engine,
    }
    if engine == "google":
        params.update({"tbm": "nws", "tbs": "qdr:d"})
    elif engine == "youtube":
        params.update({"sp": "CAI%3D"})

    try:
        results = GoogleSearch(params).get_dict()
        if "news_results" in results: return results.get("news_results", [])
        if "video_results" in results: return results.get("video_results", [])
        if "organic_results" in results: return results.get("organic_results", [])
        if "scholar_articles" in results: return results.get("scholar_articles", [])
    except Exception as e:
        print(f"Erro ao buscar notícias para '{termo_busca}': {e}")
    return []

def find_or_create_daily_page(parent_page_id):
    """Encontra ou cria uma página para o dia atual."""
    today_str = datetime.now().strftime("%d/%m/%Y")
    page_title = f"Notícias de IA - {today_str}"

    try:
        results = notion.search(query=page_title, filter={"property": "object", "value": "page"}).get("results")
        for page in results:
            if page.get("parent", {}).get("page_id") == parent_page_id and not page.get("archived"):
                print(f"Página do dia encontrada: {page['id']}")
                return page['id']
    except Exception as e:
        print(f"Erro ao buscar página: {e}")

    try:
        print(f"Criando nova página para o dia: {page_title}")
        new_page = notion.pages.create(
            parent={"page_id": parent_page_id},
            properties={"title": [{"text": {"content": page_title}}]},
            children=[
                {"type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": page_title}}]}},
                {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Resumo das notícias de Inteligência Artificial encontradas nas últimas 24 horas."}}]}},
                {"type": "divider", "divider": {}}
            ]
        )
        return new_page["id"]
    except Exception as e:
        print(f"Erro ao criar a página do dia: {e}")
        return None

def append_blocks_to_page(page_id, blocks):
    """Adiciona blocos de conteúdo a uma página."""
    if not page_id or not blocks: return
    try:
        notion.blocks.children.append(block_id=page_id, children=blocks)
        print(f"  -> Sucesso! {len(blocks)} blocos de conteúdo adicionados à página do dia.")
    except Exception as e:
        print(f"  -> ERRO ao adicionar blocos à página: {e}")

def get_fonte_from_engine(engine):
    if engine in ["google", "google_scholar"]: return "Portal"
    if engine == "twitter": return "X.com"
    return engine.capitalize()

# --- FLUXO PRINCIPAL ---
if __name__ == "__main__":
    print("Iniciando o assistente de pesquisa de notícias de IA...")
    
    daily_page_id = find_or_create_daily_page(NOTION_PAGE_ID)
    if not daily_page_id:
        print("Não foi possível encontrar ou criar a página do dia. Encerrando.")
        exit()

    all_news_blocks = []
    for categoria, config in CATEGORIAS.items():
        print(f"\n--- Processando Categoria: {categoria} ---")
        
        category_blocks = []
        for fonte_engine in config["fontes"]:
            resultados = busca_noticias(config["termos"], engine=fonte_engine)
            if not resultados:
                print(f"Nenhum resultado encontrado em '{fonte_engine}' para esta categoria.")
                continue

            for item in resultados[:2]:
                titulo = item.get("title")
                link = item.get("link")
                resumo = item.get("snippet", "Resumo não disponível.")
                if not all([titulo, link]): continue
                
                fonte_nome = get_fonte_from_engine(fonte_engine)
                
                news_text = [
                    {"type": "text", "text": {"content": f"{titulo}", "link": {"url": link}}},
                    {"type": "text", "text": {"content": f" – {fonte_nome}"}},
                    {"type": "text", "text": {"content": f"\n{resumo}"}, "annotations": {"italic": True}}
                ]
                category_blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": news_text}
                })

        if category_blocks:
            all_news_blocks.append({"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": categoria}}]}})
            all_news_blocks.extend(category_blocks)
            all_news_blocks.append({"type": "divider", "divider": {}})

    if all_news_blocks:
        append_blocks_to_page(daily_page_id, all_news_blocks)
    else:
        print("\nNenhuma notícia encontrada hoje.")

    print("\nProcesso finalizado.")