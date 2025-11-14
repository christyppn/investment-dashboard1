// fund_flow.js - JavaScript for fund_flow.html

// --- Configuration ---
const DATA_DIR = "data/";
// Map of ETF symbols to their full names in Chinese/English
const SECTOR_ETFS_MAP = {
    "XLK": "科技 (Technology)",
    "XLC": "通訊服務 (Communication Services)",
    "XLY": "非必需消費 (Consumer Discretionary)",
    "XLP": "必需消費 (Consumer Staples)",
    "XLV": "醫療保健 (Health Care)",
    "XLF": "金融 (Financial)",
    "XLE": "能源 (Energy)",
    "XLI": "工業 (Industrial)",
    "XLB": "原材料 (Materials)",
    "XLU": "公用事業 (Utilities)",
    "VNQ": "房地產 (Real Estate)",
    "GLD": "黃金 (Gold)",
    "ROBO": "機器人 (Robotics)",
    "SMH": "半導體 (Semiconductors)",
    "IWM": "羅素2000 (Small Cap)"
};
const SECTOR_ETFS = Object.keys(SECTOR_ETFS_MAP);

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
 * Renders a simple bar chart for volume change using ApexCharts.
 * @param {string} elementId - The ID of the element to render the chart in.
 * @param {Array<Object>} data - The time series data for the chart.
 */
function renderVolumeChangeChart(elementId, data) {
    // Filter out data points where volume_change_percent is missing or null
    const validData = data.filter(item => item.volume_change_percent !== null && item.volume_change_percent !== undefined);
    
    const dates = validData.map(item => item.date);
    const volumeChanges = validData.map(item => item.volume_change_percent);
    
    const options = {
        series: [{
            name: 'Volume Change %',
            data: volumeChanges
        }],
        chart: {
            type: 'bar',
            height: 150,
            toolbar: {
                show: false
            },
            sparkline: {
                enabled: true
            }
        },
        // Set colors based on the value of the bar
        colors: volumeChanges.map(change => change >= 0 ? '#28a745' : '#dc3545'), 
        plotOptions: {
            bar: {
                columnWidth: '80%',
                colors: {
                    ranges: [{
                        from: -Infinity,
                        to: 0,
                        color: '#dc3545' // Red for negative
                    }, {
                        from: 0,
                        to: Infinity,
                        color: '#28a745' // Green for positive
                    }]
                }
            }
        },
        xaxis: {
            categories: dates,
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
                show: true,
                formatter: function(val) {
                    return val;
                }
            },
            y: {
                formatter: function(val) {
                    return val.toFixed(2) + '%';
                }
            }
        },
        grid: {
            show: false
        }
    };

    const chartElement = document.getElementById(elementId);
    if (chartElement) {
        const chart = new ApexCharts(chartElement, options);
        chart.render();
    }
}

// --- Main Function ---

/**
 * Loads and displays Fund Flow data (Sector ETFs).
 * Assumes market_data_history.json is an object: { "XLK": [history], "XLC": [history], ... }
 */
async function loadFundFlowData() {
    const marketData = await fetchData("market_data_history.json");
    const container = document.getElementById("fund-flow-container");

    if (!container) {
        console.error("Fund flow container not found.");
        return;
    }

    if (!marketData || Object.keys(marketData).length === 0) {
        container.innerHTML = "<p class='text-danger'>資金流向數據不可用或為空。請檢查 `market_data_history.json` 文件。</p>";
        return;
    }

    let html = `
        <p class="text-muted small">數據來源：Yahoo Finance (yfinance) - 過去 30 個交易日的成交量變化</p>
        <div class="row">
    `;
    
    SECTOR_ETFS.forEach(symbol => {
        const history = marketData[symbol];
        const fullName = SECTOR_ETFS_MAP[symbol] || symbol; // Get the full name
        
        if (history && history.length > 0) {
            const latest = history[history.length - 1];
            // Ensure volume_change_percent exists and is a number
            const volumeChange = latest.volume_change_percent !== undefined && latest.volume_change_percent !== null 
                               ? parseFloat(latest.volume_change_percent).toFixed(2) 
                               : 'N/A';
            
            const isNumeric = volumeChange !== 'N/A';
            const changeClass = isNumeric ? (parseFloat(volumeChange) >= 0 ? 'text-success' : 'text-danger') : 'text-muted';
            const changeIcon = isNumeric ? (parseFloat(volumeChange) >= 0 ? '▲' : '▼') : '';
            
            // Get the last 10 days of data for the sparkline chart
            const chartData = history.slice(-10);

            html += `
                <div class="col-lg-3 col-md-4 col-sm-6 mb-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title mb-1">${symbol} - ${fullName}</h5>
                            <p class="card-text small text-muted">成交量變化</p>
                            <p class="card-text h4 ${changeClass}">${changeIcon} ${volumeChange}${isNumeric ? '%' : ''}</p>
                            <div id="chart-volume-${symbol}" style="height: 150px;"></div>
                        </div>
                    </div>
                </div>
            `;
            
            // Render chart after the HTML is inserted (in the main init function)
            if (isNumeric) {
                setTimeout(() => {
                    renderVolumeChangeChart(`chart-volume-${symbol}`, chartData);
                }, 0);
            }

        } else {
            html += `
                <div class="col-lg-3 col-md-4 col-sm-6 mb-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">${symbol} - ${fullName}</h5>
                            <p class="text-warning">數據未找到。</p>
                        </div>
                    </div>
                </div>
            `;
        }
    });

    html += "</div>";
    container.innerHTML = html;
}

// --- Initialization ---

document.addEventListener("DOMContentLoaded", loadFundFlowData);
