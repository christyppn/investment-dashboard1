// 資金流向頁面專用邏輯
document.addEventListener('DOMContentLoaded', () => {
    // 確保只在 fund_flow.html 頁面運行
    if (document.getElementById('fundFlowsDetails')) {
        loadFundFlowsDetails();
    }
});

// 載入資金流向詳細數據
async function loadFundFlowsDetails() {
    const DATA_BASE_URL = './data/';
    const elementId = 'fundFlowsDetails';

    try {
        const response = await fetch(`${DATA_BASE_URL}market_data_history.json`);
        const allMarketData = await response.json();

        if (allMarketData && allMarketData.length > 0) {
            
            // 1. 篩選出資金流向數據 (包含 'Volume' 且不包含 'Daily Change' 的指標)
            // 這是最精確的過濾方式，因為市場廣度是 Daily Change，資金流向是 Volume
            const fundFlowData = allMarketData.filter(d => 
                d.metric_name.includes('Volume') && !d.metric_name.includes('Daily Change')
            );
            
            if (fundFlowData.length === 0) {
                document.getElementById(elementId).innerHTML = '<p>暫無資金流向數據</p>';
                return;
            }

            // 2. 找出最新的日期
            // 由於數據已經按日期排序，最新日期是最後一個數據點的日期
            const latestDate = fundFlowData[fundFlowData.length - 1].date;

            // 3. 過濾出最新日期的所有行業數據
            const latestFundFlowData = fundFlowData.filter(d => d.date === latestDate);

            // 4. 繪製趨勢圖 (使用所有數據)
            const chartData = {};
            const categories = [];
            
            // 整理趨勢圖數據
            fundFlowData.forEach(d => {
                if (!chartData[d.metric_name]) {
                    chartData[d.metric_name] = [];
                }
                chartData[d.metric_name].push(d.volume_change);
                
                // 確保 categories (日期) 不重複
                if (!categories.includes(formatTimestamp(d.date, true))) {
                    categories.push(formatTimestamp(d.date, true));
                }
            });

            // 轉換為 ApexCharts 格式
            const series = Object.keys(chartData).map(name => ({
                name: name.replace(' Volume', '').replace(/\s\(.*\)/, ''), // 清理名稱
                data: chartData[name]
            }));

            // 繪製圖表
            renderChart('fundFlowsChart', series, categories, '各板塊成交量變動趨勢', '日變動 (%)', false);


            // 5. 顯示最新的詳細列表
            let html = '';
            latestFundFlowData.forEach(fund => {
                const trend = fund.volume_change;
                const trendClass = trend >= 0 ? 'positive' : 'negative';
                const trendSign = trend >= 0 ? '▲' : '▼';
                
                // 清理名稱，移除 Volume (ETF)
                const cleanName = fund.metric_name.replace(' Volume', '').replace(/\s\(.*\)/, '');

                html += `
                    <div class="fund-item">
                        <div class="fund-name">${cleanName}</div>
                        <div class="fund-price">
                            成交量: <span>${fund.volume.toLocaleString()}</span>
                        </div>
                        <div class="fund-change ${trendClass}">
                            日變動: <span class="flow-trend ${trendClass}">${trendSign} ${Math.abs(trend).toFixed(2)}%</span>
                        </div>
                    </div>
                `;
            });

            document.getElementById(elementId).innerHTML = html;
            document.getElementById('fundFlowsTimestamp').textContent = `更新時間：${formatTimestamp(latestDate)}`;
            document.getElementById('lastUpdate').textContent = formatTimestamp(new Date().toISOString());

        } else {
            document.getElementById(elementId).innerHTML = '<p>載入失敗或數據為空</p>';
        }
    } catch (error) {
        console.error('載入資金流向詳細數據失敗:', error);
        document.getElementById(elementId).innerHTML = '<p>載入失敗</p>';
    }
}
