import {findSimilarProducts} from './productSearch.js';

document.addEventListener('DOMContentLoaded', () => {
        


        // side bar 
        const sidebar = document.querySelector('.sidebar');
        const toggleBtn = document.querySelector('.toggle-sidebar');

        toggleBtn.addEventListener('click', () => {
            if (sidebar.style.marginLeft === '-350px') {
                sidebar.style.marginLeft = '0';
                toggleBtn.style.left = '350px';
                toggleBtn.textContent = '◀';
            } else {
                sidebar.style.marginLeft = '-350px';
                toggleBtn.style.left = '0';
                toggleBtn.textContent = '▶';
            }
        });

        document.querySelectorAll('.toggle').forEach(toggle => {
            toggle.addEventListener('click', function () {
                this.classList.toggle('active');
            });
        });


        // Dropdown user config
        const btn = document.getElementById('config-btn');
        const menu = document.getElementById('config-menu');

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            menu.classList.toggle('show');
        });
        

        // Fecha o menu ao clicar fora
        document.addEventListener('click', () => {
            menu.classList.remove('show');
        });
        

        // Navegação nas paginas do menu lateral
        document.querySelectorAll(".menu-items li").forEach(item => {
            item.addEventListener('click', (event) => {
                const page = event.target.getAttribute('data-page');
                if (page) {
                    loadContent(event, page);
                }
            });
        });

        // carregar contudo dinamico

        async function loadContent(event, page) {
            const contentArea = document.querySelector("#content-area");

            try {
                // Faz uma checagem para garantir que o arquivo existe antes de trocar o src
                const response = await fetch(page);
                if (!response.ok) throw new Error("Página não encontrada");

                // Faz uma animação leve antes da troca
                contentArea.style.opacity = "0";

                setTimeout(() => {
                    // Atualiza a página exibida no iframe
                    contentArea.src = page;

                    // Anima novamente após um curto tempo
                    setTimeout(() => {
                        contentArea.style.opacity = "1";
                    }, 200);
                }, 200);

                // Atualiza visualmente o item ativo no menu lateral
                if (event && event.target && event.target.nodeType === 1) {
                    document.querySelectorAll(".menu-items li").forEach(li => li.classList.remove("active"));
                    event.target.classList.add("active");
                }

            } catch (error) {
                console.error("Erro ao carregar página:", error);

                // Caso a página não exista, exibe um aviso dentro do iframe (dinamicamente)
                const iframeDoc = contentArea.contentDocument || contentArea.contentWindow.document;
                iframeDoc.open();
                iframeDoc.write(`<p style="color:red; padding:20px;">Erro ao carregar o conteúdo de <strong>${page}</strong>.</p>`);
                iframeDoc.close();
            }
        }

        window.addEventListener("DOMContentLoaded", () => {
            // Chamada inicial (passando 'null' para o evento)
            loadContent(null, "static/components/maker.html"); 
        });


        // Interação com o searchbar e busca de produtos

        const usersearch = document.getElementById('searchInput');
        const searchbutton = document.querySelector('.product-input button');
        const searchResults = document.getElementById('searchResults');
        const productInput = document.querySelector('.product-input');

        function clearOldResults() {
            searchResults.innerHTML = '';
            searchResults.classList.remove('show', 'empty');
        }

        function showEmptyState() {
            searchResults.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🔍</div>
                    <div>Nenhum produto encontrado</div>
                </div>
            `;
            searchResults.classList.add('show', 'empty');
        }

        async function performSearch() {
            const query = usersearch.value.trim();
            
            if (!query) {
                clearOldResults();
                return;
            }

            // Adiciona estado de loading
            productInput.classList.add('loading');
            clearOldResults();

            try {
                const results = await findSimilarProducts(query, 10, 0.25);
                
                // Remove loading
                productInput.classList.remove('loading');

                if (results.length === 0) {
                    showEmptyState();
                    return;
                }

                // Adiciona badge com contagem
                const countBadge = document.createElement('div');
                countBadge.className = 'results-count';
                countBadge.textContent = `${results.length} resultado${results.length > 1 ? 's' : ''} encontrado${results.length > 1 ? 's' : ''}`;
                searchResults.appendChild(countBadge);

                // Adiciona resultados com delay escalonado para animação
                results.forEach((item, index) => {
                    const itemlist = document.createElement('li');
                    itemlist.className = 'product-db-response';
                    itemlist.id = item.code;
                    itemlist.innerHTML = `
                        <span>${item.name}</span>
                        <small style="margin-left: auto; color: #6a6a6a; font-size: 12px;">${item.unit}</small>
                    `;
                    itemlist.style.animationDelay = `${index * 0.05}s`;
                    searchResults.appendChild(itemlist);
                });

                searchResults.classList.add('show');
            } catch (error) {
                productInput.classList.remove('loading');
                console.error('Erro na busca:', error);
                searchResults.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">⚠️</div>
                        <div>Erro ao buscar produtos</div>
                    </div>
                `;
                searchResults.classList.add('show', 'empty');
            }
        }

        // Event listener para botão
        searchbutton.addEventListener('click', performSearch);

        // Event listener para Enter
        usersearch.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                performSearch();
            }
        });

        // Busca em tempo real (opcional - remova se não quiser)
        let debounceTimer;
        usersearch.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                if (e.target.value.length >= 3) {
                    performSearch();
                } else if (e.target.value.length === 0) {
                    clearOldResults();
                }
            }, 300);
        });

        // Selecionar produto da lista
        searchResults.addEventListener('click', async (e) => {
            const selectedProduct = e.target.closest('li.product-db-response');
            if (!selectedProduct) return;

            // Feedback visual
            selectedProduct.style.background = '#2a2a2a';
            
            const bundle = {
                code: selectedProduct.id,
                name: selectedProduct.querySelector('span').innerText
            };

            // Enviar produto selecionado
            const sendProduct = document.querySelector('.main-container');

            if (sendProduct?.contentWindow) {
                sendProduct.contentWindow.postMessage({
                    type: 'ADD_PRODUCT',
                    data: bundle
                }, "*");
                console.log('Produto enviado:', bundle);
                
                // Limpa busca após seleção
                setTimeout(() => {
                    usersearch.value = '';
                    clearOldResults();
                }, 500);
            } else {
                console.log('Produto selecionado:', bundle);
            }
        });

        // Fechar resultados ao clicar fora
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.function-section')) {
                clearOldResults();
            }
        });
    
    });
