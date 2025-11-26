// money_fund.js - 最終修復版本 (Final Corrected Version)

const DATA_BASE_URL = './data/';

// --- Helper Functions ---

function formatChange(change) {
    const isPositive = change >= 0;
    const sign = isPositive ? '+' : '';
    const colorClass = isPositive ? 'positive' : 'negative';
    return `<span class="${colorClass}">${sign}${change.toFixed(2)}%</span>`;
}

// --- Data Loading Functions ---

/**
 * Loads and renders the money fund data. This function is called by switchTab in script.js.
 */
async function loadMoneyFundData() {
    const data = await fetchData('money_fund_data.json');
    if (!data || !data.funds) {
        console.error("Money fund data is missing or invalid.");
        return;
    }

    const funds = data.funds;
    
    // Update each fund card
    funds.forEach(fund => {
        const symbol = fund.symbol.toLowerCase();
        const valueSpan = document.getElementById(`${symbol}-value`);
        const changeSpan = document.getElementById(`${symbol}-change`);
        const dateSpan = document.getElementById(`${symbol}-date`);

        if (valueSpan && changeSpan && dateSpan) {
            valueSpan.textContent = fund.latest_price.toFixed(4);
            changeSpan.innerHTML = formatChange(fund.daily_change_percent);
            dateSpan.textContent = `更新於 ${fund.date}`;
        } else {
            console.warn(`Could not find elements for fund: ${fund.symbol}`);
        }
    });
}

// Expose the function globally so script.js can call it
window.loadMoneyFundData = loadMoneyFundData;
