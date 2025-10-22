// API 端點配置
const DATA_BASE_URL = './data/'; // GitHub Pages 會從同一儲存庫讀取

// 格式化時間戳
function formatTimestamp(timestamp) {
    if (!timestamp) return '--';
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

// 載入恐懼貪婪指數
async function loadFearGreedIndex() {
    try {
        const response = await fetch(`${DATA_BASE_URL}market_sentiment.json`);
        const data = await response.json();
        
        if (data && data.length > 0) {
            const latest = data[0];
            document.getElementById('fearGreedIndex').innerHTML = `<div class="value">${latest.value}</div>`;
            
            const statusElement = document.getElementById('fearGreedStatus');
            statusElement.textContent = latest.status || '未知';
            statusElement.className = 'status ' + getStatusClass(latest.status);
            
            document.getElementById('fearGreedTimestamp').textContent = `更新時間：${formatTimestamp(latest.timestamp)}`;
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
            document.getElementById('hiborRates').innerHTML = '<p>暫無數據</p>';
        }
    } catch (error) {
        console.error('載入 HIBOR 利率失敗:', error);
        document.getElementById('hiborRates').innerHTML = '<p>載入失敗</p>';
    }
}

// 載入市場廣度
async function loadMarketBreadth() {
    try {
        const response = await fetch(`${DATA_BASE_URL}market_breadth.json`);
        const data = await response.json();
        
        if (data && data.length > 0) {
            let html = '';
            data.forEach(metric => {
                const valueClass = metric.value >= 0 ? 'positive' : 'negative';
                const sign = metric.value >= 0 ? '+' : '';
                html += `
                    <div class="metric-item">
                        <div class="metric-name">${metric.metric_name}</div>
                        <div class="metric-value ${valueClass}">${sign}${metric.value}%</div>
                    </div>
                `;
            });
            document.getElementById('marketBreadth').innerHTML = html;
            document.getElementById('marketBreadthTimestamp').textContent = `更新時間：${formatTimestamp(data[0].timestamp)}`;
        } else {
            document.getElementById('marketBreadth').innerHTML = '<p>暫無數據</p>';
        }
    } catch (error) {
        console.error('載入市場廣度失敗:', error);
        document.getElementById('marketBreadth').innerHTML = '<p>載入失敗</p>';
    }
}

// 載入資金流向
async function loadFundFlows() {
    try {
        const response = await fetch(`${DATA_BASE_URL}fund_flows.json`);
        const data = await response.json();
        
        if (data && data.length > 0) {
            let html = '';
            data.forEach(flow => {
                html += `
                    <div class="flow-item">
                        <div class="flow-sector">${flow.sector}</div>
                        <div class="flow-amount">${flow.amount.toLocaleString()}</div>
                        <div style="font-size: 0.9rem; color: #666;">${flow.flow_type}</div>
                    </div>
                `;
            });
            document.getElementById('fundFlows').innerHTML = html;
            document.getElementById('fundFlowsTimestamp').textContent = `更新時間：${formatTimestamp(data[0].timestamp)}`;
        } else {
            document.getElementById('fundFlows').innerHTML = '<p>暫無數據</p>';
        }
    } catch (error) {
        console.error('載入資金流向失敗:', error);
        document.getElementById('fundFlows').innerHTML = '<p>載入失敗</p>';
    }
}

// 載入所有數據
async function loadAllData() {
    document.getElementById('lastUpdate').textContent = '載入中...';
    
    await Promise.all([
        loadFearGreedIndex(),
        loadHiborRates(),
        loadMarketBreadth(),
        loadFundFlows()
    ]);
    
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

