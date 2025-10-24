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
        const historyResponse = await fetch(`${DATA_BASE_URL}market_sentiment_history.json`);
        const historyData = await historyResponse.json();

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
            document.getElementById('fearGreedIndex').innerHTML = '<p>暫無數據</p>';
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

// 載入 HIBOR 利率 (不變)
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
            document.getElementById('hiborRates').innerHTML = '<p>暫無數據</p>';
        }
    } catch (error) {
        console.error('載入 HIBOR 利率失敗:', error);
        document.getElementById('hiborRates').innerHTML = '<p>載入失敗</p>';
    }
}

// 載入市場廣度與資金流向 (新邏輯，從 market_data_history.json 讀取)
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

            document.getElementById('marketBreadth').innerHTML = latestBreadthHtml || '<p>暫無數據</p>';
            if (breadthSeries.length > 0) {
                renderChart('marketBreadthChart', breadthSeries, breadthCategories, '市場廣度 (日變動)', '百分比');
            }
            document.getElementById('marketBreadthTimestamp').textContent = `更新時間：${formatTimestamp(breadthData[breadthData.length - 1].date)}`;


            // --- 2. 資金流向 (Volume) ---
            const flowMetrics = ['Technology Sector Volume', 'Financial Sector Volume', 'Energy Sector Volume', 'Consumer Staples Volume', 'Consumer Discretionary Volume', 'Small Cap (Russell 2000) Volume'];
            const flowData = historyData.filter(d => flowMetrics.includes(d.metric_name));

            let latestFlowHtml = '';
            const flowSeries = [];
            let flowCategories = [];

            flowMetrics.forEach(metric => {
                const metricHistory = flowData.filter(d => d.metric_name === metric);
                if (metricHistory.length > 0) {
                    // Get latest value for the card
                    const latest = metricHistory[metricHistory.length - 1];
                    latestFlowHtml += `
                        <div class="flow-item">
                            <div class="flow-sector">${metric.replace(' Volume', '')}</div>
                            <div class="flow-amount">${latest.volume.toLocaleString()}</div>
                        </div>
                    `;
                    
                    // Prepare series data for chart
                    flowSeries.push({
                        name: metric.replace(' Volume', ''),
                        data: metricHistory.map(d => latest.volume) // Note: Using latest volume for all points in the series for simplicity
                    });
                    // Use categories from the first metric
                    if (flowCategories.length === 0) {
                        flowCategories = metricHistory.map(d => new Date(d.date).toLocaleDateString('zh-TW', { month: '2-digit', day: '2-digit' }));
                    }
                }
            });

            document.getElementById('fundFlows').innerHTML = latestFlowHtml || '<p>暫無數據</p>';
            if (flowSeries.length > 0) {
                renderChart('fundFlowsChart', flowSeries, flowCategories, '資金流向 (成交量)', '成交量', true); // isVolume = true for bar chart
            }
            document.getElementById('fundFlowsTimestamp').textContent = `更新時間：${formatTimestamp(flowData[flowData.length - 1].date)}`;


        } else {
            document.getElementById('marketBreadth').innerHTML = '<p>暫無數據</p>';
            document.getElementById('fundFlows').innerHTML = '<p>暫無數據</p>';
        }
    } catch (error) {
        console.error('載入市場數據失敗:', error);
        document.getElementById('marketBreadth').innerHTML = '<p>載入失敗</p>';
        document.getElementById('fundFlows').innerHTML = '<p>載入失敗</p>';
    }
}


// 載入所有數據
async function loadAllData() {
    document.getElementById('lastUpdate').textContent = '載入中...';
    
    await Promise.all([
        loadFearGreedIndex(),
        loadHiborRates(),
        loadMarketData() // 合併市場廣度與資金流向
    ]);
    
    // 由於數據來源更新時間不同，這裡只顯示當前時間
    document.getElementById('lastUpdate').textContent = formatTimestamp(new Date().toISOString());
}

// 刷新按鈕事件
document.getElementById('refreshBtn').addEventListener('click', () => {
    loadAllData();
});

// 頁面載入時自動載入數據
window.addEventListener('DOMContentLoaded', () => {
    loadAllData();
});
