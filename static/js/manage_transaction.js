// Ensure Bootstrap is loaded before initializing modals
let editTransactionModal;
let deleteConfirmModal;

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded, initializing transaction page");

    // Initialize Modals after DOM is ready and Bootstrap JS is likely loaded
    const editModalElement = document.getElementById('editTransactionModal');
    const deleteModalElement = document.getElementById('deleteConfirmModal');
    if (editModalElement && typeof bootstrap !== 'undefined') {
        editTransactionModal = new bootstrap.Modal(editModalElement);
    } else {
        console.error('Edit modal element not found or Bootstrap not loaded');
    }
    if (deleteModalElement && typeof bootstrap !== 'undefined') {
        deleteConfirmModal = new bootstrap.Modal(deleteModalElement);
    } else {
        console.error('Delete modal element not found or Bootstrap not loaded');
    }

    // Find all needed DOM elements
    const transactionTableLoading = document.getElementById('transactionTableLoading');
    const transactionTableBody = document.getElementById('transactionTableBody');
    const noTransactionsMessage = document.getElementById('noTransactionsMessage');

    // Check if filter elements exist before trying to access them
    const filterStartDateInput = document.getElementById('filterStartDate');
    const filterEndDateInput = document.getElementById('filterEndDate');

    // **MODIFICATION:** Do NOT set default date values here
    // Let the inputs start empty to show all transactions initially
    /*
    if (filterStartDateInput && filterEndDateInput) {
        const today = new Date();
        const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDayOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        const formatDate = (date) => date.toISOString().split('T')[0];
        filterStartDateInput.value = formatDate(firstDayOfMonth);
        filterEndDateInput.value = formatDate(lastDayOfMonth);
    } else {
        console.error("Start or End date filter inputs not found.");
    }
    */

    // Initial load of transactions (will load all since dates are empty)
    loadTransactions();
});

// Filter elements
const transactionTableLoading = document.getElementById('transactionTableLoading');
const transactionTableBody = document.getElementById('transactionTableBody');
const noTransactionsMessage = document.getElementById('noTransactionsMessage');
const filterCategorySelect = document.getElementById('filterCategory');
const filterAccountSelect = document.getElementById('filterAccount');
const filterStartDateInput = document.getElementById('filterStartDate');
const filterEndDateInput = document.getElementById('filterEndDate');
const filterDescriptionInput = document.getElementById('filterDescription');
const filterMinAmountInput = document.getElementById('filterMinAmount');
const filterMaxAmountInput = document.getElementById('filterMaxAmount');
const filterSortSelect = document.getElementById('filterSort');
const clearFiltersButton = document.getElementById('clearFilters');

// Modal elements (references for use inside functions)
const editTransactionId = document.getElementById('editTransactionId');
const editAmount = document.getElementById('editAmount');
const editDescription = document.getElementById('editDescription');
const editDate = document.getElementById('editDate');
const editCategory = document.getElementById('editCategory');
const editAccount = document.getElementById('editAccount');
const deleteTransactionId = document.getElementById('deleteTransactionId');
const confirmDeleteBtn = document.getElementById('confirmDelete');
const saveTransactionChangesBtn = document.getElementById('saveTransactionChanges');

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

