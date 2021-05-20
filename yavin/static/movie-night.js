document.getElementById('modal-edit').addEventListener('show.bs.modal', (ev) => {
    const source = ev.relatedTarget;
    ev.target.querySelector('input[name="id"]').value = source.dataset.pickId;
    ev.target.querySelector('#edit-pick-date').value = source.dataset.pickDate;
    ev.target.querySelectorAll('option').forEach((el) => {
        if (el.value === source.dataset.pickPersonId) {
            el.selected = true;
        }
    });
    ev.target.querySelector('#edit-pick-text').value = source.dataset.pickText;
    ev.target.querySelector('#edit-pick-url').value = source.dataset.pickUrl;
});
