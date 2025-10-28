// 貨幣基金頁面專用邏輯
document.addEventListener('DOMContentLoaded', () => {
    // 確保只在 money_fund.html 頁面運行
    if (document.getElementById('moneyFundDetails')) {
        loadMoneyFundDetails();
    }
});

// 載入貨幣基金詳細數據
async function loadMoneyFundDetails() {
    const DATA_BASE_URL = './data/';
    const elementId = 'moneyFundDetails';

    try {
        const response = await fetch(`${DATA_BASE_URL}money_fund_data.json`);
        const fundData = await response.json();

        if (fundData && fundData.length > 0) {
            let html = '';
            let latestTimestamp = fundData[0].timestamp;

            fundData.forEach(fund => {
                const changeClass = fund.change >= 0 ? 'positive' : 'negative';
                const changeSign = fund.change >= 0 ? '+' : '';
                
                html += `
                    <div class="fund-item">
                        <div class="fund-name">${fund.fund_name} (${fund.symbol})</div>
                        <div class="fund-price">
                            價格: <span>${fund.price.toFixed(2)}</span>
                        </div>
                        <div class="fund-change ${changeClass}">
                            變動: <span>${changeSign}${fund.change.toFixed(2)} (${fund.change_percent.replace('%', '')}%)</span>
                        </div>
                    </div>
                `;
            });

            document.getElementById(elementId).innerHTML = html;
            document.getElementById('moneyFundTimestamp').textContent = `更新時間：${formatTimestamp(latestTimestamp)}`;
            document.getElementById('lastUpdate').textContent = formatTimestamp(new Date().toISOString());

        } else {
            document.getElementById(elementId).innerHTML = '<p>暫無數據</p>';
        }
    } catch (error) {
        console.error('載入貨幣基金數據失敗:', error);
        document.getElementById(elementId).innerHTML = '<p>載入失敗</p>';
    }
}

// 由於 money_fund.js 已經引入了 script.js，我們只需要確保主頁面的 loadAllData 被調用
// 這裡不需要額外的 DOMContentLoaded 監聽器，因為 script.js 已經處理了。
