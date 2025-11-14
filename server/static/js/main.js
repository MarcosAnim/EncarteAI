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


        
        // Search box para procurar produtos
        const usersearch = document.getElementById('searchInput');
        const searchbutton = document.querySelector('.product-input button');

        function clearOldResults(value) {
            value.innerHTML = '';
        };

        searchbutton.addEventListener('click', async (e) => {
            const searchResults = document.getElementsByClassName('result-box');
            clearOldResults(searchResults[0]);
            const querysearch = await findSimilarProducts(usersearch.value, 10, 0.25);
            

            querysearch.forEach(item => {
                const itemCode = item.code;
                const itemName = item.name;
                const itemUnit = item.unit;
                
                const itemlist = document.createElement('li');
                itemlist.className = 'product-db-response';
                itemlist.id = `${itemCode}`;
                itemlist.innerHTML = `${itemName}`;
                searchResults[0].appendChild(itemlist);
            });

        });


        
        // Selecionar produto da lista de resultados
        const searchResultsBox = document.querySelector('#searchResults');

        searchResultsBox.addEventListener('click', async (e) => {
            const selectedProduct =  e.target.closest('li');
            if (!selectedProduct) return;

            const bundle = {
                code: selectedProduct.id,
                name: selectedProduct.innerText
            }
            // enviar produto selecionado para o maker.html
            const sendProduct = document.querySelector('.main-container');

            if (sendProduct?.contentWindow) {
                sendProduct.contentWindow.postMessage({
                    type: 'ADD_PRODUCT',
                    data: bundle
                }, "*");
                console.log('Produto enviado para o maker:', bundle);
            } else {
                console.error('Iframe não encontrado ou não carregado.');
            }
        })
        
    
    });
