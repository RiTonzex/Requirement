/**
 * Client-side script for Local Skilled Worker Directory (ช่างใกล้บ้าน)
 */

document.addEventListener('DOMContentLoaded', function() {
    // Auto dismiss flash alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Quick Fill Demo Credentials on Login Page
    window.fillCredentials = function(email, password) {
        const emailInput = document.getElementById('loginEmail');
        const passInput = document.getElementById('loginPassword');
        if (emailInput && passInput) {
            emailInput.value = email;
            passInput.value = password;
        }
    };

    // Toggle Saved Worker (Bookmark)
    const saveButtons = document.querySelectorAll('.btn-toggle-save');
    saveButtons.forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            const workerId = this.getAttribute('data-worker-id');
            if (!workerId) return;

            try {
                const response = await fetch('index.php?page=api_save_worker', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'worker_id=' + encodeURIComponent(workerId)
                });
                const result = await response.json();
                if (result.success) {
                    if (result.saved) {
                        this.classList.remove('btn-outline-secondary');
                        this.classList.add('btn-warning');
                        this.innerHTML = '<i class="fas fa-bookmark me-1"></i> บันทึกแล้ว';
                    } else {
                        this.classList.remove('btn-warning');
                        this.classList.add('btn-outline-secondary');
                        this.innerHTML = '<i class="far fa-bookmark me-1"></i> บันทึกช่าง';
                    }
                } else if (result.redirect) {
                    window.location.href = result.redirect;
                } else {
                    alert(result.message || 'เกิดข้อผิดพลาด');
                }
            } catch (err) {
                console.error('Save error:', err);
            }
        });
    });

    // Confirm Delete Actions
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            const msg = this.getAttribute('data-confirm') || 'คุณแน่ใจหรือไม่ว่าต้องการดำเนินการนี้?';
            if (!confirm(msg)) {
                e.preventDefault();
            }
        });
    });
});
