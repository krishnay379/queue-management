// ============================================
// SmartQueue — Live queue page
// ============================================

const TOKEN = document.getElementById('q-token').textContent;

async function loadQueue() {
    try {
        const res  = await fetch(`/api/queue/${TOKEN}`);
        const data = await res.json();
        if (!res.ok) { console.error(data.error); return; }

        document.getElementById('q-current').textContent = data.current_serving || '—';
        document.getElementById('q-ahead').textContent   = data.people_ahead;
        document.getElementById('q-wait').textContent    = data.estimated_wait_minutes + ' min';
        document.getElementById('q-status').textContent  = data.status;
        document.getElementById('q-service').textContent = data.service;
    } catch (err) {
        console.error(err);
    }
}

document.getElementById('q-refresh').addEventListener('click', loadQueue);

document.getElementById('q-cancel').addEventListener('click', async () => {
    if (!confirm('Cancel this token?')) return;
    const res  = await fetch(`/api/queue/${TOKEN}/cancel`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) { alert(data.error || 'Error'); return; }
    alert('Token cancelled.');
    loadQueue();
});

loadQueue();
setInterval(loadQueue, 10000);