async function loadTransactions() {
    // Check essential elements needed for loading
    if (!transactionTableLoading || !transactionTableBody || !noTransactionsMessage) {
         console.error("Error: Core table/loading elements not found.");
         if (transactionTableBody) {
             transactionTableBody.innerHTML = '<tr><td colspan="6" class="text-center text-danger p-3">Error: Page elements missing. Cannot load transactions.</td></tr>';
         }
         return;
    }
     if (!filterCategorySelect || !filterStartDateInput || !filterEndDateInput || !filterDescriptionInput ||
         !filterAccountSelect || !filterMinAmountInput || !filterMaxAmountInput || !filterSortSelect) {
         console.warn("Warning: One or more filter elements not found. Filtering might be incomplete.");
    }

    transactionTableLoading.style.display = 'block';
    transactionTableBody.innerHTML = '';
    noTransactionsMessage.style.display = 'none';

    const params = new URLSearchParams({
        start_date: filterStartDateInput ? filterStartDateInput.value : '',
        end_date: filterEndDateInput ? filterEndDateInput.value : '',
        category: filterCategorySelect ? filterCategorySelect.value : '',
        account: filterAccountSelect ? filterAccountSelect.value : '',
        description: filterDescriptionInput ? filterDescriptionInput.value : '',
        min_amount: filterMinAmountInput ? filterMinAmountInput.value : '',
        max_amount: filterMaxAmountInput ? filterMaxAmountInput.value : '',
        sort: filterSortSelect ? filterSortSelect.value : 'date_desc'
    });

    const paramsToDelete = [];
    params.forEach((value, key) => {
        if (!value) {
            paramsToDelete.push(key);
        }
    });
    paramsToDelete.forEach(key => params.delete(key));

    const apiUrl = `/api/transactions?${params.toString()}`;
    console.log("Fetching transactions with filters:", apiUrl);

    try {
        const response = await fetch(apiUrl);
        const data = await response.json();

        if (!response.ok) {
            const errorMsg = data?.error || data?.message || response.statusText;
            throw new Error(errorMsg || `HTTP error ${response.status}`);
        }

        if (data && data.length > 0) {
            data.forEach(t => {
                const row = transactionTableBody.insertRow();
                row.dataset.transactionId = t.Transaction_ID;

                let displayDate = 'N/A';
                if (t.Transaction_Date) {
                    displayDate = t.Transaction_Date;
                }
                row.insertCell().textContent = displayDate;

                row.insertCell().textContent = t.Transaction_Description || '-';
                row.insertCell().textContent = t.Category_Name || 'Uncategorized';

                const amountCell = row.insertCell();
                const amount = parseFloat(t.Transaction_Amount || 0);
                amountCell.textContent = amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
                amountCell.classList.add(amount >= 0 ? 'amount-positive' : 'amount-negative');
                amountCell.style.textAlign = 'right';

                row.insertCell().textContent = t.Account_Name || 'N/A';

                const actionsCell = row.insertCell();
                actionsCell.className = 'text-center action-buttons';
                actionsCell.innerHTML = `
                    <button class="btn btn-sm btn-outline-primary edit-btn" data-id="${t.Transaction_ID}" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-btn ms-1" data-id="${t.Transaction_ID}" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                `;
            });

            transactionTableBody.querySelectorAll('.edit-btn').forEach(btn => {
                btn.addEventListener('click', handleEditClick);
            });
            transactionTableBody.querySelectorAll('.delete-btn').forEach(btn => {
                btn.addEventListener('click', handleDeleteClick);
            });
        } else {
            noTransactionsMessage.style.display = 'block';
        }

    } catch (error) {
        console.error("Error loading transactions:", error);
        transactionTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger p-3">Error loading transactions: ${error.message}</td></tr>`;
        noTransactionsMessage.style.display = 'none';
    } finally {
        transactionTableLoading.style.display = 'none';
    }
}

function handleFilterChange() {
    console.log("Filter changed, reloading transactions...");
    loadTransactions();
}

function handleClearFilters() {
    // Check if elements exist before setting value
    if (filterCategorySelect) filterCategorySelect.value = '';
    if (filterAccountSelect) filterAccountSelect.value = '';
    if (filterDescriptionInput) filterDescriptionInput.value = '';
    if (filterMinAmountInput) filterMinAmountInput.value = '';
    if (filterMaxAmountInput) filterMaxAmountInput.value = '';
    if (filterSortSelect) filterSortSelect.value = 'date_desc';

    // **MODIFICATION:** Clear date fields instead of resetting to current month
    if (filterStartDateInput) filterStartDateInput.value = '';
    if (filterEndDateInput) filterEndDateInput.value = '';
    /* Remove this block:
    if (filterStartDateInput && filterEndDateInput) {
         const today = new Date();
         const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
         const lastDayOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
         const formatDate = (date) => date.toISOString().split('T')[0];

         filterStartDateInput.value = formatDate(firstDayOfMonth);
         filterEndDateInput.value = formatDate(lastDayOfMonth);
    }
    */

    loadTransactions();
}

function handleEditClick(e) {
    const transactionId = e.currentTarget.dataset.id;
    const row = document.querySelector(`tbody#transactionTableBody tr[data-transaction-id="${transactionId}"]`);

    if (!editTransactionModal) {
        console.error("Edit modal not initialized.");
        alert("Error: Cannot open edit form.");
        return;
    }

    if (!editTransactionId || !editAmount || !editDescription || !editDate || !editCategory || !editAccount) {
        console.error("One or more edit modal form elements not found.");
        alert("Error: Edit form is broken.");
        return;
    }

    if (row) {
        const cells = row.cells;
        if (cells.length < 6) {
            console.error("Table row structure seems incorrect.");
            alert("Error reading transaction data.");
            return;
        }

        const dateStr = cells[0].textContent;
        const description = cells[1].textContent;
        const category = cells[2].textContent;
        const amountText = cells[3].textContent;
        const accountName = cells[4].textContent;

        let amount = 0;
        try {
           amount = parseFloat(amountText.replace(/[^0-9.-]+/g, ''));
        } catch (parseError) {
           console.error("Could not parse amount:", amountText, parseError);
           alert("Error reading transaction amount.");
           return;
        }

        editTransactionId.value = transactionId;
        editAmount.value = amount;
        editDescription.value = description === '-' ? '' : description;
        editDate.value = (dateStr !== 'N/A') ? dateStr : '';

        let categoryFound = false;
        Array.from(editCategory.options).forEach(option => {
            if (option.text === category) {
                option.selected = true;
                categoryFound = true;
            } else {
                option.selected = false;
            }
        });
         if (!categoryFound) console.warn(`Category "${category}" not found in edit dropdown.`);

        let accountFound = false;
        Array.from(editAccount.options).forEach(option => {
            if (option.text === accountName) {
                option.selected = true;
                accountFound = true;
            } else {
                option.selected = false;
            }
        });
        if (!accountFound) console.warn(`Account "${accountName}" not found in edit dropdown.`);

        editTransactionModal.show();
    } else {
         console.error(`Row for transaction ID ${transactionId} not found.`);
         alert("Error: Could not find transaction details to edit.");
    }
}

