/**
 * Main Interactive JS for Local Worker Directory (ช่างใกล้บ้าน)
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Bootstrap Tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // 2. Auto-hide Alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-auto-dismiss');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // 3. Quick Test Account Filler on Login Page
    window.fillLogin = function(email, password) {
        const emailInput = document.getElementById('id_username');
        const passInput = document.getElementById('id_password');
        if (emailInput && passInput) {
            emailInput.value = email;
            passInput.value = password;
            emailInput.focus();
        }
    };

    // 4. AJAX Bookmark / Save Worker
    document.querySelectorAll('.btn-ajax-save').forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            const workerId = button.getAttribute('data-worker-id');
            const url = `/workers/${workerId}/save/?format=json`;

            try {
                const response = await fetch(url, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                const data = await response.json();
                if (data.status === 'success') {
                    if (data.saved) {
                        button.classList.add('active');
                        button.innerHTML = '<i class="fa-solid fa-heart text-danger"></i>';
                        showToast(data.message || 'บันทึกช่างเรียบร้อยแล้ว', 'success');
                    } else {
                        button.classList.remove('active');
                        button.innerHTML = '<i class="fa-regular fa-heart"></i>';
                        showToast(data.message || 'ยกเลิกการบันทึกแล้ว', 'info');
                    }
                }
            } catch (err) {
                console.error(err);
                window.location.href = `/workers/${workerId}/save/`;
            }
        });
    });

    // 5. Toast Notification Helper
    window.showToast = function(message, type = 'info') {
        let container = document.getElementById('custom-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'custom-toast-container';
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            container.style.zIndex = '1100';
            document.body.appendChild(container);
        }

        const bgClass = type === 'success' ? 'bg-success' : (type === 'error' ? 'bg-danger' : 'bg-primary');
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-white ${bgClass} border-0 shadow-lg`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center gap-2">
                    <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-info-circle'}"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        container.appendChild(toastEl);
        const bsToast = new bootstrap.Toast(toastEl, { delay: 4000 });
        bsToast.show();
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    };
});
