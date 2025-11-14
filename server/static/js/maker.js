document.addEventListener('DOMContentLoaded', () => {

        document.querySelectorAll('.toggle').forEach(toggle => {
            toggle.addEventListener('click', function() {
                this.classList.toggle('active');
            });
        });

        const productGrid = document.querySelector('.products-grid')
        window.addEventListener('message', (event) => {
            
            if (event.data.type === 'ADD_PRODUCT') {
                const productId = event.data.data.code;
                const productName = event.data.data.name;
                const productCard = document.createElement('div');
                
                productCard.classList.add('product-card');
                productCard.innerHTML = `
                    <button class="close-btn">x</button>
                    <img class="product-image" src="https://i.ibb.co/5h3D0zB4/12203.png" alt="Produto">
                    <p>${productName}</p>
                `;
                productGrid.appendChild(productCard);
                
        }});
        
        /* Excluir produto da lista */
        productGrid.addEventListener('click', (e) => {
            if (e.target.classList.contains('close-btn')) {
                e.stopPropagation();
                const card = e.target.closest('.product-card');
                card.remove();
                console.log('Produto removido');
            }

    });
});
