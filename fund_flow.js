// 資金流向頁面專用邏輯
document.addEventListener('DOMContentLoaded', () => {
    // 確保只在 fund_flow.html 頁面運行
    if (document.getElementById('fundFlowsDetails')) {
        loadFundFlowsDetails();
    }
});

// 格式化時間戳 (從 script.js 繼承)
// function formatTimestamp(timestamp) { ... }
// function renderChart(elementId, seriesData, categories, chartTitle, yAxisTitle, isVolume = false) { ... }

// 載入資金流向詳細數據
async function loadFundFlowsDetails() {
    const DATA_BASE_URL = './data/';
    const elementId = 'fundFlowsDetails';

    try {
        const response = await fetch(`${DATA_BASE_URL}market_data_history.json`);
        const historyData = await response.json();

        if (historyData && historyData.length > 0) {
            const flowMetrics = [
                'Technology Sector Volume', 
                'Financial Sector Volume', 
                'Energy Sector Volume', 
                'Consumer Staples Volume', 
                'Consumer Discretionary Volume', 
                'Small Cap (Russell 2000) Volume'
            ];
        // 篩選出資金流向數據 (包含 Volume 的指標)
        const fundFlowData = allMarketData.filter(d => d.metric_name.includes('Volume'));

        // 由於 market_data_history 包含歷史數據，我們需要過濾出最新的數據點
        // 這裡我們只取最新的數據點
        const latestDate = fundFlowData.length > 0 ? fundFlowData[fundFlowData.length - 1].date : null;
        const latestFundFlowData = fundFlowData.filter(d => d.date === latestDate);
            
            let latestFlowHtml = '';
            const flowSeries = [];
            let flowCategories = [];

            // 提取最新的時間戳
            const latestTimestamp = flowData[flowData.length - 1].date;

            flowMetrics.forEach(metric => {
                const metricHistory = flowData.filter(d => d.metric_name === metric);
                if (metricHistory.length > 0) {
                    // Get latest value and volume change for the card
                    const latest = metricHistory[metricHistory.length - 1];
                    const trendClass = latest.volume_change >= 0 ? 'positive' : 'negative';
                    const trendSign = latest.volume_change >= 0 ? '▲' : '▼';
                    
                    latestFlowHtml += `
                        <div class="flow-item">
                            <div class="flow-sector">${metric.replace(' Volume', '')}</div>
                            <div class="flow-amount">
                                <span>${latest.volume.toLocaleString()}</span>
                                <span class="flow-trend ${trendClass}">${trendSign} ${Math.abs(latest.volume_change).toFixed(2)}%</span>
                            </div>
                        </div>
                    `;
                    
                    // Prepare series data for chart
                    flowSeries.push({
                        name: metric.replace(' Volume', ''),
                        data: metricHistory.map(d => d.volume)
                    });
                    // Use categories from the first metric
                    if (flowCategories.length === 0) {
                        flowCategories = metricHistory.map(d => new Date(d.date).toLocaleDateString('zh-TW', { month: '2-digit', day: '2-digit' }));
                    }
                }
            });

            document.getElementById(elementId).innerHTML = latestFlowHtml || '<p>暫無數據</p>';
            
            // 繪製趨勢圖
            if (flowSeries.length > 0) {
                renderChart('fundFlowsChart', flowSeries, flowCategories, '資金流向 (成交量) 趨勢', '成交量', true);
            }
            document.getElementById('fundFlowsTimestamp').textContent = `更新時間：${formatTimestamp(latestTimestamp)}`;
            document.getElementById('lastUpdate').textContent = formatTimestamp(new Date().toISOString());

        } else {
            document.getElementById(elementId).innerHTML = '<p>暫無數據</p>';
        }
    } catch (error) {
        console.error('載入資金流向失敗:', error);
        document.getElementById(elementId).innerHTML = '<p>載入失敗</p>';
    }
}

// 由於 fund_flow.js 已經引入了 script.js，我們只需要確保主頁面的 loadAllData 被調用
// 這裡不需要額外的 DOMContentLoaded 監聽器，因為 script.js 已經處理了。
