const DATA_BASE_URL = './data/';

const SECTOR_ETFS = [
    { symbol: 'XLK', name: '科技 (Technology)' },
    { symbol: 'XLC', name: '通訊服務 (Communication Services)' },
    { symbol: 'XLY', name: '非必需消費 (Consumer Discretionary)' },
    { symbol: 'XLP', name: '必需消費 (Consumer Staples)' },
    { symbol: 'XLV', name: '醫療保健 (Health Care)' },
    { symbol: 'XLF', name: '金融 (Financial)' },
    { symbol: 'XLE', name: '能源 (Energy)' },
    { symbol: 'XLI', name: '工業 (Industrial)' },
    { symbol: 'XLB', name: '原材料 (Materials)' },
    { symbol: 'XLU', name: '公用事業 (Utilities)' },
    { symbol: 'VNQ', name: '房地產 (Real Estate)' },
    { symbol: 'GLD', name: '黃金 (Gold)' },
    { symbol: 'ROBO', name: '機器人 (Robotics)' },
    { symbol: 'SMH', name: '半導體 (Semiconductors)' },
    { symbol: 'IWM', name: '羅素2000 (Small Cap)' },
];

/**
 * Creates and appends a fund flow card to the container.
 * @param {string} symbol - ETF symbol.
 * @param {string} name - ETF name.
 * @param {object} latestData - Object containing latest volume_change_percent.
 */
function createFundFlowCard(symbol, name, latestData) {
    const container = document.getElementById('fund-flow-container');
    if (!container) return;

    const card = document.createElement('div');
    card.className = 'card fund-flow-card';

    let changePercent = '--';
    let changeClass = 'neutral';
    let flowText = '無數據';

    if (latestData && latestData.volume_change_percent !== undefined) {
        changePercent = latestData.volume_change_percent.toFixed(2) + '%';
        const change = latestData.volume_change_percent;

        if (change > 0) {
            changeClass = 'positive';
            flowText = '資金流入';
        } else if (change < 0) {
            changeClass = 'negative';
            flowText = '資金流出';
        } else {
            flowText = '持平';
        }
    }

    card.innerHTML = `
        <div class="card-header">
            <span class="symbol">${symbol}</span>
            <span class="name">${name}</span>
        </div>
        <div class="card-body">
            <div class="current-value ${changeClass}">${changePercent}</div>
            <div class="flow-status">${flowText}</div>
        </div>
    `;

    container.appendChild(card);
}

/**
 * Loads and renders fund flow data.
 */
async function loadFundFlowData() {
    try {
        const response = await fetch(`${DATA_BASE_URL}market_data_history.json?v=${new Date().getTime()}`);
        const marketData = await response.json();

        const container = document.getElementById('fund-flow-container');
        if (!container) return;
        
        // Clear loading message
        container.innerHTML = '';

        let hasData = false;
        SECTOR_ETFS.forEach(etf => {
            const history = marketData[etf.symbol];
            // We only need the latest data point for the card
            const latestData = history && history.length > 0 ? history[history.length - 1] : null;
            
            createFundFlowCard(etf.symbol, etf.name, latestData);
            if (latestData) hasData = true;
        });

        if (!hasData) {
            container.innerHTML = `<p style="color: #6c757d; text-align: center; width: 100%;">
                市場數據載入成功，但所有板塊數據均為空。請檢查 sync_data.py 運行日誌。
            </p>`;
        }

    } catch (error) {
        console.error("Error loading fund flow data:", error);
        const container = document.getElementById('fund-flow-container');
        container.innerHTML = `<p style="color: red; text-align: center; width: 100%;">
            數據載入失敗，請檢查 market_data_history.json 文件和控制台錯誤。
        </p>`;
    }
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    loadFundFlowData();
});

