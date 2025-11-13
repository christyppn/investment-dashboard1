// script.js - Main JavaScript for index.html

// --- Configuration ---
const DATA_DIR = "data/";
const HIBOR_TERMS = ["1M", "3M", "6M"];

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
 * Renders a simple sparkline chart using ApexCharts.
 * @param {string} elementId - The ID of the element to render the chart in.
 * @param {Array<Object>} data - The time series data for the chart.
 * @param {string} colorClass - The class to determine the line color.
 */
function renderSparklineChart(elementId, data, colorClass) {
    const color = colorClass === 'text-success' ? '#28a745' : '#dc3545';
    
    const options = {
        series: [{
            name: 'Price',
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
                show: false
            },
            y: {
                formatter: function(value) {
                    return value.toFixed(2);
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
        const chart = new ApexCharts(chartElement, options);
        chart.render();
    }
}


// --- HIBOR Rates ---

/**
 * Loads and displays HIBOR rates.
 * Assumes hibor_rates.json is an array of objects: [{id, term, rate, timestamp}, ...]
 */
async function loadHiborRates() {
    const hiborData = await fetchData("hibor_rates.json");
    const container = document.getElementById("hibor-rates-container"); // Assuming a new container for the new layout

    // Fallback to old IDs if container is not found (for compatibility)
    const fallback1M = document.getElementById('hibor-1m');
    const fallback3M = document.getElementById('hibor-3m');
    const fallback6M = document.getElementById('hibor-6m');
    const fallbackTimestamp = document.getElementById('hibor-timestamp');

    if (!hiborData || hiborData.length === 0) {
        const msg = "HIBOR rates data is not available or empty.";
        if (container) container.innerHTML = `<p class='text-danger'>${msg}</p>`;
        if (fallback1M) fallback1M.textContent = '無數據';
        if (fallbackTimestamp) fallbackTimestamp.textContent = '無數據或數據格式錯誤';
        return;
    }

    let html = "";
    
    // Create a map for quick lookup by term
    const ratesMap = new Map();
    hiborData.forEach(item => {
        // Ensure the rate is a number and the term is valid
        if (item.term && HIBOR_TERMS.includes(item.term) && item.rate) {
            // The sync script ensures we only have the latest for each term, but we'll take the first one we see
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

    // --- New Layout (Preferred) ---
    if (container) {
        html += `<p class="text-muted small">${formattedTimestamp}</p>`;
        html += "<div class='row'>";
        
        HIBOR_TERMS.forEach(term => {
            const item = ratesMap.get(term);
            // The rate is already a percentage in the JSON from the Python script
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

    // --- Old Layout (Fallback) ---
    if (fallback1M) {
        const rate1M = ratesMap.get('1M');
        const rate3M = ratesMap.get('3M');
        const rate6M = ratesMap.get('6M');

        fallback1M.textContent = rate1M ? parseFloat(rate1M.rate).toFixed(3) + '%' : '無數據';
        fallback3M.textContent = rate3M ? parseFloat(rate3M.rate).toFixed(3) + '%' : '無數據';
        fallback6M.textContent = rate6M ? parseFloat(rate6M.rate).toFixed(3) + '%' : '無數據';
        fallbackTimestamp.textContent = formattedTimestamp;
    }
}

// --- Market Breadth (SPY, QQQ, DIA) ---

/**
 * Loads and displays Market Breadth data (SPY, QQQ, DIA) with charts.
 * Assumes market_data_history.json is an object: { "SPY": [history], "QQQ": [history], ... }
 */
async function loadMarketBreadth() {
    const marketData = await fetchData("market_data_history.json");
    const container = document.getElementById("market-breadth-container"); // Assuming a new container
    const symbols = ["SPY", "QQQ", "DIA"];

    if (!marketData || Object.keys(marketData).length === 0) {
        if (container) container.innerHTML = "<p class='text-danger'>Market Breadth data is not available or empty.</p>";
        // Fallback for old layout
        symbols.forEach(symbol => {
            const cleanSymbol = symbol.replace('^', '');
            const valueEl = document.getElementById(`${cleanSymbol}-value`);
            const changeEl = document.getElementById(`${cleanSymbol}-change`);
            if (valueEl) valueEl.textContent = '--';
            if (changeEl) changeEl.textContent = '無數據';
        });
        return;
    }

    let html = "<div class='row'>";
    
    symbols.forEach(symbol => {
        const history = marketData[symbol];
        
        // --- New Layout (Preferred) ---
        if (container) {
            if (history && history.length > 0) {
                const latest = history[history.length - 1];
                const change = parseFloat(latest.change_percent).toFixed(2);
                const changeClass = change >= 0 ? 'text-success' : 'text-danger';
                const changeIcon = change >= 0 ? '▲' : '▼';
                
                html += `
                    <div class="col-md-4 mb-4">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">${symbol}</h5>
                                <p class="card-text h3 mb-1">${parseFloat(latest.close).toFixed(2)}</p>
                                <p class="card-text ${changeClass}">${changeIcon} ${change}%</p>
                                <div id="chart-${symbol}" style="height: 150px;"></div>
                            </div>
                        </div>
                    </div>
                `;
                
                // Prepare data for ApexCharts
                const seriesData = history.map(item => ({
                    x: new Date(item.date).getTime(),
                    y: item.close
                }));

                // Render chart after the HTML is inserted (in the main init function)
                setTimeout(() => {
                    renderSparklineChart(`chart-${symbol}`, seriesData, changeClass);
                }, 0);

            } else {
                html += `
                    <div class="col-md-4 mb-4">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">${symbol}</h5>
                                <p class="text-warning">Data not found.</p>
                            </div>
                        </div>
                    </div>
                `;
            }
        }

        // --- Old Layout (Fallback) ---
        const cleanSymbol = symbol.replace('^', '');
        const valueEl = document.getElementById(`${cleanSymbol}-value`);
        const changeEl = document.getElementById(`${cleanSymbol}-change`);
        const chartEl = document.getElementById(`${cleanSymbol}-chart`);

        if (history && history.length > 0) {
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

            // The original renderChart function is complex, using the new sparkline function instead
            if (chartEl) {
                const seriesData = history.map(item => ({
                    x: new Date(item.date).getTime(),
                    y: item.close
                }));
                const changeClass = change >= 0 ? 'text-success' : 'text-danger';
                // Need to ensure the chart element is empty before rendering
                chartEl.innerHTML = ''; 
                renderSparklineChart(chartEl.id, seriesData, changeClass);
            }
        } else {
            if (valueEl) valueEl.textContent = '--';
            if (changeEl) changeEl.textContent = '無數據';
            if (changeEl) changeEl.className = 'change-percent neutral';
        }
    });

    if (container) {
        html += "</div>";
        container.innerHTML = html;
    }
}

// --- Fear & Greed Index ---

/**
 * Loads and displays the Fear & Greed Index.
 * Assumes market_sentiment_history.json is an array of objects: [{date, value, sentiment}, ...]
 */
async function loadFearGreedIndex() {
    const sentimentData = await fetchData("market_sentiment_history.json");
    const container = document.getElementById("fear-greed-container");
    const fallbackValue = document.getElementById('fng-value');
    const fallbackSentiment = document.getElementById('fng-sentiment');
    const fallbackTimestamp = document.getElementById('fng-timestamp');

    if (!sentimentData || sentimentData.length === 0) {
        if (container) container.innerHTML = "<p class='text-danger'>Fear & Greed Index data is not available or empty.</p>";
        if (fallbackSentiment) fallbackSentiment.textContent = '無數據';
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

    // --- New Layout (Preferred) ---
    if (container) {
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

    // --- Old Layout (Fallback) ---
    if (fallbackValue) fallbackValue.textContent = value;
    if (fallbackSentiment) fallbackSentiment.textContent = sentiment;
    if (fallbackTimestamp) fallbackTimestamp.textContent = formattedTimestamp;
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
                enabled: false
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
                format: 'dd MMM'
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
function initDashboard() {
    loadHiborRates();
    loadFearGreedIndex();
    loadMarketBreadth();
}

// Run the initialization when the document is ready
document.addEventListener("DOMContentLoaded", initDashboard);
