// fund_flow.js - JavaScript for fund_flow.html

// --- Configuration ---
const DATA_DIR = "data/";

// ETF Full Names Map
const SECTOR_ETFS_MAP = {
    "XLK": "科技 (Technology)",
    "XLC": "通訊服務 (Communication Services)",
    "XLY": "非必需消費品 (Consumer Discretionary)",
    "XLP": "必需消費品 (Consumer Staples)",
    "XLV": "醫療保健 (Health Care)",
    "XLF": "金融 (Financial)",
    "XLE": "能源 (Energy)",
    "XLI": "工業 (Industrial)",
    "XLB": "材料 (Materials)",
    "XLU": "公用事業 (Utilities)",
    "VNQ": "房地產 (Real Estate)",
    "GLD": "黃金 (Gold)",
    "ROBO": "機器人與自動化 (Robotics & Automation)",
    "SMH": "半導體 (Semiconductors)",
    "IWM": "羅素2000 (Russell 2000)"
};

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
 * Renders a simple sparkline chart for volume change using ApexCharts.
 * @param {string} elementId - The ID of the element to render the chart in.
 * @param {Array<Object>} data - The time series data for the chart.
 * @param {string} colorClass - The class to determine the line color.
 */
function renderVolumeSparklineChart(elementId, data, colorClass) {
    const color = colorClass === 'text-success' ? '#28a745' : '#dc3545';
    
    const options = {
        series: [{
            name: 'Volume Change %',
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
                    return value.toFixed(2) + '%';
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


// --- Fund Flow Data ---

/**
 * Loads and displays Fund Flow data (Sector ETFs, etc.) with volume change charts.
 * Assumes market_data_history.json is an object: { "XLK": [history], "XLC": [history], ... }
 */
async function loadFundFlowData() {
    const marketData = await fetchData("market_data_history.json");
    const container = document.getElementById("fund-flow-container");
    
    // Filter for the ETFs we want to display in the fund flow section
    const fundFlowSymbols = Object.keys(SECTOR_ETFS_MAP);

    if (!marketData || Object.keys(marketData).length === 0) {
        if (container) container.innerHTML = "<p class='text-danger'>Fund Flow data is not available or empty.</p>";
        return;
    }

    let html = "<div class='row'>";
    
    fundFlowSymbols.forEach(symbol => {
        const history = marketData[symbol];
        const fullName = SECTOR_ETFS_MAP[symbol] || symbol;
        
        if (history && history.length > 0) {
            const latest = history[history.length - 1];
            const price = parseFloat(latest.close).toFixed(2);
            const change = parseFloat(latest.change_percent).toFixed(2);
            const volume = latest.volume.toLocaleString(); // Format volume with commas
            const changeClass = change >= 0 ? 'text-success' : 'text-danger';
            const changeIcon = change >= 0 ? '▲' : '▼';
            
            html += `
                <div class="col-lg-3 col-md-4 col-sm-6 mb-4">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title mb-1">${symbol} - ${fullName}</h5>
                            <p class="card-text h4 mb-1">${price} <span class="small text-muted">USD</span></p>
                            <p class="card-text ${changeClass}">${changeIcon} ${change}%</p>
                            <p class="card-text small text-muted">Volume: ${volume}</p>
                            <div class="mt-3">
                                <h6 class="card-subtitle mb-2 text-muted">Volume Change Trend (%)</h6>
                                <div id="chart-volume-${symbol}" style="height: 150px;"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Prepare data for ApexCharts (Volume Change %)
            const seriesData = history.map(item => ({
                x: new Date(item.date).getTime(),
                y: item.volume_change_percent
            }));

            // Render chart after the HTML is inserted (in the main init function)
            setTimeout(() => {
                renderVolumeSparklineChart(`chart-volume-${symbol}`, seriesData, changeClass);
            }, 0);

        } else {
            html += `
                <div class="col-lg-3 col-md-4 col-sm-6 mb-4">
                    <div class="card h-100">
                        <div class="card-body">
                            <h5 class="card-title">${symbol} - ${fullName}</h5>
                            <p class="text-warning">Data not found.</p>
                        </div>
                    </div>
                </div>
            `;
        }
    });

    if (container) {
        html += "</div>";
        container.innerHTML = html;
    }
}


// --- Initialization ---

/**
 * Main function to load all data and render the dashboard.
 */
function initFundFlowDashboard() {
    loadFundFlowData();
}

// Run the initialization when the document is ready
document.addEventListener("DOMContentLoaded", initFundFlowDashboard);
