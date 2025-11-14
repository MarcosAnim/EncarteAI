const { Client } = require('pg');

// Configuração da conexão
const client = new Client({
  host: 'db',       // endereço do servidor do banco
  port: 5432,              // porta padrão do Postgres
  user: 'user',     // usuário do banco
  password: 'password',   // senha
  database: 'layout_requests_db'// nome do banco
});

// Conectando e executando uma query
async function conectar() {
  try {
    await client.connect();
    console.log('Conectado ao PostgreSQL!');

    const res = await client.query('SELECT NOW()');
    console.log('Hora atual do banco:', res.rows[0]);

  } catch (err) {
    console.error('Erro de conexão:', err);
  } finally {
    await client.end();
  }
}

conectar();
