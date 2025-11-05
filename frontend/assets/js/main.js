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
            const contentArea = document.getElementById("content-area");

            try {
                const response = await fetch(page);
                if (!response.ok) throw new Error("Página não encontrada");
                const html = await response.text();

                // Animação de fade suave
                contentArea.style.opacity = "0";
                setTimeout(() => {
                    contentArea.innerHTML = html;
                    contentArea.style.opacity = "1";
                }, 200);
            
                // **CORREÇÃO APLICADA AQUI**

                if (event && event.target && event.target.nodeType === 1) { 
                    document.querySelectorAll(".menu-items li").forEach(li => li.classList.remove("active"));
                    event.target.classList.add("active");
                }

            } catch (error) {
                // Adicione console.error para ver detalhes no console
                console.error("Fetch Error:", error); 
                contentArea.innerHTML = `<p style="color:red;">Erro ao carregar o conteúdo de <strong>${page}</strong>.</p>`;
                
                // É importante retornar aqui para que o código de manipulação de menu não 
                // tente rodar se o fetch falhou.
                return; 
            }
        }

        window.addEventListener("DOMContentLoaded", () => {
            // Chamada inicial (passando 'null' para o evento)
            loadContent(null, "components/maker.html"); 
            
        });
        
})
