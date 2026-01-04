// Load search history when the page loads
document.addEventListener('DOMContentLoaded', loadSearchHistory);

// Save the search query to localStorage
function saveSearchHistory(event) {
    event.preventDefault();
    const searchInput = document.getElementById('searchInput');
    const query = searchInput.value.trim();

    if (!query) return;

    let history = JSON.parse(localStorage.getItem('searchHistory')) || [];

    // Avoid duplicate queries
    if (!history.includes(query)) {
        history.unshift(query); // Add to the beginning of the array
    }

    // Limit history to 10 items
    if (history.length > 10) {
        history.pop();
    }

    localStorage.setItem('searchHistory', JSON.stringify(history));
    loadSearchHistory();

    // Optionally submit the form
    event.target.submit();
}

// Load History and Render It
function loadSearchHistory() {
    const history = JSON.parse(localStorage.getItem('searchHistory')) || [];
    const historyList = document.getElementById('historyList');
    historyList.innerHTML = ''; // Clear existing history

    history.forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = `<a href="#">${item}</a>`;
        historyList.appendChild(li);
    });
}

// Clear All Search History
function clearHistory() {
    localStorage.removeItem('searchHistory');
    loadSearchHistory();
}