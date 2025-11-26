// money_fund.js - 最終修復版本 (No auto-run)

const DATA_BASE_URL = './data/';

// --- Helper Functions ---

/**
 * Renders a single money fund card.
 * @param {string} symbol - The fund symbol.
 * @param {string} name - The fund name.
 * @param {Object} data - The latest data point for the fund.
 */
function renderFundCard(symbol, name, data) {
    const cleanSymbol = symbol.toLowerCase();
    
    const valueEl = document.getElementById(`${cleanSymbol}-value`);
    const changeEl = document.getElementById(`${cleanSymbol}-change`);
    const dateEl = document.getElementById(`${cleanSymbol}-date`);

    if (!data) {
        if (valueEl) valueEl.textContent = '--';
        if (changeEl) changeEl.textContent = '無數據';
        if (changeEl) changeEl.className = 'change-percent neutral';
        if (dateEl) dateEl.textContent = '載入中...';
        return;
    }

    const close = data.close;
    const change = data.change_percent;

    if (valueEl) valueEl.textContent = close.toFixed(4); // Use 4 decimal places for funds
    if (changeEl) changeEl.textContent = (change > 0 ? '+' : '') + change.toFixed(2) + '%';
    if (dateEl) dateEl.textContent = `更新時間: ${data.date}`;
    
    let changeClass = 'neutral';
    if (change > 0) {
        changeClass = 'positive';
    } else if (change < 0) {
        changeClass = 'negative';
    }
    if (changeEl) changeEl.className = `change-percent ${changeClass}`;
}

// --- Data Loading Functions ---

/**
 * Loads and renders the money fund data. This function is called by switchTab in script.js.
 */
async function loadMoneyFundData() {
    try {
        // Use fetchData from script.js if available, otherwise use local fetch
        const fetchFunc = typeof fetchData === 'function' ? fetchData : (path) => fetch(`${DATA_BASE_URL}${path}?v=${new Date().getTime()}`).then(res => res.json());
        
        const data = await fetchFunc("money_fund_data.json");

        // The symbols are hardcoded in the HTML
        const fundSymbols = [
            { symbol: "VFIAX", name: "Vanguard 500 Index Fund" },
            { symbol: "VTSAX", name: "Vanguard Total Stock Market Index Fund" },
            { symbol: "VBTLX", name: "Vanguard Total Bond Market Index Fund" },
            { symbol: "BIL", name: "SPDR Bloomberg 1-3 Month T-Bill ETF" } // VMMXX is now BIL
        ];

        fundSymbols.forEach(fund => {
            // Use the symbol from the fundSymbols array to look up data
            // Note: The HTML uses VMMXX for the last card, but sync_data.py uses BIL.
            // We must use the key that sync_data.py writes to the JSON.
            const dataKey = (fund.symbol === "BIL") ? "VMMXX" : fund.symbol; // Use VMMXX as the key for the BIL data
            renderFundCard(fund.symbol, fund.name, data[dataKey]);
        });

    } catch (error) {
        console.error("Error loading money fund data:", error);
        // Display error on cards if fetch fails completely
        const fundSymbols = ["VFIAX", "VTSAX", "VBTLX", "BIL"];
        fundSymbols.forEach(symbol => {
            const dateEl = document.getElementById(`${symbol.toLowerCase()}-date`);
            if (dateEl) dateEl.textContent = `載入失敗: ${error.message}`;
        });
    }
}

// Expose the function globally so script.js can call it
window.loadMoneyFundData = loadMoneyFundData;

// --- Initialization (Removed DOMContentLoaded listener) ---
// The function is now called by script.js when the tab is clicked.
