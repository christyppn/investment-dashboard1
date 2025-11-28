// money_fund.js - Final Corrected Version

const DATA_BASE_URL = './data/';

// --- Helper Functions ---

async function fetchData(filename) {
    // 確保路徑正確，例如：./data/ai_analysis.json
    const path = DATA_BASE_URL + filename; 
    try {
        const response = await fetch(path);
        
        // 檢查 HTTP 狀態碼
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status} for ${path}`);
            // 如果文件不存在 (404)，返回 null
            if (response.status === 404) {
                return null;
            }
            throw new Error(`Network response was not ok for ${path}`);
        }
        
        // 嘗試解析 JSON
        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Error fetching or parsing ${path}:`, error);
        return null;
    }
}

function formatChange(change) {
    const isPositive = change >= 0;
    const sign = isPositive ? '+' : '';
    const colorClass = isPositive ? 'text-success' : 'text-danger';
    return `<span class="${colorClass}">${sign}${change.toFixed(2)}%</span>`;
}

// --- Data Loading Functions ---

/**
 * Loads and renders the money fund data. This function is called by switchTab in script.js.
 */
async function loadMoneyFundData() {
    const data = await fetchData('money_fund_data.json');
    const container = document.getElementById('money-fund-grid'); // Assuming you have a container with this ID

    if (!container) return;

    if (!data || !data.funds || data.funds.length === 0) {
        container.innerHTML = '<p class="text-danger">多基金對比數據不可用 (money_fund_data.json 缺失或格式錯誤)。</p>';
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
