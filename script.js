// API 端點配置
const DATA_BASE_URL = './data/'; // GitHub Pages 會從同一儲存庫讀取

// 格式化時間戳
function formatTimestamp(timestamp) {
    if (!timestamp) return '--';
    // 確保只取日期部分，避免時間戳過長
    const date = new Date(timestamp);
    return date.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}

// --- 繪製趨勢圖函數 ---
function renderChart(elementId, seriesData, categories, chartTitle, yAxisTitle, isVolume = false) {
    const options = {
        series: seriesData,
        chart: {
            type: isVolume ? 'bar' : 'line',
            height: 150,
            toolbar: {
                show: false
            }
        },
        title: {
            text: chartTitle,
            align: 'left',
            style: {
                fontSize: '14px'
            }
        },
        xaxis: {
            categories: categories,
            labels: {
                show: false // 隱藏 X 軸標籤，保持簡潔
            }
        },
        yaxis: {
            title: {
                text: yAxisTitle,
                style: {
                    fontSize: '10px'
                }
            }
        },
        tooltip: {
            x: {
                format: 'MM/dd'
            }
        },
        dataLabels: {
            enabled: false
        }
    };

    // 銷毀舊圖表（如果存在）
    const chartElement = document.getElementById(elementId);
    if (chartElement.chart) {
        chartElement.chart.destroy();
    }
    
    chartElement.chart = new ApexCharts(chartElement, options);
    chartElement.chart.render();
}

// --- 載入數據函數 ---

// 載入恐懼貪婪指數 (包含歷史趨勢)
async function loadFearGreedIndex() {
    try {
        // 載入歷史數據
        // 新增隨機參數以避免瀏覽器緩存
        const response = await fetch(`${DATA_BASE_URL}market_sentiment_history.json?v=${new Date().getTime()}`);
        const historyData = await response.json(); // <-- 直接將結果賦值給 historyData

        if (historyData && historyData.length > 0) {
            // 找出最新數據 (sync_data.py 中已標記 is_latest)
            const latest = historyData[historyData.length - 1];
            
            // 1. 更新主卡片顯示
            document.getElementById('fearGreedIndex').innerHTML = `<div class="value">${latest.value}</div>`;
            const statusElement = document.getElementById('fearGreedStatus');
            statusElement.textContent = latest.status || '未知';
            statusElement.className = 'status ' + getStatusClass(latest.status);
            document.getElementById('fearGreedTimestamp').textContent = `更新時間：${formatTimestamp(latest.date)}`;

            // 2. 繪製趨勢圖
            const categories = historyData.map(d => new Date(d.date).toLocaleDateString('zh-TW', { month: '2-digit', day: '2-digit' }));
            const seriesData = [{
                name: '指數',
                data: historyData.map(d => d.value)
            }];
            renderChart('fearGreedChart', seriesData, categories, '30天趨勢', '指數分數');

        } else {
            document.getElementById('fearGreedIndex').innerHTML = '<p>載入失敗</p>';
        }
    } catch (error) {
        console.error('載入恐懼貪婪指數失敗:', error);
        document.getElementById('fearGreedIndex').innerHTML = '<p>載入失敗</p>';
    }
}

// 根據狀態返回 CSS 類別
function getStatusClass(status) {
    if (!status) return '';
    const lowerStatus = status.toLowerCase();
    if (lowerStatus.includes('extreme fear')) return 'extreme-fear';
    if (lowerStatus.includes('fear')) return 'fear';
    if (lowerStatus.includes('neutral')) return 'neutral';
    if (lowerStatus.includes('extreme greed')) return 'extreme-greed';
    if (lowerStatus.includes('greed')) return 'greed';
    return '';
}

// 載入 HIBOR 利率
async function loadHiborRates() {
    try {
        const response = await fetch(`${DATA_BASE_URL}hibor_rates.json`);
        const data = await response.json();
        
        if (data && data.length > 0) {
            let html = '';
            data.forEach(rate => {
                html += `
                    <div class="rate-item">
                        <span class="rate-term">${rate.term}</span>
                        <span class="rate-value">${rate.rate.toFixed(2)}%</span>
                    </div>
                `;
            });
            document.getElementById('hiborRates').innerHTML = html;
            document.getElementById('hiborTimestamp').textContent = `更新時間：${formatTimestamp(data[0].timestamp)}`;
        } else {
            document.getElementById('hiborRates').innerHTML = '<p>載入失敗</p>';
        }
    } catch (error) {
        console.error('載入 HIBOR 利率失敗:', error);
        document.getElementById('hiborRates').innerHTML = '<p>載入失敗</p>';
    }
}

