
import pandas as pd
import requests
from lxml import html
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time

# --- Configurações ---
INPUT_FILE = r'C:\Users\Marcos\Desktop\Dellys NS\ofertas\products.xlsx'  # Nome do seu arquivo de entrada
OUTPUT_FILE = r'C:\Users\Marcos\Desktop\Dellys NS\ofertas\produtos_atualizados.xlsx' # Nome do arquivo de saída
PRODUCT_CODE_COLUMN = 'product_code' # Nome da coluna que contém os códigos dos produtos
BASE_URL = 'https://www.dellys.com.br/product/'

# XPaths para extrair as informações
XPATH_DESCRIPTION = '//*[@id="cc-product-details"]/div/div[1]'
XPATH_BRAND = '//*[@id="cc-product-details"]/div/div[2]/div/div/div[1]/a'
XPATH_CATEGORY = '//*[@id="CC-breadcrumb-details"]/div[1]/div/div/a[2]'

# Headers para simular um navegador e evitar bloqueios básicos
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Número máximo de requisições simultâneas. Ajuste conforme sua conexão e a robustez do site.
# Um valor entre 5 e 20 é um bom ponto de partida.
MAX_WORKERS = 20 

# --- Função para extrair dados de um único produto ---
def scrape_product_data(product_code):
    url = f"{BASE_URL}{product_code}"
    description = ''
    brand = ''
    category = ''

    try:
        response = requests.get(url, headers=HEADERS, timeout=10) # Timeout de 10 segundos
        response.raise_for_status() # Lança um erro para status de erro HTTP (4xx ou 5xx)

        tree = html.fromstring(response.content)

        # Extrair descrição
        desc_element = tree.xpath(XPATH_DESCRIPTION)
        if desc_element:
            description = desc_element[0].text_content().strip()

        # Extrair marca
        brand_element = tree.xpath(XPATH_BRAND)
        if brand_element:
            brand = brand_element[0].text_content().strip()

        # Extrair categoria
        category_element = tree.xpath(XPATH_CATEGORY)
        if category_element:
            category = category_element[0].text_content().strip()

    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar {url}: {e}")
        # Campos vazios conforme solicitado
    except Exception as e:
        print(f"Erro inesperado ao processar {url}: {e}")
        # Campos vazios
    
    return {
        PRODUCT_CODE_COLUMN: product_code,
        'description': description,
        'brand': brand,
        'category': category
    }

# --- Lógica Principal ---
if __name__ == "__main__":
    print(f"Lendo o arquivo Excel: {INPUT_FILE}...")
    try:
        df = pd.read_excel(INPUT_FILE)
    except FileNotFoundError:
        print(f"Erro: O arquivo '{INPUT_FILE}' não foi encontrado.")
        exit()
    except Exception as e:
        print(f"Erro ao ler o arquivo Excel: {e}")
        exit()

    if PRODUCT_CODE_COLUMN not in df.columns:
        print(f"Erro: A coluna '{PRODUCT_CODE_COLUMN}' não foi encontrada no arquivo Excel.")
        exit()

    product_codes = df[PRODUCT_CODE_COLUMN].tolist()
    total_products = len(product_codes)
    print(f"Total de {total_products} códigos de produto encontrados.")

    results = []

    # Usando ThreadPoolExecutor para requisições concorrentes
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Mapeia a função scrape_product_data para cada código de produto
        # as_completed permite processar os resultados assim que terminam,
        # e tqdm mostra o progresso.
        future_to_code = {executor.submit(scrape_product_data, code): code for code in product_codes}
        
        for future in tqdm(as_completed(future_to_code), total=total_products, desc="Raspando dados"):
            data = future.result()
            results.append(data)

    # Cria um DataFrame com os novos dados
    new_df = pd.DataFrame(results)

    # Mescla os novos dados com o DataFrame original
    # Usamos 'left merge' para garantir que todas as linhas originais sejam mantidas
    # e as novas colunas sejam adicionadas ou atualizadas.
    # O suffix é para evitar conflito de nomes de colunas, caso as colunas 'description', 'brand', 'category'
    # já existam no dataframe original. Se não existirem, os campos serão apenas adicionados.
    
    # Primeiro, remover as colunas antigas se existirem para evitar duplicidade no merge
    existing_cols_to_remove = ['description', 'brand', 'category']
    for col in existing_cols_to_remove:
        if col in df.columns:
            df = df.drop(columns=[col])

    # Agora faz o merge
    df_updated = pd.merge(df, new_df, on=PRODUCT_CODE_COLUMN, how='left')
    
    print(f"Salvando o arquivo atualizado em: {OUTPUT_FILE}...")
    try:
        df_updated.to_excel(OUTPUT_FILE, index=False)
        print("Processo concluído com sucesso!")
    except Exception as e:
        print(f"Erro ao salvar o arquivo Excel: {e}")