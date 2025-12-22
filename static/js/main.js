document.addEventListener('DOMContentLoaded', () => {
    const navToggle = document.querySelector('.nav-toggle');
    const mainNav = document.querySelector('.main-nav');
    const body = document.body;
    const html = document.documentElement;

    function closeMenu() {
        mainNav.classList.remove('open');
        body.style.overflow = '';
        html.style.overflow = '';
        body.classList.remove('menu-open');
    }

    if (navToggle && mainNav) {
        navToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = mainNav.classList.toggle('open');

            if (isOpen) {
                body.style.overflow = 'hidden';
                html.style.overflow = 'hidden';
                body.classList.add('menu-open');
            } else {
                closeMenu();
            }
        });
    }

    // AQUI ESTÁ O SEGREDO:
    // Quando clicar em QUALQUER link do menu, limpa as travas imediatamente
    const menuLinks = document.querySelectorAll('.main-nav a');
    menuLinks.forEach(link => {
        link.addEventListener('click', () => {
            closeMenu();
        });
    });
});

// Garante que ao entrar na nova página, nada esteja travado
window.addEventListener('pageshow', () => {
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
});