const DATA_BASE_URL = './data/';

// --- Helper Functions ---

/**
 * Formats a timestamp string (YYYY-MM-DD) into a more readable format.
 * @param {string} timestamp - The timestamp string.
 * @returns {string} Formatted time string.
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return '未知時間';
    // HIBOR timestamp is a full ISO string, extract date only
    const datePart = timestamp.substring(0, 10);
    return `更新時間: ${datePart}`;
}

/**
 * Renders the time series chart for a given symbol.
 * @param {string} symbol - The stock/index symbol.
 * @param {Array} history - Array of historical data points.
 */
function renderChart(symbol, history) {
    const chartData = history.map(item => ({
        x: new Date(item.date).getTime(),
        y: item.close
    }));

    const options = {
        series: [{
            name: symbol,
            data: chartData
        }],
        chart: {
            type: 'area',
            height: 100,
            sparkline: {
                enabled: true
            },
            toolbar: {
                show: false
            }
        },
        stroke: {
            curve: 'smooth',
            width: 2
        },
        xaxis: {
            type: 'datetime',
            labels: {
                show: false
            }
        },
        yaxis: {
            labels: {
                show: false
            }
        },
        tooltip: {
            enabled: true,
            x: {
                format: 'dd MMM'
            },
            y: {
                formatter: function (val) {
                    return val.toFixed(2);
                }
            }
        },
        colors: ['#007bff']
    };

    // Clean symbol for ID matching
    const cleanSymbol = symbol.replace('^', '');
    const chartElement = document.querySelector(`#${cleanSymbol}-chart`);
    
    if (chartElement) {
        // Check if chart exists, if so, update it, otherwise create new
        if (ApexCharts.getChartByID(`${cleanSymbol}-chart`)) {
            ApexCharts.exec(`${cleanSymbol}-chart`, 'updateSeries', [{ data: chartData }]);
        } else {
            const chart = new ApexCharts(chartElement, options);
            chart.render();
        }
    }
}

/**
 * Renders a single market index/ETF card.
 * @param {string} symbol - The stock/index symbol (e.g., 'SPY', 'VIX').
 * @param {string} name - The display name.
 * @param {Array} history - Array of historical data points.
 */
function renderIndexCard(symbol, name, history) {
    // Clean symbol for ID matching (e.g., '^VIX' -> 'VIX')
    const cleanSymbol = symbol.replace('^', '');
    
    const valueEl = document.getElementById(`${cleanSymbol}-value`);
    const changeEl = document.getElementById(`${cleanSymbol}-change`);
    const chartEl = document.getElementById(`${cleanSymbol}-chart`);

    if (!history || history.length === 0) {
        if (valueEl) valueEl.textContent = '--';
        if (changeEl) changeEl.textContent = '無數據';
        if (changeEl) changeEl.className = 'change-percent neutral';
        return;
    }

    const latestData = history[history.length - 1];
    const close = latestData.close;
    const change = latestData.change_percent;

    if (valueEl) valueEl.textContent = close.toFixed(2);
    if (changeEl) changeEl.textContent = (change > 0 ? '+' : '') + change.toFixed(2) + '%';
    
    let changeClass = 'neutral';
    if (change > 0) {
        changeClass = 'positive';
    } else if (change < 0) {
        changeClass = 'negative';
    }
    if (changeEl) changeEl.className = `change-percent ${changeClass}`;

    if (chartEl && history) {
        renderChart(symbol, history);
    }
}

// --- Data Loading Functions ---

async function loadHiborRates() {
    try {
        const response = await fetch(`${DATA_BASE_URL}hibor_rates.json?v=${new Date().getTime()}`);
        const data = await response.json();

        // FIX: The JSON is an array of objects, not a single object.
        // We need to map the array to the required terms.
        const hiborMap = {};
        let latestTimestamp = '未知時間';

        if (Array.isArray(data) && data.length > 0) {
            data.forEach(item => {
                if (item.term && item.rate) {
                    hiborMap[item.term] = item.rate;
                    if (item.timestamp) {
                        latestTimestamp = item.timestamp;
                    }
                }
            });
        }

        if (hiborMap['1M']) {
            document.getElementById('hibor-1m').textContent = (parseFloat(hiborMap['1M'])).toFixed(2) + '%';
            document.getElementById('hibor-3m').textContent = (parseFloat(hiborMap['3M'])).toFixed(2) + '%';
            document.getElementById('hibor-6m').textContent = (parseFloat(hiborMap['6M'])).toFixed(2) + '%';
            document.getElementById('hibor-timestamp').textContent = formatTimestamp(latestTimestamp);
        } else {
            document.getElementById('hibor-1m').textContent = '無數據';
            document.getElementById('hibor-3m').textContent = '無數據';
            document.getElementById('hibor-6m').textContent = '無數據';
            document.getElementById('hibor-timestamp').textContent = '無數據或數據格式錯誤';
        }
    } catch (error) {
        console.error("Error loading HIBOR rates:", error);
        document.getElementById('hibor-timestamp').textContent = '載入失敗';
    }
}

async function loadFearGreedIndex() {
    try {
        const response = await fetch(`${DATA_BASE_URL}market_sentiment_history.json?v=${new Date().getTime()}`);
        const history = await response.json();

        if (history && history.length > 0) {
            const latest = history[history.length - 1];
            document.getElementById('fng-value').textContent = latest.value;
            document.getElementById('fng-sentiment').textContent = latest.sentiment;
            document.getElementById('fng-timestamp').textContent = formatTimestamp(latest.date);

            // Render FNG Chart
            const chartData = history.map(item => ({
                x: new Date(item.date).getTime(),
                y: item.value
            }));

            const options = {
                series: [{
                    name: "F&G Index",
                    data: chartData
                }],
                chart: {
                    type: 'line',
                    height: 150,
                    toolbar: {
                        show: false
                    }
                },
                stroke: {
                    curve: 'smooth',
                    width: 2
                },
                xaxis: {
                    type: 'datetime',
                    labels: {
                        show: false
                    }
                },
                yaxis: {
                    min: 0,
                    max: 100,
                    tickAmount: 4,
                    labels: {
                        formatter: function (val) {
                            return val.toFixed(0);
                        }
                    }
                },
                colors: ['#ff9800']
            };

            const chart = new ApexCharts(document.querySelector("#fng-chart"), options);
            chart.render();
        } else {
            document.getElementById('fng-sentiment').textContent = '無數據';
        }
    } catch (error) {
        console.error("Error loading Fear & Greed Index:", error);
        document.getElementById('fng-sentiment').textContent = '載入失敗';
    }
}

async function loadMarketData() {
    try {
        const response = await fetch(`${DATA_BASE_URL}market_data_history.json?v=${new Date().getTime()}`);
        const marketData = await response.json();

        // --- Market Breadth ---
        renderIndexCard('SPY', 'S&P 500 ETF', marketData['SPY']);
        renderIndexCard('QQQ', 'NASDAQ 100 ETF', marketData['QQQ']);
        renderIndexCard('DIA', 'Dow Jones ETF', marketData['DIA']);
        
        // --- Global Markets and Volatility ---
        // Note: The symbols in marketData are the keys from YAHOO_SYMBOLS in sync_data.py
        renderIndexCard('^VIX', 'VIX 波動率指數', marketData['VIX']);
        renderIndexCard('^HSI', '恒生指數', marketData['HSI']);
        renderIndexCard('^N225', '日經 225 指數', marketData['N225']);

    } catch (error) {
        console.error("Error loading market data:", error);
    }
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    loadHiborRates();
    loadFearGreedIndex();
    loadMarketData();
});

