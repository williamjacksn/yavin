document.getElementById('modal-package').addEventListener('show.bs.modal', (ev) => {
    const source = ev.relatedTarget;
    document.getElementById('modal-action').textContent = source.dataset.action;
    document.getElementById('arrived-at').value = source.dataset.arrivedAt;
    document.getElementById('expected-at').value = source.dataset.expectedAt;
    document.getElementById('notes').value = source.dataset.notes;
    document.getElementById('shipper').value = source.dataset.shipper;
    document.getElementById('tracking-number').value = source.dataset.trackingNumber;
});
