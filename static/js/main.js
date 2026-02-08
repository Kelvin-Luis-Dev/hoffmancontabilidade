document.addEventListener('DOMContentLoaded', () => {
    const navToggle = document.querySelector('.nav-toggle');
    const mainNav = document.querySelector('.main-nav');
    const body = document.body;

    // Função centralizada para fechar o menu e restaurar o comportamento da página
    function closeMenu() {
        if (mainNav.classList.contains('open')) {
            mainNav.classList.remove('open');
            body.style.overflow = '';
            body.classList.remove('menu-open');
            navToggle.setAttribute('aria-expanded', 'false');
        }
    }

    if (navToggle && mainNav) {
        navToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = mainNav.classList.toggle('open');
            
            // Atualiza acessibilidade
            navToggle.setAttribute('aria-expanded', isOpen);

            if (isOpen) {
                // Trava a rolagem do fundo para focar no menu (UX Mobile)
                body.style.overflow = 'hidden';
                body.classList.add('menu-open');
            } else {
                closeMenu();
            }
        });

        // Fecha o menu ao clicar fora dele (em qualquer lugar da página)
        document.addEventListener('click', (e) => {
            if (!mainNav.contains(e.target) && !navToggle.contains(e.target)) {
                closeMenu();
            }
        });
    }

    // Fecha o menu imediatamente ao clicar em um link
    const menuLinks = document.querySelectorAll('.main-nav a');
    menuLinks.forEach(link => {
        link.addEventListener('click', closeMenu);
    });

    // Tratamento para submenus (Dropdown de Serviços) em dispositivos touch
    const dropdownLinks = document.querySelectorAll('.has-dropdown > a');
    dropdownLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            if (window.innerWidth < 992) {
                e.preventDefault(); // Impede a navegação imediata no mobile para abrir o submenu
                const parent = link.parentElement;
                parent.classList.toggle('active');
            }
        });
    });
});

// Reset de segurança para o histórico do navegador (botão voltar)
window.addEventListener('pageshow', () => {
    document.body.style.overflow = '';
    document.body.classList.remove('menu-open');
});
