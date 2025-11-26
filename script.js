// script.js - Final Corrected Version for index.html

// --- Configuration ---
const DATA_DIR = "data/";
const HIBOR_TERMS = ["1M", "3M", "6M"];

// Global variable to store the full market data history
let fullMarketData = {};

// --- Helper Functions ---

/**
 * Fetches JSON data from a given path, adding a cache-busting parameter.
 * @param {string} path - The path to the JSON file.
 * @returns {Promise<Object|Array|null>} The parsed JSON data or null on failure.
 */
async function fetchData(path) {
    try {
        // Force cache-busting with a timestamp
        const cacheBuster = new Date().getTime();
        const response = await fetch(`${DATA_DIR}${path}?t=${cacheBuster}`);
        
        if (!response.ok) {
            console.error(`HTTP error! Status: ${response.status} for ${path}`);
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error(`Error fetching data from ${path}:`, error);
        return null;
    }
}

// --- Rendering Functions (ApexCharts) ---

function renderChart(elementId, seriesData, categories, title, type = 'line') {
    const options = {
        series: [{
            name: title,
            data: seriesData
        }],
        chart: {
            type: type,
            height: 150,
            toolbar: { show: false }
        },
        xaxis: {
            categories: categories,
            labels: { show: false }
        },
        yaxis: {
            labels: { show: false }
        },
        title: {
            text: title,
            align: 'left',
            style: { fontSize: '14px' }
        },
        dataLabels: { enabled: false },
        stroke: { curve: 'smooth', width: 2 },
        grid: { show: false }
    };
    
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '';
        new ApexCharts(element, options).render();
    }
}

// --- Loaders for Dashboard Tab ---

