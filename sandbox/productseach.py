# run_product_finder.py

from client.finder import ProductFinder
from client.models import LayoutRequest
from client.apiclient import LayoutAPIClient
# (Você pode precisar das outras classes para o fluxo completo)

if __name__ == "__main__":
    
    # 1. Crie uma instância do nosso buscador de produtos
    finder = ProductFinder()
    
    # 2. Simula a entrada do usuário
    entrada_do_usuario = "Azeite de oliva Extra virgem 200ml"
    
    print(f"\nBuscando por produtos similares a: '{entrada_do_usuario}'...")
    
    try:
        # 3. Encontra os produtos mais similares na tabela 'products'
        resultados_busca = finder.find_similar(entrada_do_usuario, limit=3)
        
        if not resultados_busca:
            print("Nenhum produto similar encontrado.")
        else:
            print(f"\nEncontrados {len(resultados_busca)} resultados mais próximos:")
            for produto, similaridade in resultados_busca:
                print("-" * 30)
                print(f"  Similaridade: {similaridade:.2%}")
                print(f"  Código: {produto.code}")
                print(f"  Nome: {produto.name}")
                print(f"  Unidade: {produto.unit}")

            # --- FLUXO COMPLETO ---
            print("\n--- Simulando a seleção do primeiro resultado para gerar um layout ---")
            
            # 4. Seleciona o resultado mais relevante (o primeiro da lista)
            produto_selecionado, _ = resultados_busca[0]

            # 5. Usa os dados do produto encontrado para criar um LayoutRequest
            req_para_api = LayoutRequest(
                prod_code=produto_selecionado.code,
                preco="R$99,99", # O preço viria de outra fonte
                descricao=produto_selecionado.name, # Usa o nome correto do DB
                preset="OfertaEspecial",
                tipo=produto_selecionado.unit # Usa a unidade correta do DB
            )

            print(f"\nCriando requisição para API com o produto '{req_para_api.descricao}'")

            # 6. Chama a API para gerar a imagem
            api_client = LayoutAPIClient()
            layout_final = api_client.generate_layout(req_para_api)
            layout_final.save("layouts_recebidos")

    except Exception as e:
        print(f"\nOcorreu um erro durante o processo: {e}")
    finally:
        finder.close_connection()