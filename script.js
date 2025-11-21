// script.js - Main JavaScript for index.html

// --- Configuration ---
const DATA_DIR = "data/";
const HIBOR_TERMS = ["1M", "3M", "6M"];

// Global variable to store the full market data history
let fullMarketData = {};

// --- Helper Functions ---

/**
 * Fetches JSON data from a given path, adding a cache-busting parameter.
 * @param {string} path - The path to the JSON file.
 * @returns {Promise<Object|Array>} The parsed JSON data.
 */
async function fetchData(path) {
    const cacheBuster = new Date().getTime();
    const url = `${DATA_DIR}${path}?t=${cacheBuster}`;
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Could not fetch data from ${url}:`, error);
        return null;
    }
}

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
 * Calculates the cumulative percentage change from a series of daily close prices.
 * @param {Array<Object>} history - The time series data.
 * @returns {Array<Object>} The series with cumulative percentage change.
 */
function calculateCumulativeChange(history) {
    if (!history || history.length === 0) return [];

    const basePrice = history[0].close;
    return history.map(item => ({
        x: new Date(item.date).getTime(),
        y: ((item.close - basePrice) / basePrice) * 100
    }));
}

/**
 * Renders a simple sparkline chart using ApexCharts.
 * @param {string} elementId - The ID of the element to render the chart in.
 * @param {Array<Object>} data - The time series data for the chart.
 * @param {string} colorClass - The class to determine the line color.
 * @param {string} seriesName - Name of the series (Price or % Change).
 * @param {boolean} isPercentage - Whether the y-axis represents percentage.
 */
function renderSparklineChart(elementId, data, colorClass, seriesName = '價格', isPercentage = false) {
    const color = colorClass === 'text-success' ? '#28a745' : '#dc3545';
    
    const options = {
        series: [{
            name: seriesName,
            data: data
        }],
        chart: {
            type: 'area',
            height: 150,
            sparkline: {
                enabled: true
            },
            animations: {
                enabled: false
            }
        },
        stroke: {
            curve: 'smooth',
            width: 2
        },
        colors: [color],
        tooltip: {
            enabled: true,
            x: {
                show: true,
                format: 'dd MMM yyyy' // Show date on hover
            },
            y: {
                formatter: function(value) {
                    return value.toFixed(2) + (isPercentage ? '%' : '');
                }
            }
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
        grid: {
            show: false
        },
        fill: {
            opacity: 0.3,
            type: 'gradient',
            gradient: {
                shade: 'dark',
                type: 'vertical',
                shadeIntensity: 0.5,
                gradientToColors: [color],
                inverseColors: false,
                opacityFrom: 0.5,
                opacityTo: 0,
                stops: [0, 100]
            }
        }
    };

    const chartElement = document.getElementById(elementId);
    if (chartElement) {
        // Clear previous chart instance if exists
        if (chartElement.chart) {
            chartElement.chart.destroy();
        }
        const chart = new ApexCharts(chartElement, options);
        chart.render();
        chartElement.chart = chart; // Store chart instance
    }
}

/**
 * Filters the history data based on the selected period.
 * @param {Array<Object>} history - The full time series data.
 * @param {string} period - The selected period ('1M', '3M', '6M', 'ALL').
 * @returns {Array<Object>} The filtered data.
 */
function filterDataByPeriod(history, period) {
    if (!history || history.length === 0 || period === 'ALL') {
        return history;
    }

    let days;
    switch (period) {
        case '1M':
            days = 21; // Approx 1 month of trading days
            break;
        case '3M':
            days = 63; // Approx 3 months of trading days
            break;
        case '6M':
            days = 126; // Approx 6 months of trading days
            break;
        default:
            days = history.length;
    }

    // Slice from the end to get the latest 'days' data points
    return history.slice(-days);
}

// --- Theme Toggle ---

function toggleTheme() {
    const isDarkMode = document.body.classList.toggle('dark-mode');
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
    document.getElementById('theme-icon').textContent = isDarkMode ? '☀️' : '🌙';
    // Re-render charts to apply dark mode styles if necessary
    if (fullMarketData && Object.keys(fullMarketData).length > 0) {
        // Get current period and chart type from active buttons
        const currentMarketBreadthPeriod = document.querySelector('#market-breadth-container .btn-group:first-child .btn-primary')?.textContent || 'ALL';
        const currentMarketBreadthChartType = document.querySelector('#market-breadth-container .btn-group:last-child .btn-secondary')?.getAttribute('onclick').match(/'(price|percent)'/)?.[1] || 'price';
        
        const currentGlobalMarketsPeriod = document.querySelector('#global-markets-container .btn-group:first-child .btn-primary')?.textContent || 'ALL';
        const currentGlobalMarketsChartType = document.querySelector('#global-markets-container .btn-group:last-child .btn-secondary')?.getAttribute('onclick').match(/'(price|percent)'/)?.[1] || 'price';

        renderMarketBreadth(currentMarketBreadthPeriod, currentMarketBreadthChartType);
        renderGlobalMarkets(currentGlobalMarketsPeriod, currentGlobalMarketsChartType);
    }
}

function applyInitialTheme() {
    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        document.getElementById('theme-icon').textContent = '☀️';
    } else {
        document.getElementById('theme-icon').textContent = '🌙';
    }
    
    const toggleButton = document.getElementById('theme-toggle');
    if (toggleButton) {
        toggleButton.addEventListener('click', toggleTheme);
    }
}

// --- Global Timestamp ---

function renderGlobalTimestamp(marketData) {
    const container = document.getElementById("global-timestamp-container");
    if (!container || !marketData || Object.keys(marketData).length === 0) return;

    // Find the latest date across all symbols
    let latestDate = null;
    for (const symbol in marketData) {
        const history = marketData[symbol];
        if (history && history.length > 0) {
            const dateStr = history[history.length - 1].date;
            const currentDate = new Date(dateStr);
            if (!latestDate || currentDate > latestDate) {
                latestDate = currentDate;
            }
        }
    }

    if (latestDate) {
        const formattedDate = latestDate.toISOString().substring(0, 10);
        container.innerHTML = `<p class="text-muted small mb-0">市場數據更新時間: ${formattedDate}</p>`;
    }
}

// --- HIBOR Rates ---

/**
 * Loads and displays HIBOR rates.
 */
async function loadHiborRates() {
    const hiborData = await fetchData("hibor_rates.json");
    const container = document.getElementById("hibor-rates-container");

    if (!container) return;

    if (!hiborData || hiborData.length === 0) {
        container.innerHTML = "<p class='text-danger'>HIBOR rates data is not available or empty.</p>";
        return;
    }

    let html = "";
    
    // Create a map for quick lookup by term
    const ratesMap = new Map();
    hiborData.forEach(item => {
        if (item.term && HIBOR_TERMS.includes(item.term) && item.rate) {
            if (!ratesMap.has(item.term)) {
                ratesMap.set(item.term, item);
            }
        }
    });

    // Extract the latest timestamp from the available data
    const latestTimestamp = hiborData.reduce((latest, item) => {
        const currentTimestamp = new Date(item.timestamp).getTime();
        return currentTimestamp > latest ? currentTimestamp : latest;
    }, 0);
    
    const formattedTimestamp = latestTimestamp > 0 ? formatTimestamp(new Date(latestTimestamp).toISOString()) : '未知時間';

    // --- New Layout ---
    html += `<p class="text-muted small">${formattedTimestamp}</p>`;
    html += "<div class='row'>";
    
    HIBOR_TERMS.forEach(term => {
        const item = ratesMap.get(term);
        const rate = item ? parseFloat(item.rate).toFixed(3) : "N/A";
        
        html += `
            <div class="col-4 text-center">
                <div class="card p-2 mb-2">
                    <h5 class="card-title mb-0">${term}</h5>
                    <p class="card-text h4 text-primary">${rate}%</p>
                </div>
            </div>
        `;
    });

    html += "</div>";
    container.innerHTML = html;
}

// --- Market Breadth (SPY, QQQ, DIA) ---

/**
 * Renders the Market Breadth section, including the time filter UI.
 * @param {string} period - The selected period ('1M', '3M', '6M', 'ALL').
 * @param {string} chartType - The type of chart to render ('price' or 'percent').
 */
function renderMarketBreadth(period = 'ALL', chartType = 'price') {
    const container = document.getElementById("market-breadth-container");
    const symbols = ["SPY", "QQQ", "DIA"];

    if (!container) return;

    if (!fullMarketData || Object.keys(fullMarketData).length === 0) {
        container.innerHTML = "<p class='text-danger'>Market Breadth data is not available or empty. Please run sync_data.py.</p>";
        return;
    }

    // 1. Render Filter Buttons
    const periods = ['ALL', '1M', '3M', '6M'];
    const chartTypes = [{ key: 'price', label: '價格' }, { key: 'percent', label: '累積漲跌幅' }];

    let filterHtml = '<div class="d-flex justify-content-between mb-3">';
    
    // Time Filter
    filterHtml += '<div class="btn-group" role="group" aria-label="Time Filter">';
    periods.forEach(p => {
        const activeClass = p === period ? 'btn-primary' : 'btn-outline-primary';
        filterHtml += `<button type="button" class="btn ${activeClass}" onclick="window.renderMarketBreadth('${p}', '${chartType}')">${p}</button>`;
    });
    filterHtml += '</div>';

    // Chart Type Filter
    filterHtml += '<div class="btn-group" role="group" aria-label="Chart Type Filter">';
    chartTypes.forEach(t => {
        const activeClass = t.key === chartType ? 'btn-secondary' : 'btn-outline-secondary';
        filterHtml += `<button type="button" class="btn ${activeClass}" onclick="window.renderMarketBreadth('${period}', '${t.key}')">${t.label}</button>`;
    });
    filterHtml += '</div>';

    filterHtml += '</div>';

    // 2. Render Cards and Charts
    let cardsHtml = "<div class='row'>";
    
    symbols.forEach(symbol => {
        const fullHistory = fullMarketData[symbol];
        const history = filterDataByPeriod(fullHistory, period);
        
        if (history && history.length > 0) {
            const latest = history[history.length - 1];
            const change = parseFloat(latest.change_percent).toFixed(2);
            const changeClass = change >= 0 ? 'text-success' : 'text-danger';
            const changeIcon = change >= 0 ? '▲' : '▼';
            
            cardsHtml += `
                <div class="col-md-4 mb-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">${symbol}</h5>
                            <p class="card-text h3 mb-1">${parseFloat(latest.close).toFixed(2)}</p>
                            <p class="card-text ${changeClass}">${changeIcon} ${change}%</p>
                            <div id="chart-market-breadth-${symbol}" style="height: 150px;"></div>
                        </div>
                    </div>
                </div>
            `;
            
            // Prepare data for ApexCharts
            let seriesData;
            let seriesName;
            let isPercentage;

            if (chartType === 'percent') {
                seriesData = calculateCumulativeChange(history);
                seriesName = '累積漲跌幅';
                isPercentage = true;
            } else {
                seriesData = history.map(item => ({
                    x: new Date(item.date).getTime(),
                    y: item.close
                }));
                seriesName = '價格';
                isPercentage = false;
            }

            // Render chart after the HTML is inserted
            setTimeout(() => {
                renderSparklineChart(`chart-market-breadth-${symbol}`, seriesData, changeClass, seriesName, isPercentage);
            }, 0);

        } else {
            cardsHtml += `
                <div class="col-md-4 mb-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">${symbol}</h5>
                            <p class="text-warning">Data not found for this period.</p>
                        </div>
                    </div>
                </div>
            `;
        }
    });

    cardsHtml += "</div>";

    // Update the container content
    container.innerHTML = filterHtml + cardsHtml;
}

// --- Global Markets and Volatility ---

/**
 * Renders the Global Markets section, including the time filter UI.
 * @param {string} period - The selected period ('1M', '3M', '6M', 'ALL').
 * @param {string} chartType - The type of chart to render ('price' or 'percent').
 */
function renderGlobalMarkets(period = 'ALL', chartType = 'price') {
    const container = document.getElementById("global-markets-container");
    const symbols = ["VIX", "HSI", "N225"];
    const symbolMap = {
        "VIX": "VIX 波動率指數",
        "HSI": "恒生指數",
        "N225": "日經 225 指數"
    };

    if (!container) return;

    if (!fullMarketData || Object.keys(fullMarketData).length === 0) {
        container.innerHTML = "<p class='text-danger'>Global Markets data is not available or empty. Please run sync_data.py.</p>";
        return;
    }

    // 1. Render Filter Buttons
    const periods = ['ALL', '1M', '3M', '6M'];
    const chartTypes = [{ key: 'price', label: '價格' }, { key: 'percent', label: '累積漲跌幅' }];

    let filterHtml = '<div class="d-flex justify-content-between mb-3">';
    
    // Time Filter
    filterHtml += '<div class="btn-group" role="group" aria-label="Time Filter">';
    periods.forEach(p => {
        const activeClass = p === period ? 'btn-primary' : 'btn-outline-primary';
        filterHtml += `<button type="button" class="btn ${activeClass}" onclick="window.renderGlobalMarkets('${p}', '${chartType}')">${p}</button>`;
    });
    filterHtml += '</div>';

    // Chart Type Filter
    filterHtml += '<div class="btn-group" role="group" aria-label="Chart Type Filter">';
    chartTypes.forEach(t => {
        const activeClass = t.key === chartType ? 'btn-secondary' : 'btn-outline-secondary';
        filterHtml += `<button type="button" class="btn ${activeClass}" onclick="window.renderGlobalMarkets('${period}', '${t.key}')">${t.label}</button>`;
    });
    filterHtml += '</div>';

    filterHtml += '</div>';

    // 2. Render Cards and Charts
    let cardsHtml = "<div class='row'>";
    
    symbols.forEach(symbol => {
        const fullHistory = fullMarketData[symbol];
        const history = filterDataByPeriod(fullHistory, period);
        const fullName = symbolMap[symbol] || symbol;
        
        if (history && history.length > 0) {
            const latest = history[history.length - 1];
            const change = parseFloat(latest.change_percent).toFixed(2);
            const changeClass = change >= 0 ? 'text-success' : 'text-danger';
            const changeIcon = change >= 0 ? '▲' : '▼';
            
            cardsHtml += `
                <div class="col-md-4 mb-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">${symbol} - ${fullName}</h5>
                            <p class="card-text h3 mb-1">${parseFloat(latest.close).toFixed(2)}</p>
                            <p class="card-text ${changeClass}">${changeIcon} ${change}%</p>
                            <div id="chart-global-markets-${symbol}" style="height: 150px;"></div>
                        </div>
                    </div>
                </div>
            `;
            
            // Prepare data for ApexCharts
            let seriesData;
            let seriesName;
            let isPercentage;

            if (chartType === 'percent') {
                seriesData = calculateCumulativeChange(history);
                seriesName = '累積漲跌幅';
                isPercentage = true;
            } else {
                seriesData = history.map(item => ({
                    x: new Date(item.date).getTime(),
                    y: item.close
                }));
                seriesName = '價格';
                isPercentage = false;
            }

            // Render chart after the HTML is inserted
            setTimeout(() => {
                renderSparklineChart(`chart-global-markets-${symbol}`, seriesData, changeClass, seriesName, isPercentage);
            }, 0);

        } else {
            cardsHtml += `
                <div class="col-md-4 mb-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">${symbol} - ${fullName}</h5>
                            <p class="text-warning">Data not found for this period.</p>
                        </div>
                    </div>
                </div>
            `;
        }
    });

    cardsHtml += "</div>";

    // Update the container content
    container.innerHTML = filterHtml + cardsHtml;
}

// --- Fear & Greed Index ---

/**
 * Loads and displays the Fear & Greed Index.
 */
async function loadFearGreedIndex() {
    const sentimentData = await fetchData("market_sentiment_history.json");
    const container = document.getElementById("fear-greed-container");

    if (!container) return;

    if (!sentimentData || sentimentData.length === 0) {
        container.innerHTML = "<p class='text-danger'>Fear & Greed Index data is not available or empty.</p>";
        return;
    }

    // Get the latest data point
    const latest = sentimentData[sentimentData.length - 1];
    const value = latest.value;
    const sentiment = latest.sentiment;
    const formattedTimestamp = formatTimestamp(latest.date);

    let colorClass;
    if (sentiment.includes("Extreme Fear")) {
        colorClass = "bg-danger";
    } else if (sentiment.includes("Fear")) {
        colorClass = "bg-warning";
    } else if (sentiment.includes("Neutral")) {
        colorClass = "bg-info";
    } else if (sentiment.includes("Greed")) {
        colorClass = "bg-success";
    } else if (sentiment.includes("Extreme Greed")) {
        colorClass = "bg-primary";
    } else {
        colorClass = "bg-secondary";
    }

    // --- New Layout ---
    const html = `
        <div class="card text-white ${colorClass} mb-3">
            <div class="card-header">Fear & Greed Index</div>
            <div class="card-body text-center">
                <h1 class="card-title display-3">${value}</h1>
                <p class="card-text h4">${sentiment}</p>
                <p class="card-text small">${formattedTimestamp}</p>
            </div>
        </div>
        <div id="fear-greed-chart" style="height: 200px;"></div>
    `;
    container.innerHTML = html;

    // Prepare data for ApexCharts
    const seriesData = sentimentData.map(item => ({
        x: new Date(item.date).getTime(),
        y: item.value
    }));

    // Render chart
    renderFearGreedChart("fear-greed-chart", seriesData);
}

/**
 * Renders the Fear & Greed Index chart.
 */
function renderFearGreedChart(elementId, data) {
    const options = {
        series: [{
            name: 'Index Value',
            data: data
        }],
        chart: {
            type: 'line',
            height: 200,
            toolbar: {
                show: false
            },
            zoom: {
                enabled: false
            }
        },
        stroke: {
            curve: 'smooth',
            width: 3
        },
        colors: ['#007bff'], // Blue color for the line
        xaxis: {
            type: 'datetime',
            tooltip: {
                enabled: true,
                format: 'dd MMM yyyy' // Show date on hover
            }
        },
        yaxis: {
            min: 0,
            max: 100,
            tickAmount: 5,
            labels: {
                formatter: function(value) {
                    return value.toFixed(0);
                }
            }
        },
        tooltip: {
            x: {
                format: 'dd MMM yyyy'
            }
        },
        grid: {
            borderColor: '#f1f1f1',
        },
        annotations: {
            yaxis: [
                { y: 25, borderColor: '#dc3545', label: { borderColor: '#dc3545', style: { color: '#fff', background: '#dc3545' }, text: 'Extreme Fear' } },
                { y: 45, borderColor: '#ffc107', label: { borderColor: '#ffc107', style: { color: '#000', background: '#ffc107' }, text: 'Fear' } },
                { y: 55, borderColor: '#17a2b8', label: { borderColor: '#17a2b8', style: { color: '#fff', background: '#17a2b8' }, text: 'Neutral' } },
                { y: 75, borderColor: '#28a745', label: { borderColor: '#28a745', style: { color: '#fff', background: '#28a745' }, text: 'Greed' } },
                { y: 100, borderColor: '#007bff', label: { borderColor: '#007bff', style: { color: '#fff', background: '#007bff' }, text: 'Extreme Greed' } }
            ]
        }
    };

    const chartElement = document.getElementById(elementId);
    if (chartElement) {
        const chart = new ApexCharts(chartElement, options);
        chart.render();
    }
}


// --- Initialization ---

/**
 * Main function to load all data and render the dashboard.
 */
async function initDashboard() {
    // Apply theme first
    applyInitialTheme();

    // Fetch market data first and store it globally
    const marketData = await fetchData("market_data_history.json");
    if (marketData && Object.keys(marketData).length > 0) {
        fullMarketData = { ...fullMarketData, ...marketData };
        renderGlobalTimestamp(fullMarketData);
    } else {
        console.error("FATAL ERROR: market_data_history.json is empty or failed to load. Cannot render Market Breadth or Global Markets.");
    }

    loadHiborRates();
    loadFearGreedIndex();
    
    // Make render functions globally accessible for onclick events
    window.renderMarketBreadth = renderMarketBreadth;
    window.renderGlobalMarkets = renderGlobalMarkets;

    // Initial render with 'ALL' data
    renderMarketBreadth('ALL');
    renderGlobalMarkets('ALL');
}

// Run the initialization when the document is ready
document.addEventListener("DOMContentLoaded", initDashboard);
