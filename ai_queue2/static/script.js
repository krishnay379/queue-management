// ============================================
// SmartQueue — Homepage logic
// ============================================

const backdrop       = document.getElementById('modal-backdrop');
const ticketBackdrop = document.getElementById('ticket-backdrop');
const serviceNameEl  = document.getElementById('modal-service-name');
const nameInput      = document.getElementById('customer-name');
const errorEl        = document.getElementById('modal-error');

let selectedService = null;

// Open modal when a service is clicked
document.querySelectorAll('.service-card').forEach(card => {
    card.addEventListener('click', () => {
        selectedService = card.dataset.serviceName;
        serviceNameEl.textContent = selectedService;
        nameInput.value = '';
        errorEl.textContent = '';
        backdrop.classList.add('open');
        nameInput.focus();
    });
});

// Cancel modal
document.getElementById('modal-cancel').addEventListener('click', closeModal);
backdrop.addEventListener('click', (e) => { if (e.target === backdrop) closeModal(); });

function closeModal() { backdrop.classList.remove('open'); }

// Confirm join
document.getElementById('modal-confirm').addEventListener('click', async () => {
    const name = nameInput.value.trim();
    if (!name) { errorEl.textContent = 'Please enter your name.'; return; }

    try {
        const res = await fetch('/api/join-queue', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ customer_name: name, service: selectedService }),
        });
        const data = await res.json();

        if (!res.ok) { errorEl.textContent = data.error || 'Something went wrong.'; return; }
        closeModal();
        showTicket(data);
    } catch (err) {
        errorEl.textContent = 'Network error. Try again.';
    }
});

// Show ticket
function showTicket(data) {
    document.getElementById('ticket-token').textContent   = data.token_number;
    document.getElementById('ticket-service').textContent = data.service;
    document.getElementById('ticket-ahead').textContent   = data.people_ahead;
    document.getElementById('ticket-wait').textContent    = data.estimated_wait_minutes + ' min';
    document.getElementById('ticket-status').textContent  = data.status;
    document.getElementById('ticket-live').href           = '/queue/' + data.token_number;
    ticketBackdrop.classList.add('open');
}

// Cancel queue from ticket
document.getElementById('ticket-cancel').addEventListener('click', async () => {
    const token = document.getElementById('ticket-token').textContent;
    if (!confirm('Cancel your queue token ' + token + '?')) return;

    const res = await fetch(`/api/queue/${token}/cancel`, { method: 'POST' });
    const data = await res.json();

    if (!res.ok) { alert(data.error || 'Could not cancel.'); return; }
    ticketBackdrop.classList.remove('open');
    alert('Token cancelled.');
    location.reload();
});

// Smooth scroll for hash links
document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
        const target = document.querySelector(link.getAttribute('href'));
        if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth' }); }
    });
});

console.log('SmartQueue homepage ready.');