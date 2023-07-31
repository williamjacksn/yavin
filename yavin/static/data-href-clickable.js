document.querySelectorAll('[data-href]').forEach((el) => {
    el.addEventListener('click', (ev) => {
        const target = ev.target.closest('[data-href]');
        window.location = target.dataset.href;
    });
});
