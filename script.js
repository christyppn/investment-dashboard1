// script.js - Main JavaScript for index.html

// --- Configuration ---
const DATA_DIR = "data/";
const HIBOR_TERMS = ["1M", "3M", "6M"];

// Global variable to store the full market data history
let fullMarketData = {};

// --- Helper Functions ---

/**
 * Fetches JSON data from a given path, adding a cache-busting parameter.
 * @param {string} path - The path to the JSON file.
 * @returns {Promise<Object|Array>} The parsed JSON data.
 */
async function fetchData(path) {
    try {
        // --- 關鍵修復：加入時間戳以強制緩存無效化 ---
        const cacheBuster = new Date().getTime();
        const response = await fetch(`${DATA_DIR}${path}?t=${cacheBuster}`);
        // ------------------------------------------------
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error fetching data from ${path}:`, error);
        return null;
    }
}

// ... (其餘代碼保持不變) ...

// --- Initialization ---

/**
 * Main function to load all data and render the dashboard.
 */
async function initDashboard() {
    // Fetch market data first and store it globally
    const marketData = await fetchData("market_data_history.json");
    if (marketData && Object.keys(marketData).length > 0) {
        fullMarketData = { ...fullMarketData, ...marketData };
    } else {
        console.error("FATAL ERROR: market_data_history.json is empty or failed to load.");
        // 顯示錯誤信息
        document.getElementById('market-breadth-container').innerHTML = '<p class="text-danger">Market Breadth data is not available or empty. Please run sync_data.py.</p>';
        document.getElementById('global-markets-container').innerHTML = '<p class="text-danger">Global Markets data is not available or empty. Please run sync_data.py.</p>';
    }

    loadHiborRates();
    loadFearGreedIndex();
    loadAIAnalysis(); // 加載 AI 分析

    // Make render functions globally accessible for onclick events
    window.renderMarketBreadth = renderMarketBreadth;
    window.renderGlobalMarkets = renderGlobalMarkets;

    // Initial render with 'ALL' data
    renderMarketBreadth('ALL');
    renderGlobalMarkets('ALL');
}

// Run the initialization when the document is ready
document.addEventListener("DOMContentLoaded", initDashboard);
