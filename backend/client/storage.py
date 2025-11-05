import os
import psycopg2
from uuid import UUID

class LayoutRequestDB:
    """
    Gerencia o armazenamento e recuperação de objetos LayoutRequest
    usando um banco de dados PostgreSQL.
    """
    def __init__(self):
        # Credenciais de variáveis de ambiente
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_name = os.getenv("DB_NAME", "layout_requests_db")
        self.db_user = os.getenv("DB_USER", "user")
        self.db_pass = os.getenv("DB_PASSWORD", "password")
        self.db_port = os.getenv("DB_PORT", "5432")
        
        self.conn = None
        try:
            self.conn = psycopg2.connect(
                host=self.db_host,
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_pass,
                port=self.db_port
            )
            self._create_table()
            print(f"Conectado ao banco de dados PostgreSQL em: {self.db_host}")
        except psycopg2.OperationalError as e:
            print(f"ERRO: Não foi possível conectar ao PostgreSQL. Verifique se o banco de dados está rodando e se as credenciais estão corretas. Erro: {e}")
            raise

    def update(self, request:dict):
        """
        Atualiza uma requisição existente no banco de dados.
        Esta é uma função de conveniência que chama o método save().
        """
        print(f"Atualizando requisição {request['request_id']}...")
        self.save(request)
    
    def _create_table(self):
        """Cria a tabela de requisições se ela não existir."""
        
        with self.conn.cursor() as cursor:
            # Usamos o tipo UUID nativo do Postgres, que é muito mais eficiente
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS requests (
                    request_id UUID PRIMARY KEY,
                    prod_code INTEGER NOT NULL,
                    preco TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    preset TEXT NOT NULL,
                    client TEXT,
                    tipo TEXT,
                    selo TEXT,
                    last_modified TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
        self.conn.commit()

    def save(self, request:dict):
        print(request)
        """Salva ou uma requisição no banco de dados."""
        with self.conn.cursor() as cursor:
            # O equivalente do SQLite 'INSERT OR REPLACE' no Postgres é 'ON CONFLICT ... DO UPDATE'
            cursor.execute('''
                INSERT INTO requests (request_id, prod_code, preco, descricao, preset, client, tipo, selo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (request_id) DO UPDATE SET
                    prod_code = EXCLUDED.prod_code,
                    preco = EXCLUDED.preco,
                    descricao = EXCLUDED.descricao,
                    preset = EXCLUDED.preset,
                    client = EXCLUDED.client,
                    tipo = EXCLUDED.tipo,
                    selo = EXCLUDED.selo,
                    last_modified = NOW()
            ''', (
                request["request_id"],
                request.get("prod_code"),
                request.get("preco"),
                request.get("descricao"),
                request.get("preset"),
                request.get("client"),
                request.get("tipo"),
                request.get("selo")
            ))
        self.conn.commit()
        print(f"Requisição {request['request_id']} salva no banco de dados.")

    def load(self, request_id: str):
        """Carrega uma requisição do banco de dados pelo seu ID."""
        with self.conn.cursor() as cursor:
            
            cursor.execute(
                "SELECT request_id, prod_code, preco, descricao, preset, client, tipo, selo FROM requests WHERE request_id = %s",
                (request_id,)
            )
            row = cursor.fetchone()

        if row is None:
            raise FileNotFoundError(f"Nenhuma requisição encontrada com o ID: {request_id}")
        
        loaded_request = {
            "request_id": row[0],
            "prod_code": row[1],
            "preco": row[2],
            "descricao": row[3],
            "preset": row[4],
            "client": row[5],
            "tipo": row[6],
            "selo": row[7]
        }
        
        print(f"Requisição {loaded_request['request_id']} carregada do banco de dados.")
        return loaded_request

    def list_requests(self) -> list[UUID]:
        """Lista os IDs de todas as requisições salvas."""
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT request_id FROM requests")
            return [row[0] for row in cursor.fetchall()]

    def __del__(self):
        """Garante que a conexão com o banco de dados seja fechada."""
        if self.conn:
            self.conn.close()
            print("Conexão com PostgreSQL fechada.")

if __name__ == "__main__":
    
    # Teste ade funcionalidade do banco de dados
    db = LayoutRequestDB()
    payload = {
        "prod_code": "113395",
        "preco": "R$100,00",
        "descricao": "BATATA PRÉ FRITA CORTE FINA CONGELADO MCCAIN 2,5KG",
        "preset": "Aniversario",
        "request_id": "61417de6-5968-4269-9406-3db74dfd095d"
    }

    #db.save(request=payload)
    db.load("61417de6-5968-4269-9406-3db74dfd095d")
