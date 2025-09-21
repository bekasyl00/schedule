document.addEventListener('DOMContentLoaded', function() {
    // Пример: подсветка строки при клике
    const rows = document.querySelectorAll('.schedule-table tbody tr');
    rows.forEach(row => {
        row.addEventListener('click', function() {
            rows.forEach(r => r.classList.remove('selected'));
            this.classList.add('selected');
        });
    });
});