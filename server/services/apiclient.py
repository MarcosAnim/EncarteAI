import requests
import re
from server.services.models import GeneratedLayout 

class LayoutAPIClient:
    """
    Um cliente para se comunicar com a API de geração de layouts.
    """
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.endpoint = f"{self.base_url}/gerar-layout"

    def _get_filename_from_headers(self, headers):
        # (Função auxiliar que já criamos antes)
        content_disposition = headers.get('Content-Disposition')
        if content_disposition:
            fname_match = re.search('filename="(.+)"', content_disposition)
            if fname_match:
                return fname_match.group(1)
        return None

    def generate_layout(self, request: dict):
        """
        Envia uma requisição para a API e retorna um objeto GeneratedLayout.

        Args:
            request (LayoutRequest): O objeto contendo os dados da requisição.

        Returns:
            GeneratedLayout: Um objeto com os dados binários da imagem e metadados.

        Raises:
            requests.exceptions.RequestException: Se houver um erro de conexão.
            ValueError: Se a API retornar um erro ou uma resposta inesperada.
        """
        print(f"Enviando requisição (ID: {request['request_id']}) para: {self.endpoint}")
        
        try:
            payload = {
                "prod_code": request['prod_code'],
                "preco": request['preco'],
                "descricao": request['descricao'],
                "preset": request['preset'],
                "client": request['client'],
                "tipo": request['tipo'],
                "selo": request['selo']
            }

            response = requests.post(self.endpoint, json=payload, timeout=60)
            response.raise_for_status() # Lança exceção para erros 4xx/5xx

            if 'image' not in response.headers.get('Content-Type', ''):
                raise ValueError("A resposta da API não é uma imagem.")

            # Extrai o nome do arquivo ou cria um padrão
            filename = self._get_filename_from_headers(response.headers)
            if not filename:
                filename = f"{request['prod_code']}.png"

            # Cria e retorna o objeto de resultado
            return GeneratedLayout(
                image_data=response.content,
                filename=filename,
                content_type=response.headers.get('Content-Type'), # type: ignore
                source_request=request
            )

        except requests.exceptions.HTTPError as http_err:
            print(f"Erro HTTP da API: {http_err}")
            raise ValueError(f"API retornou status {response.status_code}: {response.text}") from http_err
            
        except requests.exceptions.RequestException as req_err:
            print(f"Erro de conexão com a API: {req_err}")
            raise