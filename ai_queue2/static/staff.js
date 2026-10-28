// ============================================
// SmartQueue — Staff dashboard
// ============================================

async function loadQueue() {
    const res  = await fetch('/api/queue');
    const data = await res.json();

    document.getElementById('current-serving').textContent = data.current_serving || '—';

    const waiting = data.entries.filter(e => e.status === 'WAITING').length;
    document.getElementById('waiting-count').textContent = waiting;

    const tbody = document.getElementById('staff-table-body');
    tbody.innerHTML = '';

    if (data.entries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">No entries yet.</td></tr>';
        return;
    }

    data.entries.slice().reverse().forEach(e => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${e.token_number}</strong></td>
            <td>${e.customer_name}</td>
            <td>${e.service}</td>
            <td><span class="status status-${e.status.toLowerCase()}">${e.status}</span></td>
            <td>${new Date(e.created_at).toLocaleTimeString()}</td>
        `;
        tbody.appendChild(tr);
    });
}

document.getElementById('btn-call-next').addEventListener('click', async () => {
    const res  = await fetch('/api/staff/call-next', { method: 'POST' });
    const data = await res.json();
    const errEl = document.getElementById('staff-error');
    if (!res.ok) { errEl.textContent = data.error; return; }
    errEl.textContent = '';
    loadQueue();
});

document.getElementById('btn-complete').addEventListener('click', async () => {
    const res  = await fetch('/api/staff/complete', { method: 'POST' });
    const data = await res.json();
    const errEl = document.getElementById('staff-error');
    if (!res.ok) { errEl.textContent = data.error; return; }
    errEl.textContent = '';
    loadQueue();
});

loadQueue();
setInterval(loadQueue, 5000);