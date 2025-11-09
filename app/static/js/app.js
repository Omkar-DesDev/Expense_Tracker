document.addEventListener('DOMContentLoaded', function(){
  // DataTables (if table id=expensesTable)
  try {
    const table = $('#expensesTable').DataTable({
      paging: true,
      pageLength: 10,
      lengthChange: false,
      searching: true,
      info: false,
      columnDefs: [{ targets: 3, className: 'dt-body-right' }] // align amount right
    });
  } catch(e){ /* DataTables not loaded or table not present */ }

  // AJAX submit for Add Expense modal
  const expenseForm = document.getElementById('expenseForm');
  if (expenseForm){
    expenseForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const btn = document.getElementById('expenseSubmit');
      btn.disabled = true;
      const formData = new FormData(expenseForm);
      try {
        const res = await fetch(expenseForm.action, {
          method: 'POST',
          body: formData,
          headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (res.redirected) {
          // on success redirect or reload
          window.location.href = res.url;
        } else {
          const text = await res.text();
          showToast('Saved', 'Expense saved successfully', 'success');
          // simplest: reload to update list or do DOM insert for single row
          window.location.reload();
        }
      } catch(err){
        showToast('Error', 'Could not save expense', 'danger');
      } finally { btn.disabled = false; }
    });
  }

  // Toast helper
  window.showToast = function(title, message, type='success'){
    const container = document.getElementById('toast-container');
    if(!container) return;
    const id = 't' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${type} border-0`;
    toast.role = 'alert'; toast.ariaLive='assertive'; toast.ariaAtomic='true';
    toast.id = id;
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body"><strong>${title}:</strong> ${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>`;
    container.appendChild(toast);
    const bs = new bootstrap.Toast(toast, { delay: 3500 });
    bs.show();
  };

  // Dark mode toggle (if you add a button with id toggledark)
  const toggle = document.getElementById('toggleDark');
  if (toggle){
    toggle.addEventListener('click', ()=> {
      const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', theme === 'dark' ? 'dark' : '');
      localStorage.setItem('theme', theme);
    });
    // restore theme
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme','dark');
  }
});
