document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const loginSection = document.getElementById('loginSection');
    const dataSection = document.getElementById('dataSection');
    const tableBody = document.getElementById('tableBody');
    const logoutBtn = document.getElementById('logoutBtn');

    // Check if already logged in (optional persistence)
    // sessionStorage.setItem('isAdmin', 'true') could be used, but let's keep it simple: always ask or simple session.
    if (sessionStorage.getItem('lumaAdminLoggedIn') === 'true') {
        showData();
    }

    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const password = document.getElementById('adminPassword').value;

        if (password === 'Amiri Johnson') {
            sessionStorage.setItem('lumaAdminLoggedIn', 'true');
            showData();
            loginForm.reset();
        } else {
            alert('Incorrect Password');
        }
    });

    logoutBtn.addEventListener('click', () => {
        sessionStorage.removeItem('lumaAdminLoggedIn');
        loginSection.style.display = 'block';
        dataSection.style.display = 'none';
    });

    function showData() {
        loginSection.style.display = 'none';
        dataSection.style.display = 'block';
        renderTable();
    }

    async function renderTable() {
        try {
            const response = await fetch('/api/reservations');
            if (!response.ok) {
                throw new Error('Failed to fetch data');
            }
            const data = await response.json();

            tableBody.innerHTML = '';

            if (data.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="3" class="empty-state">No reservations found</td></tr>';
                return;
            }

            // Sort by newest first (assuming timestamp is ISO string)
            data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

            data.forEach(entry => {
                const tr = document.createElement('tr');

                // Format Date
                const dateStr = new Date(entry.timestamp).toLocaleString();

                tr.innerHTML = `
                    <td>${dateStr}</td>
                    <td>${entry.email}</td>
                    <td>${entry.phone}</td>
                `;
                tableBody.appendChild(tr);
            });
        } catch (err) {
            console.error('Error loading data:', err);
            tableBody.innerHTML = '<tr><td colspan="3" class="empty-state" style="color:red">Error loading data. Is the server running?</td></tr>';
        }
    }
});
