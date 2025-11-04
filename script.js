const DATA_BASE_URL = './data/';

// --- Helper Functions ---

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
 * Renders an ApexChart.
 * (This function is kept simple as the main rendering logic is now in renderIndexCard)
 */
function renderChart(elementId, series, categories, title, yAxisTitle, showLabels = true) {
    const options = {
        series: series,
        chart: {
            type: 'line',
            height: showLabels ? 250 : 100,
            sparkline: { enabled: !showLabels }
        },
        title: {
            text: title,
            align: 'left',
            style: { fontSize: '14px' }
        },
        xaxis: {
            categories: categories,
            labels: { show: showLabels },
            tooltip: { enabled: false }
        },
        yaxis: {
            title: { text: yAxisTitle },
            labels: { show: showLabels }
        },
        stroke: {
            curve: 'smooth',
            width: 2
        },
        tooltip: {
            x: { show: showLabels },
            y: {
                formatter: function(val) {
                    return val.toFixed(2) + (yAxisTitle.includes('%') ? '%' : '');
                }
            }
        },
        grid: {
            show: showLabels,
            padding: { left: 0, right: 0 }
        }
    };

    // Check if chart exists, if so, update it, otherwise create new
    if (ApexCharts.getChartByID(elementId)) {
        ApexCharts.exec(elementId, 'updateOptions', options);
    } else {
        const chart = new ApexCharts(document.getElementById(elementId), options);
        chart.render();
    }
}

/**
 * Sets the current value and change percentage for a card, including color coding.
 * @param {string} valueId - ID of the element for the current value.
 * @param {string} changeId - ID of the element for the change percentage.
 * @param {number} value - The current value.
 * @param {number} change - The change percentage.
 */
function setCardData(valueId, changeId, value, change) {
    const valueEl = document.getElementById(valueId);
    const changeEl = document.getElementById(changeId);

    if (valueEl) {
        valueEl.textContent = value.toFixed(2);
    }

    if (changeEl) {
        changeEl.textContent = (change > 0 ? '+' : '') + change.toFixed(2) + '%';
        changeEl.className = 'change-percent ' + (change > 0 ? 'positive' : (change < 0 ? 'negative' : 'neutral'));
    }
}

// --- Data Loading Functions ---

/**
 * Loads and displays HIBOR rates.
 */
async function loadHiborRates() {
    try {
        const response = await fetch(`${DATA_BASE_URL}hibor_rates.json?v=${new Date().getTime()}`);
        const data = await response.json();

        document.getElementById('hibor-1m').textContent = `${data.ir_1m}%`;
        document.getElementById('hibor-3m').textContent = `${data.ir_3m}%`;
        document.getElementById('hibor-6m').textContent = `${data.ir_6m}%`;
        document.getElementById('hibor-timestamp').textContent = formatTimestamp(data.date);

    } catch (error) {
        console.error("Error loading HIBOR rates:", error);
    }
}

/**
 * Loads and displays Fear & Greed Index data.
 */
async function loadFearGreedIndex() {
    try {
        const response = await fetch(`${DATA_BASE_URL}market_sentiment_history.json?v=${new Date().getTime()}`);
        const historyData = await response.json();

        if (historyData && historyData.length > 0) {
            const latest = historyData[historyData.length - 1];
            document.getElementById('fng-value').textContent = latest.value;
            document.getElementById('fng-sentiment').textContent = latest.sentiment;
            document.getElementById('fng-timestamp').textContent = formatTimestamp(latest.date);

            const categories = historyData.map(d => d.date);
            const seriesData = historyData.map(d => d.value);

            renderChart('fng-chart', [{ name: '指數分數', data: seriesData }], categories, '30天趨勢', '指數分數', true);
        }
    } catch (error) {
        console.error("Error loading Fear & Greed Index:", error);
    }
}

/**
 * Renders a single index card (SPY, QQQ, DIA, VIX, HSI, N225).
 * @param {string} symbol - The stock/index symbol (e.g., 'SPY', '^VIX').
 * @param {string} name - The display name.
 * @param {Array<Object>} data - The 30-day historical data.
 */
function renderIndexCard(symbol, name, data) {
    // Clean symbol for element IDs (e.g., '^VIX' -> 'vix')
    const cleanSymbol = symbol.toLowerCase().replace('^', '');
    
    // Fallback for missing data
    if (!data || data.length === 0) {
        console.warn(`No data for ${symbol}`);
        document.getElementById(`${cleanSymbol}-value`).textContent = '--';
        document.getElementById(`${cleanSymbol}-change`).textContent = '無數據';
        document.getElementById(`${cleanSymbol}-change`).className = 'change-percent neutral';
        return;
    }

    const latest = data[data.length - 1];
    const categories = data.map(d => d.date);
    const seriesData = data.map(d => d.close);

    // 1. Update value and change percentage
    setCardData(`${cleanSymbol}-value`, `${cleanSymbol}-change`, latest.close, latest.change_percent);

    // 2. Render the sparkline chart
    const chartId = `${cleanSymbol}-chart`;
    const options = {
        chart: {
            type: 'line',
            height: 100,
            sparkline: { enabled: true }
        },
        series: [{
            name: name,
            data: seriesData
        }],
        xaxis: {
            categories: categories,
        },
        stroke: {
            width: 2,
            curve: 'smooth'
        },
        colors: [latest.change_percent >= 0 ? '#4CAF50' : '#F44336'], // Color based on latest change
        tooltip: {
            enabled: true,
            x: { show: false },
            y: {
                formatter: function(val) {
                    return val.toFixed(2);
                }
            }
        }
    };

    // Check if chart exists, if so, update it, otherwise create new
    if (ApexCharts.getChartByID(chartId)) {
        ApexCharts.exec(chartId, 'updateOptions', options);
    } else {
        const chart = new ApexCharts(document.getElementById(chartId), options);
        chart.render();
    }
}

/**
 * Loads and displays all market data (SPY, QQQ, DIA, VIX, HSI, N225).
 */
async function loadMarketData() {
    try {
        // Use cache-busting to ensure the latest file is fetched
        const response = await fetch(`${DATA_BASE_URL}market_data_history.json?v=${new Date().getTime()}`);
        const marketData = await response.json();

        // --- Market Breadth (US Indices) ---
        renderIndexCard('SPY', 'S&P 500 ETF', marketData['SPY']);
        renderIndexCard('QQQ', 'NASDAQ 100 ETF', marketData['QQQ']);
        renderIndexCard('DIA', 'Dow Jones ETF', marketData['DIA']);
        
        // --- Global Indices and Volatility ---
        renderIndexCard('^VIX', 'VIX 波動率指數', marketData['^VIX']);
        renderIndexCard('^HSI', '恒生指數', marketData['^HSI']);
        renderIndexCard('^N225', '日經 225 指數', marketData['^N225']);

    } catch (error) {
        console.error("Error loading market data:", error);
    }
}

/**
 * Loads and displays money fund data.
 */
async function loadMoneyFundData() {
    try {
        const response = await fetch(`${DATA_BASE_URL}money_fund_data.json?v=${new Date().getTime()}`);
        const data = await response.json();

        // This function is typically for the money_fund.html page, 
        // but we keep the structure for completeness.
        console.log("Money Fund Data Loaded (for money_fund.html):", data);

    } catch (error) {
        console.error("Error loading money fund data:", error);
    }
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    loadHiborRates();
    loadFearGreedIndex();
    loadMarketData();
    // loadMoneyFundData(); // Only needed for money_fund.html
});
