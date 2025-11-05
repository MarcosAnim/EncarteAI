# client/finder.py

import os
import psycopg2
from dataclasses import dataclass

@dataclass
class Product:
    """
    Representa os dados de um produto recuperado da tabela 'products'.
    """
    code: int
    name: str
    unit: str

class ProductFinder:
    """
    Realiza consultas por aproximação na tabela 'products'
    usando a extensão pg_trgm do PostgreSQL na coluna 'product_name'.
    """
    def __init__(self):
        # Carrega as credenciais do ambiente
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_name = os.getenv("DB_NAME", "layout_requests_db")
        self.db_user = os.getenv("DB_USER", "user")
        self.db_pass = os.getenv("DB_PASSWORD", "password")
        self.db_port = os.getenv("DB_PORT", "5432")
        self.conn = None

    def _get_connection(self):
        """Estabelece a conexão com o banco de dados se não existir."""
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(
                    host=self.db_host,
                    dbname=self.db_name,
                    user=self.db_user,
                    password=self.db_pass,
                    port=self.db_port
                )
            except psycopg2.OperationalError as e:
                print(f"ERRO: Não foi possível conectar ao PostgreSQL. Erro: {e}")
                raise
        return self.conn

    def find_similar(self, search_term: str, limit: int = 5, min_similarity: float = 0.2) -> list[tuple[Product, float]]:
        """
        Encontra produtos com nomes similares ao termo de busca.

        Args:
            search_term (str): O nome (ou parte do nome) do produto a ser buscado.
            limit (int): O número máximo de resultados a serem retornados.
            min_similarity (float): O limiar mínimo de similaridade (entre 0 e 1).

        Returns:
            list[tuple[Product, float]]: Uma lista de tuplas, onde cada tupla contém
                                         o objeto Product encontrado e sua pontuação
                                         de similaridade, ordenada da maior para a menor.
        """
        results = []
        conn = self._get_connection()
        
        query = """
            SELECT
                product_code, product_name, unit,
                similarity(product_name, %s) AS score
            FROM
                products
            WHERE
                product_name %% %s AND similarity(product_name, %s) >= %s
            ORDER BY
                score DESC
            LIMIT %s;
        """
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, (search_term, search_term, search_term, min_similarity, limit))
                
                for row in cursor.fetchall():
                    # Cria o objeto Product a partir dos dados do banco
                    product = Product(
                        code=row[0],
                        name=row[1],
                        unit=row[2]
                    )
                    similarity_score = row[3]
                    results.append((product, similarity_score))
                    
        except psycopg2.Error as e:
            print(f"ERRO durante a busca por similaridade de produtos: {e}")
            raise

        return results

    def close_connection(self):
        """Fecha a conexão com o banco de dados."""
        if self.conn and not self.conn.closed:
            self.conn.close()

    def __del__(self):
        """Garante que a conexão seja fechada quando o objeto for destruído."""
        self.close_connection()