// Função para buscar produtos similares usando o endpoint REST
async function findSimilarProducts(searchTerm, limit = 10, minSimilarity = 0.25) {
    try {
        // Construir a URL com os parâmetros de busca
        const params = new URLSearchParams({
            q: searchTerm,
            limit: limit,
            min_similarity: minSimilarity
        });

        // Fazer a requisição para o endpoint
        // Usar URL relativa para funcionar em diferentes ambientes
        const response = await fetch(`http://127.0.0.1:5000/produtos/buscar?${params}`, {
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.status === 'erro') {
            throw new Error(data.mensagem);
        }

        return data.results;
    } catch (error) {
        console.error('Erro ao buscar produtos:', error);
        throw error;
    }
}

// Exemplo de uso:

//const results = await findSimilarProducts('Carne Suina', 10, 0.25);
// Imprimir os resultados como no exemplo Python
//results.forEach(produto => {
//    console.log(
//        produto.code,
 //       produto.name,
//        produto.unit,
//        `score=${produto.score.toFixed(3)}`
//    );
//});

//results.forEach(item =>{console.log(item)})
// Exportar as funções para uso em outros arquivos
export {findSimilarProducts};