// 載入市場廣度 (只處理市場廣度，資金流向已移至 fund_flow.js)
async function loadMarketData() {
    try {
        const response = await fetch(`${DATA_BASE_URL}market_data_history.json`);
        const historyData = await response.json();

        if (historyData && historyData.length > 0) {
            // --- 1. 市場廣度 (Daily Change) ---
            const breadthMetrics = ['S&P 500 Daily Change', 'NASDAQ 100 Daily Change', 'Dow 30 Daily Change'];
            const breadthData = historyData.filter(d => breadthMetrics.includes(d.metric_name));
            
            let latestBreadthHtml = '';
            const breadthSeries = [];
            let breadthCategories = [];

            // Group by metric_name to prepare for charting
            breadthMetrics.forEach(metric => {
                const metricHistory = breadthData.filter(d => d.metric_name === metric);
                if (metricHistory.length > 0) {
                    // Get latest value for the card
                    const latest = metricHistory[metricHistory.length - 1];
                    const valueClass = latest.change >= 0 ? 'positive' : 'negative';
                    const sign = latest.change >= 0 ? '+' : '';
                    latestBreadthHtml += `
                        <div class="metric-item">
                            <div class="metric-name">${metric.replace(' Daily Change', '')}</div>
                            <div class="metric-value ${valueClass}">${sign}${latest.change}%</div>
                        </div>
                    `;
                    
                    // Prepare series data for chart
                    breadthSeries.push({
                        name: metric.replace(' Daily Change', ''),
                        data: metricHistory.map(d => d.change)
                    });
                    // Use categories from the first metric
                    if (breadthCategories.length === 0) {
                        breadthCategories = metricHistory.map(d => new Date(d.date).toLocaleDateString('zh-TW', { month: '2-digit', day: '2-digit' }));
                    }
                }
            });

            document.getElementById('marketBreadth').innerHTML = latestBreadthHtml || '<p>載入失敗</p>';
            if (breadthSeries.length > 0) {
                renderChart('marketBreadthChart', breadthSeries, breadthCategories, '市場廣度 (日變動)', '百分比');
            }
            document.getElementById('marketBreadthTimestamp').textContent = `更新時間：${formatTimestamp(breadthData[breadthData.length - 1].date)}`;

        } else {
            document.getElementById('marketBreadth').innerHTML = '<p>載入失敗</p>';
        }
    } catch (error) {
        console.error('載入市場廣度失敗:', error);
        document.getElementById('marketBreadth').innerHTML = '<p>載入失敗</p>';
    }
}

// 輔助函數：根據百分比變化設置顏色
function setChangeColor(elementId, change) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = (change > 0 ? '+' : '') + change.toFixed(2) + '%';
        element.className = 'change-percent ' + (change > 0 ? 'positive' : (change < 0 ? 'negative' : 'neutral'));
    }
}

// 輔助函數：渲染單個指數卡片
function renderIndexCard(symbol, name, data) {
    if (!data || data.length === 0) {
        console.warn(`No data for ${symbol}`);
        return;
    }

    const latest = data[data.length - 1];
    const categories = data.map(d => d.date);
    const seriesData = data.map(d => d.close);

    // 1. 更新數值和顏色
    document.getElementById(`${symbol.toLowerCase().replace('^', '')}-value`).textContent = latest.close.toFixed(2);
    setChangeColor(`${symbol.toLowerCase().replace('^', '')}-change`, latest.change_percent);

    // 2. 渲染趨勢圖
    const chartId = `${symbol.toLowerCase().replace('^', '')}-chart`;
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
        colors: [latest.change_percent >= 0 ? '#4CAF50' : '#F44336'], // 根據最新變化設置顏色
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

    // 檢查圖表是否已存在，如果存在則更新，否則新建
    if (ApexCharts.getChartByID(chartId)) {
        ApexCharts.exec(chartId, 'updateOptions', options);
    } else {
        const chart = new ApexCharts(document.getElementById(chartId), options);
        chart.render();
    }
}

// 擴展 loadMarketData 函數以處理 VIX, HSI, N225
async function loadMarketData() {
    const DATA_BASE_URL = './data/';
    try {
        // 新增隨機參數以避免瀏覽器緩存
        const response = await fetch(`${DATA_BASE_URL}market_data_history.json?v=${new Date().getTime()}`);
        const marketData = await response.json();

        // --- 處理市場廣度 (SPY, QQQ, DIA) ---
        // (保留您現有的市場廣度處理邏輯)
        // ... (現有的 SPY, QQQ, DIA 處理代碼) ...
        
        // --- 處理 VIX, HSI, N225 ---
        renderIndexCard('^VIX', 'VIX 波動率指數', marketData['^VIX']);
        renderIndexCard('^HSI', '恒生指數', marketData['^HSI']);
        renderIndexCard('^N225', '日經 225 指數', marketData['^N225']);

    } catch (error) {
        console.error("Error loading market data:", error);
    }
}

// 確保在頁面加載完成後調用 loadMarketData
document.addEventListener('DOMContentLoaded', () => {
    // ... (保留現有的 loadFearGreedIndex, loadHiborRates, loadMoneyFundData 調用) ...
    loadMarketData(); // 確保調用
});


// 載入所有數據 (只載入主頁面數據)
async function loadAllData() {
    document.getElementById('lastUpdate').textContent = '載入中...';
    
    await Promise.all([
        loadFearGreedIndex(),
        loadHiborRates(),
        loadMarketData()
    ]);
    
    document.getElementById('lastUpdate').textContent = formatTimestamp(new Date().toISOString());
}

// 刷新按鈕事件
document.getElementById('refreshBtn').addEventListener('click', () => {
    loadAllData();
});

// 頁面載入時自動載入數據
window.addEventListener('DOMContentLoaded', () => {
    // 確保只在主頁面運行 loadAllData
    if (document.getElementById('fearGreedIndex')) {
        loadAllData();
    }
});
