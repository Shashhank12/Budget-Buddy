// Set default date to 1 year from now
document.addEventListener('DOMContentLoaded', function() {
    const dateInput = document.getElementById('goal_deadline');
    const nextYear = new Date();
    nextYear.setFullYear(nextYear.getFullYear() + 1);
    dateInput.valueAsDate = nextYear;
});
