from server.services.apiclient import LayoutAPIClient # Cliente API
from server.services.storage import LayoutRequestDB # Banco de Dados
from server.services.product_db_consult import ProductFinder

if __name__ == "__main__":

    # --- INICIALIZAÇÃO ---
    api_client = LayoutAPIClient()
    storage = LayoutRequestDB()

    payload = {
        "prod_code": "113395",
        "preco": "R$100,00",
        "descricao": "BATATA PRÉ FRITA CORTE FINA CONGELADO MCCAIN 2,5KG",
        "preset": "Aniversario",
        "tipo": None,
        "selo": None,
        "client":"dellys",
        "request_id": "61417de6-5968-4269-9406-3db74dfd095d"
    }

    storage.save(payload) 
    #storage.load(payload['request_id'])
    #storage.update(payload)
        
    try:
        # Gerar imagem localmente apenas para debug
        print("\nGerando layout com os dados atualizados...")
        layout_atualizado = api_client.generate_layout(payload)
        layout_atualizado.filename = f"{payload['prod_code']}_atualizado.png"
        print(layout_atualizado) # O output será image_data: bytes filename: str content_type: str source_request: str 
        layout_atualizado.save(output_dir="layouts_recebidos")
    except Exception as e:
        print(f"Falha ao gerar o layout atualizado: {e}")
    
'''
if __name__ == "__main__":
      finder = ProductFinder()
try:
    resultados = finder.find_similar("carne suina", limit=10, min_similarity=0.25)
    for produto, score in resultados:
        print(produto.code, produto.name, produto.unit, f"score={score:.3f}")
finally:
    finder.close_connection()
'''
        