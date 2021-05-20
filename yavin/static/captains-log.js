document.getElementById('modal-delete').addEventListener('show.bs.modal', (ev) => {
    const source = ev.relatedTarget;
    ev.target.querySelector('input[name="id"]').value = source.dataset.logId;
});

document.getElementById('modal-edit').addEventListener('show.bs.modal', (ev) => {
    const source = ev.relatedTarget;
    ev.target.querySelector('.modal-title').textContent = source.dataset.logTimestamp;
    ev.target.querySelector('input[name="id"]').value = source.dataset.logId;
    ev.target.querySelector('textarea').value = source.dataset.logText;
});
