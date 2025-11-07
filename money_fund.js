const DATA_BASE_URL = './data/';

// List of Sector ETFs to display on this page
const SECTOR_ETFS = [
    { symbol: "XLK", name: "科技 (Technology)" },
    { symbol: "XLC", name: "通訊服務 (Communication Services)" },
    { symbol: "XLY", name: "非必需消費品 (Consumer Discretionary)" },
    { symbol: "XLP", name: "必需消費品 (Consumer Staples)" },
    { symbol: "XLV", name: "醫療保健 (Health Care)" },
    { symbol: "XLF", name: "金融 (Financial)" },
    { symbol: "XLE", name: "能源 (Energy)" },
    { symbol: "XLI", name: "工業 (Industrial)" },
    { symbol: "XLB", name: "材料 (Materials)" },
    { symbol: "XLU", name: "公用事業 (Utilities)" },
    { symbol: "VNQ", name: "房地產 (Real Estate)" },
    { symbol: "GLD", name: "黃金 (Gold)" },
    { symbol: "ROBO", name: "機器人/自動化 (Robotics)" },
    { symbol: "SMH", name: "半導體 (Semiconductors)" },
    { symbol: "IWM", name: "羅素2000 (Small Cap)" },
];

/**
 * Creates and appends a fund flow card to the container.
 * @param {string} symbol - The ETF symbol.
 * @param {string} name - The ETF name.
 * @param {Object} data - The latest data point for the ETF.
 */
function createFundFlowCard(symbol, name, data) {
    const container = document.getElementById('fund-flow-container');
    const card = document.createElement('div');
    card.className = 'flow-card';

    let valueText = '--';
    let changeText = '無數據';
    let changeClass = 'neutral';

    if (data && data.volume_change_percent !== undefined) {
        const change = data.volume_change_percent;
        valueText = data.volume.toLocaleString(); // Display raw volume
        changeText = (change > 0 ? '+' : '') + change.toFixed(2) + '%';
        changeClass = change > 0 ? 'positive' : (change < 0 ? 'negative' : 'neutral');
    }

    card.innerHTML = `
        <div class="flow-header">${symbol} - ${name}</div>
        <div class="flow-value">${valueText}</div>
        <div class="flow-change ${changeClass}">${changeText}</div>
        <p style="font-size: 0.8em; color: #666; margin-top: 10px;">成交量 (Volume)</p>
    `;

    container.appendChild(card);
}

/**
 * Loads and displays fund flow data.
 */
async function loadFundFlowData() {
    try {
        // Use cache-busting to ensure the latest file is fetched
        const response = await fetch(`${DATA_BASE_URL}market_data_history.json?v=${new Date().getTime()}`);
        const marketData = await response.json();

        SECTOR_ETFS.forEach(etf => {
            const history = marketData[etf.symbol];
            // We only need the latest data point for the card
            const latestData = history && history.length > 0 ? history[history.length - 1] : null;
            
            createFundFlowCard(etf.symbol, etf.name, latestData);
        });

    } catch (error) {
        console.error("Error loading fund flow data:", error);
        const container = document.getElementById('fund-flow-container');
        container.innerHTML = `<p style="color: red;">數據載入失敗，請檢查 market_data_history.json 文件和控制台錯誤。</p>`;
    }
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    loadFundFlowData();
});
