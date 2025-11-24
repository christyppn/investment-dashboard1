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
 * @param {Array<Object>} cumulativeData - The cumulative volume change data.
 */
function renderVolumeChangeChart(elementId, data, cumulativeData) {
    // Filter out data points where volume_change_percent is missing or null
    const validData = data.filter(item => item.volume_change_percent !== null && item.volume_change_percent !== undefined);
    
    const dates = validData.map(item => item.date);
    const volumeChanges = validData.map(item => item.volume_change_percent);
    
    const options = {
        series: [{
            name: '日成交量變化 %',
            type: 'bar',
            data: volumeChanges
        }, {
            name: '累積成交量變化 %',
            type: 'line',
            data: cumulativeData.map(item => item.y)
        }],
        chart: {
            height: 150,
            toolbar: {
                show: false
            },
            sparkline: {
                enabled: false // Disable sparkline to show full chart features
            }
        },
        stroke: {
            width: [0, 2],
            curve: 'smooth'
        },
        colors: ['#007bff', '#28a745'], // Blue for bar, Green for line
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
                show: true,
                rotate: -45,
                formatter: function(val) {
                    return val.substring(5); // Show MM-DD
                }
            },
            axisBorder: {
                show: false
            },
            axisTicks: {
                show: false
            }
        },
        yaxis: [{
            title: {
                text: '日變化 %',
                style: { color: '#007bff' }
            },
            labels: {
                formatter: function(val) {
                    return val.toFixed(0);
                }
            }
        }, {
            opposite: true,
            title: {
                text: '累積變化 %',
                style: { color: '#28a745' }
            },
            labels: {
                formatter: function(val) {
                    return val.toFixed(0);
                }
            }
        }],
        tooltip: {
            enabled: true,
            x: {
                show: true,
                formatter: function(val) {
                    return val;
                }
            },
            y: [{
                formatter: function(val) {
                    return val.toFixed(2) + '%';
                }
            }, {
                formatter: function(val) {
                    return val.toFixed(2) + '%';
                }
            }]
        },
        grid: {
            show: true,
            borderColor: '#f1f1f1'
        },
        legend: {
            show: true,
            position: 'top'
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
        chartElement.chart = chart;
    }
}

/**
 * Calculates the cumulative percentage change from a series of daily volume changes.
 * @param {Array<Object>} history - The time series data.
 * @returns {Array<Object>} The series with cumulative percentage change.
 */
function calculateCumulativeVolumeChange(history) {
    if (!history || history.length === 0) return [];

    let cumulativeChange = 0;
    return history.map(item => {
        // Only use the volume_change_percent for the cumulative calculation
        const dailyChange = item.volume_change_percent || 0;
        cumulativeChange += dailyChange;
        return {
            x: item.date,
            y: cumulativeChange
        };
    });
}

// --- Theme Toggle ---

function toggleTheme() {
    const isDarkMode = document.body.classList.toggle('dark-mode');
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
    document.getElementById('theme-icon').textContent = isDarkMode ? '☀️' : '🌙';
    // Re-render charts to apply dark mode styles
    loadFundFlowData();
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

// --- Main Function ---

/**
 * Loads and displays Fund Flow data (Sector ETFs).
 * Assumes market_data_history.json is an object: { "XLK": [history], "XLC": [history], ... }
 */
async function loadFundFlowData() {
    // Apply theme first
    applyInitialTheme();

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

    // Render global timestamp
    renderGlobalTimestamp(marketData);

    let html = "";
    
    SECTOR_ETFS.forEach(symbol => {
        const history = marketData[symbol];
        const fullName = SECTOR_ETFS_MAP[symbol] || symbol; // Get the full name
        
        if (history && history.length > 0) {
            const latest = history[history.length - 1];
            
            // Volume Change
            const volumeChange = latest.volume_change_percent !== undefined && latest.volume_change_percent !== null 
                               ? parseFloat(latest.volume_change_percent).toFixed(2) 
                               : 'N/A';
            const isNumeric = volumeChange !== 'N/A';
            const changeClass = isNumeric ? (parseFloat(volumeChange) >= 0 ? 'text-success' : 'text-danger') : 'text-muted';
            const changeIcon = isNumeric ? (parseFloat(volumeChange) >= 0 ? '▲' : '▼') : '';

            // Price and Volume
            const latestClose = parseFloat(latest.close).toFixed(2);
            const latestVolume = (latest.volume / 1000000).toFixed(2) + 'M'; // Display in Millions

            // Calculate cumulative data for the chart
            const cumulativeData = calculateCumulativeVolumeChange(history);

            html += `
                <div class="col-lg-3 col-md-4 col-sm-6 mb-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title mb-1">${symbol} - ${fullName}</h5>
                            <p class="card-text small text-muted mb-1">最新價: $${latestClose} | 成交量: ${latestVolume}</p>
                            <p class="card-text h4 ${changeClass} mb-3">
                                ${changeIcon} ${volumeChange}${isNumeric ? '%' : ''}
                                <span class="small text-muted"> (日成交量變化)</span>
                            </p>
                            <div id="chart-volume-${symbol}" style="height: 150px;"></div>
                        </div>
                    </div>
                </div>
            `;
            
            // Render chart after the HTML is inserted (in the main init function)
            if (isNumeric) {
                setTimeout(() => {
                    renderVolumeChangeChart(`chart-volume-${symbol}`, history, cumulativeData);
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

    container.innerHTML = html;
}

// Run the initialization when the document is ready
document.addEventListener("DOMContentLoaded", loadFundFlowData);
