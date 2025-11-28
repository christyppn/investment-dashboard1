// script.js - Main JavaScript for index.html

const DATA_BASE_URL = './data/';
let globalMarketsChart = null;

// --- Helper Functions ---

/**
 * 核心數據獲取函數。
 * 檢查文件路徑和響應狀態。
 */
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

function formatNumber(num, decimals = 2) {
    return num.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function formatChange(change) {
    const isPositive = change >= 0;
    const sign = isPositive ? '+' : '';
    const colorClass = isPositive ? 'text-success' : 'text-danger';
    return `<span class="${colorClass}">${sign}${change.toFixed(2)}%</span>`;
}

// --- Dashboard Rendering Functions ---

async function loadAIAnalysis() {
    const data = await fetchData('ai_analysis.json');
    const container = document.getElementById('ai-analysis-container');
    if (data && data.analysis) {
        container.innerHTML = `
            <p style="font-size: 1.1em; line-height: 1.6; color: var(--text-primary);">${data.analysis}</p>
            <p style="margin-top: 15px; font-size: 0.9em; color: var(--text-secondary);">
                <strong>情緒評級:</strong> <span style="font-weight: bold; color: ${data.sentiment === 'Bullish' ? '#22c55e' : data.sentiment === 'Bearish' ? '#ef4444' : '#f97316'};">${data.sentiment}</span>
                  

                <strong>更新時間:</strong> ${data.timestamp}
            </p>
        `;
    } else {
        container.innerHTML = '<p class="text-danger">AI 分析數據不可用。</p>';
    }
}

async function loadFearGreedIndex() {
    const data = await fetchData('fear_greed_index.json');
    const container = document.getElementById('fear-greed-container');
    
    if (!container) return;

    if (data && data.value !== undefined) {
        const value = data.value;
        const sentiment = data.sentiment;
        const source = data.source || '未知來源';
        let color;

        if (value >= 75) {
            color = '#ef4444'; // Extreme Greed
        } else if (value >= 50) {
            color = '#f97316'; // Greed
        } else if (value >= 25) {
            color = '#3b82f6'; // Neutral
        } else {
            color = '#22c55e'; // Fear/Extreme Fear
        }

        container.innerHTML = `
            <div style="font-size: 3em; font-weight: bold; color: ${color};">${value}</div>
            <div style="font-size: 1.2em; font-weight: bold; color: ${color};">${sentiment}</div>
            <div style="font-size: 0.8em; color: var(--text-secondary); margin-top: 10px;">來源: ${source}</div>
            <div style="font-size: 0.8em; color: var(--text-secondary);">更新時間: ${data.timestamp}</div>
            <div class="progress" style="height: 10px; margin-top: 15px;">
                <div class="progress-bar" role="progressbar" style="width: ${value}%; background-color: ${color};" aria-valuenow="${value}" aria-valuemin="0" aria-valuemax="100"></div>
            </div>
        `;
    } else {
        container.innerHTML = '<p class="text-danger">恐懼與貪婪指數數據不可用。</p>';
    }
}

async function loadHiborRates() {
    const data = await fetchData('hibor_rates.json');
    const container = document.getElementById('hibor-rates-container');
    
    if (!container) return;

    if (data && data.rates && data.rates.length > 0) {
        const latestRates = data.rates;
        let html = '<table class="table" style="font-size: 0.9em;">';
        html += '<thead><tr><th>期限</th><th>利率 (%)</th></tr></thead><tbody>';
        latestRates.forEach(rate => {
            html += `<tr><td>${rate.term}</td><td>${formatNumber(rate.rate, 3)}</td></tr>`;
        });
        html += '</tbody></table>';
        html += `<p style="font-size: 0.8em; color: var(--text-secondary); margin-top: 10px;">數據日期: ${latestRates[0].date}</p>`;
        html += `<p style="font-size: 0.8em; color: var(--text-secondary);">抓取時間: ${data.timestamp}</p>`;
        container.innerHTML = html;
    } else {
        container.innerHTML = '<p class="text-danger">HIBOR 利率數據不可用。</p>';
    }
}

async function loadMarketBreadth() {
    const data = await fetchData('market_breadth.json');
    const container = document.getElementById('market-breadth-container');
    
    if (!container) return;

    if (data && data.breadth) {
        let html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">';
        
        data.breadth.forEach(item => {
            const percent = item.percent_above;
            const isPositive = percent >= 50;
            const color = isPositive ? 'var(--success-color)' : 'var(--danger-color)';
            const barColor = isPositive ? 'bg-success' : 'bg-danger';
            
            html += `
                <div class="card" style="padding: 15px;">
                    <h4 style="margin-bottom: 5px; font-size: 1em;">${item.name}</h4>
                    <div style="font-size: 1.5em; font-weight: bold; color: ${color};">${percent.toFixed(1)}%</div>
                    <div style="font-size: 0.8em; color: var(--text-secondary); margin-bottom: 10px;">高於 ${item.ma_days} 日均線</div>
                    <div class="progress" style="height: 15px;">
                        <div class="progress-bar ${barColor}" role="progressbar" style="width: ${percent}%;" aria-valuenow="${percent}" aria-valuemin="0" aria-valuemax="100">${percent.toFixed(1)}%</div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        html += `<p style="font-size: 0.8em; color: var(--text-secondary); margin-top: 20px;">更新時間: ${data.timestamp}</p>`;
        container.innerHTML = html;
    } else {
        container.innerHTML = '<p class="text-danger">市場廣度數據不可用。</p>';
    }
}

async function renderGlobalMarkets(symbol) {
    const data = await fetchData('market_data_history.json');
    const container = document.getElementById('global-markets-chart');
    
    if (!container) return;

    if (!data || !data[symbol]) {
        container.innerHTML = `<p class="text-danger">指數 ${symbol} 的歷史數據不可用。</p>`;
        return;
    }

    const chartData = data[symbol];
    const dates = chartData.map(item => item.date);
    const closes = chartData.map(item => item.close);
    const name = chartData[0].name;

    if (globalMarketsChart) {
        globalMarketsChart.destroy();
    }

    container.innerHTML = '<canvas id="globalMarketsCanvas"></canvas>';
    const ctx = document.getElementById('globalMarketsCanvas').getContext('2d');

    globalMarketsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: `${name} (${symbol}) 收盤價`,
                data: closes,
                borderColor: 'var(--primary-color)',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: '日期'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: '價格'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true
                }
            }
        }
    });
}

// --- New Tab Logic ---

/**
 * 加載 13F 和 機構共識數據。
 * @param {string} tabName - 'berkshire' 或 'consensus'
 */
async function load13FData(tabName) {
    const container = document.getElementById(tabName === 'berkshire' ? 'berkshire-13f-content' : 'consensus-content');
    container.innerHTML = '<p class="text-muted">載入中...</p>';

    // 嘗試加載 13F 數據
    const f13Data = await fetchData('13f-data.json');
    // 嘗試加載市場情緒數據 (用於共識分析)
    const sentimentData = await fetchData('market_sentiment.json');

    if (tabName === 'berkshire') {
        if (f13Data && f13Data.holdings) {
            // 這裡應該是完整的 13F 渲染邏輯，但由於您沒有提供，我們只顯示一個成功的標記
            container.innerHTML = `
                <p class="text-success">✅ 伯克希爾 13F 數據已成功加載 (${f13Data.holdings.length} 筆持倉)。</p>
                <p class="text-muted">請在您的 HTML 中實現完整的渲染邏輯。</p>
            `;
        } else {
            container.innerHTML = '<p class="text-danger">伯克希爾 13F 數據不可用 (13f-data.json 缺失或格式錯誤)。</p>';
        }
    } else if (tabName === 'consensus') {
        if (sentimentData && sentimentData.consensus) {
            // 這裡應該是完整的共識渲染邏輯
            container.innerHTML = `
                <p class="text-success">✅ 機構共識數據已成功加載。</p>
                <p class="text-muted">最新情緒: ${sentimentData.consensus.latest_sentiment} (${sentimentData.consensus.timestamp})</p>
                <p class="text-muted">請在您的 HTML 中實現完整的渲染邏輯。</p>
            `;
        } else {
            container.innerHTML = '<p class="text-danger">機構共識數據不可用 (market_sentiment.json 缺失或格式錯誤)。</p>';
        }
    }
}


// --- Tab Switching Logic ---

/**
 * The core function to switch between tabs.
 * This function is called by the onclick event of all tab buttons.
 */
function switchTab(event, tabName) {
    // 1. Remove 'active' class from all content and buttons
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

    // 2. Add 'active' class to the selected content and button
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');

    // 3. Call specific loading functions for the new tab
    if (tabName === 'portfolio') displayPortfolio();
    if (tabName === 'screening') performScreening();
    if (tabName === 'favorites') displayFavorites();
    if (tabName === 'financial') displayFinancialMetrics();
    
    // The following functions are stubs to prevent errors if they are not fully implemented yet
    if (tabName === 'news') loadNews(); 
    if (tabName === 'education') loadEducation();
    
    // These call functions defined in money_fund.js and fund_flow.js
    if (tabName === 'money-fund') {
        if (typeof loadMoneyFundData === 'function') {
            loadMoneyFundData();
        } else {
            console.error("loadMoneyFundData function not found. Check if money_fund.js is loaded.");
        }
    }
    
    // Call the newly implemented load13FData
    if (tabName === 'berkshire' || tabName === 'consensus') {
        load13FData(tabName);
    }
}

// --- Placeholder/Stub Functions (Preventing errors from missing functions) ---

function displayPortfolio() { console.log("displayPortfolio called (stub)"); }
function performScreening() { console.log("performScreening called (stub)"); }
function displayFavorites() { console.log("displayFavorites called (stub)"); }
function displayFinancialMetrics() { console.log("displayFinancialMetrics called (stub)"); }
function loadNews() { console.log("loadNews called (stub)"); }
function loadEducation() { console.log("loadEducation called (stub)"); }

// --- Initialization ---

function initDashboard() {
    // 1. Load all core dashboard data
    loadAIAnalysis();
    loadFearGreedIndex();
    loadHiborRates();
    loadMarketBreadth();
    
    // 2. Initial render of Global Markets (e.g., S&P 500)
    renderGlobalMarkets('GSPC');

    // Make render functions globally accessible for onclick events
    window.renderGlobalMarkets = renderGlobalMarkets;
    window.switchTab = switchTab; // Expose switchTab globally
    window.load13FData = load13FData; // Expose load13FData globally
}

// Run the initialization when the document is ready
document.addEventListener("DOMContentLoaded", initDashboard);