async function loadHiborRates() {
    const hiborData = await fetchData("hibor_rates.json");
    const container = document.getElementById('hibor-rates-container');
    
    if (!hiborData || !hiborData.rates) {
        container.innerHTML = '<p class="text-danger">HIBOR rates data is unavailable.</p>';
        return;
    }

    let html = '<div class="row">';
    HIBOR_TERMS.forEach(term => {
        const rate = hiborData.rates[term] || 'N/A';
        html += `
            <div class="col-4 text-center">
                <h5 class="mb-0">${term}</h5>
                <p class="h4 text-primary">${rate}%</p>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

async function loadFearGreedIndex() {
    const fngData = await fetchData("fear_greed_index.json");
    const container = document.getElementById('fear-greed-container');

    if (!fngData) {
        container.innerHTML = '<p class="text-danger">Fear & Greed Index data is unavailable.</p>';
        return;
    }

    const value = fngData.value;
    const classification = fngData.classification;
    
    let colorClass = 'text-success';
    if (classification.includes('Fear')) {
        colorClass = 'text-danger';
    } else if (classification.includes('Greed')) {
        colorClass = 'text-warning';
    }

    container.innerHTML = `
        <h3 class="display-4 ${colorClass}">${value}</h3>
        <p class="lead ${colorClass}">${classification}</p>
    `;
}

async function loadAIAnalysis() {
    const aiData = await fetchData("ai_analysis.json");
    const container = document.getElementById('ai-analysis-container');

    if (!aiData) {
        container.innerHTML = '<p class="text-danger">AI Analysis data is unavailable.</p>';
        return;
    }

    container.innerHTML = `
        <p class="text-muted small">Last Updated: ${aiData.date}</p>
        <p class="lead">${aiData.analysis}</p>
        <div class="alert alert-info mt-3">
            <strong>7-Day Prediction:</strong> ${aiData.prediction_7_day}
        </div>
    `;
}

async function loadMarketBreadth() {
    const breadthData = await fetchData("market_breadth.json");
    const container = document.getElementById('market-breadth-container');

    if (!breadthData || breadthData.total_symbols === 0) {
        container.innerHTML = '<p class="text-danger">Market Breadth data is not available or empty. Please run sync_data.py.</p>';
        return;
    }

    const total = breadthData.total_symbols;
    const advancers = breadthData.advancers;
    const decliners = breadthData.decliners;
    const neutral = breadthData.neutral;

    const advancerPct = ((advancers / total) * 100).toFixed(1);
    const declinerPct = ((decliners / total) * 100).toFixed(1);
    const neutralPct = ((neutral / total) * 100).toFixed(1);

    container.innerHTML = `
        <p class="text-muted small">Date: ${breadthData.date} (Total: ${total} symbols)</p>
        <div class="progress" style="height: 25px;">
            <div class="progress-bar bg-success" role="progressbar" style="width: ${advancerPct}%" aria-valuenow="${advancerPct}" aria-valuemin="0" aria-valuemax="100">${advancers} (${advancerPct}%)</div>
            <div class="progress-bar bg-danger" role="progressbar" style="width: ${declinerPct}%" aria-valuenow="${declinerPct}" aria-valuemin="0" aria-valuemax="100">${decliners} (${declinerPct}%)</div>
            <div class="progress-bar bg-secondary" role="progressbar" style="width: ${neutralPct}%" aria-valuenow="${neutralPct}" aria-valuemin="0" aria-valuemax="100">${neutral} (${neutralPct}%)</div>
        </div>
    `;
}

function renderGlobalMarkets(symbol) {
    const containerId = 'global-markets-chart';
    const data = fullMarketData[symbol];
    
    if (!data || data.length === 0) {
        document.getElementById(containerId).innerHTML = `<p class="text-danger">Data for ${symbol} is unavailable.</p>`;
        return;
    }

    const closes = data.map(d => d.Close);
    const dates = data.map(d => d.Date);
    const title = `${symbol} - Global Market Index`;

    renderChart(containerId, closes, dates, title);
}

// --- Tab-Specific Functions (Stubs for missing functions to prevent errors) ---

// These functions are called by the switchTab logic in index.html but may not be fully implemented.
// We define them as stubs to prevent JavaScript errors from stopping the tab switching.

function loadNews() {
    console.log("loadNews called: News content loading logic goes here.");
    // Placeholder for actual news loading logic
}

function loadEducation() {
    console.log("loadEducation called: Education content loading logic goes here.");
    // Placeholder for actual education loading logic
}

function displayFavorites() {
    console.log("displayFavorites called: Favorites content display logic goes here.");
    // Placeholder for actual favorites display logic
}

function displayPortfolio() {
    console.log("displayPortfolio called: Portfolio content display logic goes here.");
    // Placeholder for actual portfolio display logic
}

function load13FData(type) {
    console.log(`load13FData called for type: ${type}. 13F/Consensus loading logic goes here.`);
    // Placeholder for actual 13F/Consensus loading logic
}

// --- Tab Switching Logic ---

/**
 * Handles the switching of content tabs.
 * @param {Event} event - The click event.
 * @param {string} tabName - The ID of the tab content to show.
 */
function switchTab(event, tabName) {
    // 1. Get all tab content elements and hide them
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });

    // 2. Get all tab buttons and remove active class
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
        button.classList.remove('active');
    });

    // 3. Show the current tab content and set the button as active
    const targetContent = document.getElementById(tabName);
    if (targetContent) {
        targetContent.classList.add('active');
    }
    // Use event.currentTarget to ensure the button itself is marked active
    event.currentTarget.classList.add('active');
    
    // 4. Special handling for tabs that need data loading
    if (tabName === 'money-fund') {
        // This tab is for "多基金對比" (Multi-Fund Comparison)
        if (typeof loadMoneyFundData === 'function') {
            loadMoneyFundData();
        } else {
            console.error("loadMoneyFundData function not found. Check if money_fund.js is loaded.");
        }
    } else if (tabName === 'berkshire' || tabName === 'consensus') {
        // These tabs are for "伯克希爾 13F" and "機構共識"
        if (typeof load13FData === 'function') {
            load13FData(tabName);
        } else {
            console.error("load13FData function not found. Check if the relevant script is loaded.");
        }
    }
    
    // Call the original functions from the user's index.html for other tabs
    if (tabName === 'news' && typeof loadNews === 'function') loadNews();
    if (tabName === 'education' && typeof loadEducation === 'function') loadEducation();
    if (tabName === 'favorites' && typeof displayFavorites === 'function') displayFavorites();
    if (tabName === 'portfolio' && typeof displayPortfolio === 'function') displayPortfolio();
}

// Make functions globally accessible for onclick events in HTML
window.switchTab = switchTab;
window.renderGlobalMarkets = renderGlobalMarkets; 
window.loadNews = loadNews;
window.loadEducation = loadEducation;
window.displayFavorites = displayFavorites;
window.displayPortfolio = displayPortfolio;
window.load13FData = load13FData;


// --- Initialization ---

/**
 * Main function to load all data and render the dashboard.
 */
async function initDashboard() {
    // 1. Fetch market data first and store it globally
    const marketData = await fetchData("market_data_history.json");
    if (marketData && Object.keys(marketData).length > 0) {
        fullMarketData = { ...marketData };
    } else {
        console.error("FATAL ERROR: market_data_history.json is empty or failed to load.");
        // Display error message for sections relying on this data
        document.getElementById('global-markets-container').innerHTML = '<p class="text-danger">Global Markets data is not available.</p>';
    }

    // 2. Load all other data sections for the default 'dashboard' tab
    loadHiborRates();
    loadFearGreedIndex();
    loadAIAnalysis();
    loadMarketBreadth();

    // 3. Initial render for Global Markets
    renderGlobalMarkets('GSPC');
    
    // 4. Manually trigger the default tab to show content on load
    const defaultTabButton = document.querySelector('.tab-btn.active');
    // Extract the tab name from the onclick attribute: onclick="switchTab(event, 'dashboard')"
    const defaultTabContentId = defaultTabButton ? defaultTabButton.getAttribute('onclick').match(/'([^']+)'/)[1] : 'dashboard';
    if (defaultTabButton) {
        document.getElementById(defaultTabContentId).classList.add('active');
    }
}

// Run the initialization when the document is ready
document.addEventListener("DOMContentLoaded", initDashboard);
