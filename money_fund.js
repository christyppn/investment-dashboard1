const DATA_BASE_URL = './data/';

/**
 * Formats a timestamp string (YYYY-MM-DD) into a more readable format.
 * @param {string} timestamp - The timestamp string.
 * @returns {string} Formatted time string.
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return '未知時間';
    // Assuming timestamp is YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
    return `更新時間: ${timestamp}`;
}

/**
 * Sets the current value and change percentage for a fund card, including color coding.
 * @param {string} symbol - The fund symbol (e.g., 'VFIAX').
 * @param {Object} data - The fund data object.
 */
function renderFundCard(symbol, data) {
    const cleanSymbol = symbol.toLowerCase();
    
    const valueEl = document.getElementById(`${cleanSymbol}-value`);
    const changeEl = document.getElementById(`${cleanSymbol}-change`);
    const dateEl = document.getElementById(`${cleanSymbol}-date`);

    if (!data || Object.keys(data).length === 0) {
        if (valueEl) valueEl.textContent = '--';
        if (changeEl) {
            changeEl.textContent = '無數據';
            changeEl.className = 'fund-change neutral';
        }
        if (dateEl) dateEl.textContent = '數據文件為空或符號無效';
        return;
    }

    const value = data.close;
    const change = data.change_percent;
    const date = data.date;

    if (valueEl) {
        valueEl.textContent = value.toFixed(4); // Use 4 decimal places for funds
    }

    if (changeEl) {
        changeEl.textContent = (change > 0 ? '+' : '') + change.toFixed(2) + '%';
        changeEl.className = 'fund-change ' + (change > 0 ? 'positive' : (change < 0 ? 'negative' : 'neutral'));
    }

    if (dateEl) {
        dateEl.textContent = formatTimestamp(date);
    }
}

/**
 * Loads and displays money fund data.
 */
async function loadMoneyFundData() {
    try {
        // Use cache-busting to ensure the latest file is fetched
        const response = await fetch(`${DATA_BASE_URL}money_fund_data.json?v=${new Date().getTime()}`);
        const data = await response.json();

        // The symbols are hardcoded in the HTML
        const symbols = ["VFIAX", "VTSAX", "VBTLX", "VMMXX"];

        symbols.forEach(symbol => {
            renderFundCard(symbol, data[symbol]);
        });

    } catch (error) {
        console.error("Error loading money fund data:", error);
        // Display error on cards if fetch fails completely
        const symbols = ["VFIAX", "VTSAX", "VBTLX", "VMMXX"];
        symbols.forEach(symbol => {
            const cleanSymbol = symbol.toLowerCase();
            const dateEl = document.getElementById(`${cleanSymbol}-date`);
            if (dateEl) dateEl.textContent = `載入失敗: ${error.message}`;
        });
    }
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    loadMoneyFundData();
});