function handleDeleteClick(e) {
     if (!deleteConfirmModal) {
        console.error("Delete confirmation modal not initialized.");
        alert("Error: Cannot open delete confirmation.");
        return;
    }
     if (!deleteTransactionId) {
        console.error("Delete transaction ID input not found in modal.");
         alert("Error: Delete confirmation is broken.");
         return;
    }
    const transactionIdVal = e.currentTarget.dataset.id;
    deleteTransactionId.value = transactionIdVal;
    deleteConfirmModal.show();
}

async function saveTransactionChanges() {
    if (!editTransactionId || !editAmount || !editDescription || !editDate || !editCategory || !editAccount || !editTransactionModal) {
        console.error("Cannot save: Edit form elements or modal instance missing.");
        alert("Error: Cannot save changes, form is broken.");
        return;
    }

    const formData = {
        transaction_id: editTransactionId.value,
        amount: editAmount.value,
        description: editDescription.value,
        date: editDate.value,
        category: editCategory.options[editCategory.selectedIndex].text,
        account: editAccount.value
    };

     if (!formData.transaction_id || !formData.amount || !formData.date || !formData.category || !formData.account) {
          alert("Please fill in all required fields (Amount, Date, Category, Account).");
          return;
     }

    try {
        const response = await fetch('/api/transactions/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData),
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Just close the modal and refresh the data
            editTransactionModal.hide();
            loadTransactions();
        } else {
            const errorMsg = result?.error || result?.message || 'Failed to update transaction';
            alert(`Error: ${errorMsg}`);
            console.error("Update failed:", result);
        }
    } catch (error) {
        console.error('Error updating transaction:', error);
        alert('Failed to update transaction due to a network or server error. Please try again.');
    }
}

async function deleteTransaction() {
    if (!deleteTransactionId || !deleteConfirmModal) {
        console.error("Cannot delete: Delete confirmation elements missing.");
        alert("Error: Cannot perform deletion.");
        return;
    }

    const transactionIdVal = deleteTransactionId.value;
    if (!transactionIdVal) {
         alert("Error: No transaction selected for deletion.");
         return;
    }

    try {
        const response = await fetch(`/api/transactions/delete/${transactionIdVal}`, {
            method: 'DELETE',
        });

        const result = await response.json();

        if (response.ok && result.success) {
            alert('Transaction deleted successfully');
            deleteConfirmModal.hide();
            loadTransactions();
        } else {
            const errorMsg = result?.error || result?.message || 'Failed to delete transaction';
            alert(`Error: ${errorMsg}`);
            console.error("Delete failed:", result);
        }
    } catch (error) {
        console.error('Error deleting transaction:', error);
        alert('Failed to delete transaction due to a network or server error. Please try again.');
    }
}

const debouncedDescriptionHandler = debounce(handleFilterChange, 400);
const debouncedAmountHandler = debounce(handleFilterChange, 400);

if (filterCategorySelect) filterCategorySelect.addEventListener('change', handleFilterChange);
if (filterAccountSelect) filterAccountSelect.addEventListener('change', handleFilterChange);
if (filterStartDateInput) filterStartDateInput.addEventListener('change', handleFilterChange);
if (filterEndDateInput) filterEndDateInput.addEventListener('change', handleFilterChange);
if (filterSortSelect) filterSortSelect.addEventListener('change', handleFilterChange);
if (filterDescriptionInput) filterDescriptionInput.addEventListener('input', debouncedDescriptionHandler);
if (filterMinAmountInput) filterMinAmountInput.addEventListener('input', debouncedAmountHandler);
if (filterMaxAmountInput) filterMaxAmountInput.addEventListener('input', debouncedAmountHandler);
if (clearFiltersButton) clearFiltersButton.addEventListener('click', handleClearFilters);

if (saveTransactionChangesBtn) saveTransactionChangesBtn.addEventListener('click', saveTransactionChanges);
if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', deleteTransaction);
