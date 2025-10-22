# 📊 投資儀表板 | Investment Dashboard

一個完全免費的投資儀表板，使用 GitHub Pages 部署，並透過 GitHub Actions 自動同步市場數據。

## 🌟 功能特色

- **恐懼貪婪指數**：即時顯示市場情緒指標
- **HIBOR 利率**：香港銀行同業拆息率（1M, 3M, 6M）
- **市場廣度**：SPY 每日變化百分比
- **資金流向**：QQQ 交易量作為科技股資金流向參考

## 🚀 部署指南

### 步驟 1：創建 GitHub 儲存庫

1. 登入您的 GitHub 帳戶
2. 創建一個新的公開儲存庫（例如：`investment-dashboard`）
3. 將本專案的所有檔案上傳到該儲存庫

### 步驟 2：設定 Alpha Vantage API 金鑰

1. 前往 [Alpha Vantage](https://www.alphavantage.co/support/#api-key) 註冊並獲取免費 API 金鑰
2. 在您的 GitHub 儲存庫中，前往 **Settings** → **Secrets and variables** → **Actions**
3. 點擊 **New repository secret**
4. 名稱設為 `ALPHA_VANTAGE_API_KEY`，值設為您的 API 金鑰
5. 點擊 **Add secret** 儲存

### 步驟 3：啟用 GitHub Pages

1. 在您的 GitHub 儲存庫中，前往 **Settings** → **Pages**
2. 在 **Source** 下拉選單中，選擇 **Deploy from a branch**
3. 在 **Branch** 下拉選單中，選擇 **main**（或 **master**），資料夾選擇 **/ (root)**
4. 點擊 **Save**
5. 等待幾分鐘後，您的網站將會在 `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/` 上線

### 步驟 4：啟用 GitHub Actions

1. 在您的 GitHub 儲存庫中，前往 **Actions** 標籤
2. 如果看到提示，點擊 **I understand my workflows, go ahead and enable them**
3. GitHub Actions 將會自動每小時執行一次數據同步
4. 您也可以手動觸發：前往 **Actions** → 選擇 **Sync Investment Data** → 點擊 **Run workflow**

## 📁 專案結構

```
investment-dashboard/
├── index.html              # 主頁面
├── styles.css              # 樣式表
├── script.js               # JavaScript 腳本
├── sync_data.py            # 數據同步腳本
├── requirements.txt        # Python 依賴
├── README.md               # 說明文件
├── data/                   # 數據目錄（由 GitHub Actions 自動生成）
│   ├── market_sentiment.json
│   ├── hibor_rates.json
│   ├── market_breadth.json
│   └── fund_flows.json
└── .github/
    └── workflows/
        └── sync-data.yml   # GitHub Actions 工作流程
```

## 🔄 數據更新頻率

- GitHub Actions 每小時自動執行一次數據同步
- 您可以隨時手動觸發數據更新
- 數據來源：
  - HIBOR：香港金融管理局 (HKMA) API
  - 恐懼貪婪指數：CNN Business API
  - 市場廣度與資金流向：Alpha Vantage API

## ⚠️ 免責聲明

本儀表板僅供參考，不構成任何投資建議。投資有風險，請謹慎決策。

## 📝 授權

MIT License

---

**作者**: Manus AI  
**更新日期**: 2025-10-16

