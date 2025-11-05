document.addEventListener('DOMContentLoaded', () => {

        document.querySelectorAll('.toggle').forEach(toggle => {
            toggle.addEventListener('click', function() {
                this.classList.toggle('active');
            });
        });

        /* Excluir produto da lista */
        document.querySelectorAll('.product-card').forEach(card => {
            card.querySelector('.close-btn').addEventListener('click', function(e) {
                e.stopPropagation();
                card.remove();
            });
        });
        
        /* Dropdown user config */
        const btn = document.getElementById('config-btn');
        const menu = document.getElementById('config-menu');

        btn.addEventListener('click', (e) => {
            e.stopPropagation(); // evita fechar ao clicar no ícone
            menu.classList.toggle('show');
        });

        // Fecha o menu ao clicar fora
        document.addEventListener('click', () => {
            menu.classList.remove('show');
        });

});
