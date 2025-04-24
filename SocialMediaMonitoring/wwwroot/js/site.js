/**
 * Mastodon Analysis Tool
 * A client-side script for analyzing Mastodon posts sentiment and summarizing trends
 * Designed to work with PythonApi.py and AnalysisController.cs
 */

// Chart instances
let sentimentChart = null;
let sentimentTimeChart = null;

// DOM elements will be initialized in the initElements function
let elements = {};

/**
 * Initialize DOM elements after document is ready
 */
function initElements() {
    elements = {
        // Input and controls
        keywordInput: document.getElementById('keywordInput'),
        maxResultsInput: document.getElementById('maxResultsInput'),
        analyzeBtn: document.getElementById('analyzeBtn'),

        // UI state indicators
        loadingIndicator: document.getElementById('loadingIndicator'),
        loadingMessage: document.getElementById('loadingMessage'),
        errorContainer: document.getElementById('errorContainer'),
        resultsContainer: document.getElementById('resultsContainer'),

        // Results display elements
        summaryText: document.getElementById('summaryText'),
        sentimentChartCanvas: document.getElementById('sentimentChart'),
        positivePercentage: document.getElementById('positivePercentage'),
        neutralPercentage: document.getElementById('neutralPercentage'),
        negativePercentage: document.getElementById('negativePercentage'),
        relatedKeywordsContainer: document.getElementById('relatedKeywordsContainer'),
        noKeywordsMessage: document.getElementById('noKeywordsMessage'),

        // NEW: Sentiment over time elements
        sentimentTimeChartCanvas: document.getElementById('sentimentTimeChart'),
        sentimentTimeContainer: document.getElementById('sentimentTimeContainer'),
        noTimeDataMessage: document.getElementById('noTimeDataMessage')
    };
}

/**
 * Initializes the application
 */
function initApp() {
    // Initialize DOM elements
    initElements();

    // Check if required elements exist
    validateRequiredElements();

    // Set up event listeners
    if (elements.analyzeBtn) {
        console.log('Adding click listener to analyze button');
        elements.analyzeBtn.addEventListener('click', handleAnalyzeClick);
    }

    if (elements.keywordInput) {
        elements.keywordInput.addEventListener('keypress', e => {
            if (e.key === 'Enter') {
                handleAnalyzeClick();
            }
        });

        // Focus on the input field
        elements.keywordInput.focus();
    }

    console.log('Mastodon Sentiment Analysis Tool initialized');
}

/**
 * Validates that all required DOM elements exist
 */
function validateRequiredElements() {
    const criticalElements = ['keywordInput', 'analyzeBtn', 'loadingIndicator', 'errorContainer', 'resultsContainer'];

    let missingElements = criticalElements.filter(id => !elements[id]);

    if (missingElements.length > 0) {
        console.error('Missing critical elements:', missingElements.join(', '));
    }

    // Log all elements for debugging
    console.log('DOM Elements:');
    Object.entries(elements).forEach(([key, element]) => {
        console.log(`- ${key}: ${element ? 'Found' : 'MISSING'}`);
    });
}

/**
 * Handles the analyze button click event
 */
async function handleAnalyzeClick() {
    console.log('Analyze button clicked');

    // Get the keyword to analyze
    const keyword = elements.keywordInput?.value?.trim();

    // Validate input
    if (!keyword) {
        showError('Please enter a hashtag or keyword to analyze');
        return;
    }

    // Update UI state - show loading indicator
    setUIState('loading');

    try {
        // Call the API and get results
        const analysisResults = await fetchAnalysisResults(keyword);

        // Display the results
        displayResults(analysisResults);

        // Update UI state - show results
        setUIState('results');
    } catch (error) {
        console.error('Analysis failed:', error);
        showError(error.message || 'Failed to analyze posts. Please try again.');

        // Update UI state - show error
        setUIState('error');
    }
}

/**
 * Sets the UI state
 * @param {string} state - The state to set ('loading', 'results', 'error')
 */
function setUIState(state) {
    // Hide all state-dependent elements first
    elements.loadingIndicator.style.display = 'none';
    elements.resultsContainer.style.display = 'none';
    elements.errorContainer.style.display = 'none';

    // Show appropriate elements based on state
    switch (state) {
        case 'loading':
            elements.loadingIndicator.style.display = 'block';
            break;
        case 'results':
            elements.resultsContainer.style.display = 'block';
            break;
        case 'error':
            // The error container is shown by showError()
            break;
    }
}

/**
 * Fetches analysis results from the API
 * @param {string} keyword - The keyword to analyze
 * @returns {Promise<Object>} - The analysis results
 */
async function fetchAnalysisResults(keyword) {
    const maxResults = parseInt(elements.maxResultsInput.value) || 100;

    console.log(`Analyzing keyword: "${keyword}" with max results: ${maxResults}`);

    // Update loading message based on max results
    if (elements.loadingMessage) {
        if (maxResults > 200) {
            elements.loadingMessage.textContent = "Analyzing a large number of posts. This may take several minutes...";
        } else if (maxResults > 100) {
            elements.loadingMessage.textContent = "Analyzing posts. This should take a minute or two...";
        } else {
            elements.loadingMessage.textContent = "This should take less than a minute...";
        }
    }

    try {
        const response = await fetch('/api/Analysis/analyze-mastodon', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: keyword,
                maxResults: maxResults
            })
        });

        console.log(`API response status: ${response.status}`);

        // Handle non-success responses
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.error || `Server responded with status ${response.status}`;
            throw new Error(errorMessage);
        }

        // Parse and return the data
        const data = await response.json();
        console.log('Analysis results:', data);
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

/**
 * Displays the analysis results
 * @param {Object} data - The analysis results
 */
function displayResults(data) {
    // Make sure we have data to display
    if (!data) {
        showError('No data received from the analysis service');
        return;
    }

    // Display the summary
    if (elements.summaryText) {
        // Convert newlines to <br> tags for proper HTML display
        const formattedSummary = data.summary ? data.summary.replace(/\n/g, '<br>') : 'No summary available';
        elements.summaryText.innerHTML = formattedSummary;  // Use innerHTML instead of textContent
    }

    // Display sentiment data if available
    if (data.sentiment) {
        displaySentimentData(data.sentiment);
    } else {
        console.warn('No sentiment data in the response');
    }

    // Display sentiment over time data if available
    if (data.sentimentOverTime && data.sentimentOverTime.length > 0) {
        displaySentimentOverTime(data.sentimentOverTime);
    } else {
        hideSentimentOverTime();
    }

    // Display related keywords if available
    if (data.relatedKeywords && data.relatedKeywords.length > 0) {
        displayRelatedKeywords(data.relatedKeywords);
    } else {
        // Show "no keywords" message
        if (elements.relatedKeywordsContainer) {
            elements.relatedKeywordsContainer.innerHTML = '';
        }
        if (elements.noKeywordsMessage) {
            elements.noKeywordsMessage.style.display = 'block';
        }
    }
}

/**
 * Displays the sentiment data
 * @param {Object} sentimentData - The sentiment data object 
 */
function displaySentimentData(sentimentData) {
    // Update percentage text displays
    updatePercentageDisplays(sentimentData);

    // Create or update the sentiment chart
    createSentimentChart(sentimentData);
}

/**
 * Updates the percentage displays
 * @param {Object} sentimentData - The sentiment data object
 */
function updatePercentageDisplays(sentimentData) {
    // Update each sentiment percentage text
    if (elements.positivePercentage) {
        elements.positivePercentage.textContent = `${sentimentData.positive}%`;
    }

    if (elements.neutralPercentage) {
        elements.neutralPercentage.textContent = `${sentimentData.neutral}%`;
    }

    if (elements.negativePercentage) {
        elements.negativePercentage.textContent = `${sentimentData.negative}%`;
    }
}

/**
 * Creates or updates the sentiment chart
 * @param {Object} sentimentData - The sentiment data object
 */
function createSentimentChart(sentimentData) {
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded. Cannot create charts.');
        return;
    }

    // Check if the chart canvas exists
    if (!elements.sentimentChartCanvas) {
        console.error('Sentiment chart canvas not found');
        return;
    }

    // If there's an existing chart, destroy it first
    if (sentimentChart) {
        sentimentChart.destroy();
    }

    // Create a new chart
    const ctx = elements.sentimentChartCanvas.getContext('2d');

    sentimentChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Positive', 'Neutral', 'Negative'],
            datasets: [{
                data: [
                    sentimentData.positive,
                    sentimentData.neutral,
                    sentimentData.negative
                ],
                backgroundColor: [
                    '#4CAF50', // Green for positive
                    '#2196F3', // Blue for neutral
                    '#F44336'  // Red for negative
                ],
                borderColor: [
                    '#388E3C', // Darker green
                    '#1976D2', // Darker blue
                    '#D32F2F'  // Darker red
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: {
                            size: 14
                        },
                        padding: 20
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return `${context.label}: ${context.raw}%`;
                        }
                    }
                }
            },
            cutout: '65%'
        }
    });
}

/**
 * Displays the sentiment over time data
 * @param {Array} timeSeriesData - Array of time period data with sentiment
 */
function displaySentimentOverTime(timeSeriesData) {
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded. Cannot create charts.');
        return;
    }

    // Check if the chart canvas exists
    if (!elements.sentimentTimeChartCanvas) {
        console.error('Sentiment time chart canvas not found');
        return;
    }

    // Additional validation: Ensure we have at least 2 data points for a meaningful chart
    if (!timeSeriesData || timeSeriesData.length < 2) {
        console.warn('Not enough time periods for a meaningful chart (need at least 2)');
        hideSentimentOverTime();
        return;
    }

    // Show the container, hide the no data message
    if (elements.sentimentTimeContainer) {
        elements.sentimentTimeContainer.style.display = 'block';
    }
    if (elements.noTimeDataMessage) {
        elements.noTimeDataMessage.style.display = 'none';
    }

    // If there's an existing chart, destroy it first
    if (sentimentTimeChart) {
        sentimentTimeChart.destroy();
    }

    // Extract dates and sentiment values
    const labels = timeSeriesData.map(entry => formatDate(entry.period));
    const positiveData = timeSeriesData.map(entry => entry.sentiment.positive);
    const neutralData = timeSeriesData.map(entry => entry.sentiment.neutral);
    const negativeData = timeSeriesData.map(entry => entry.sentiment.negative);

    // Create post count dataset to show as a line
    const postCounts = timeSeriesData.map(entry => entry.count);
    const maxCount = Math.max(...postCounts);
    const scaledCounts = postCounts.map(count => (count / maxCount) * 100 * 0.8); // Scale to 80% of max height

    // Create a new chart
    const ctx = elements.sentimentTimeChartCanvas.getContext('2d');

    sentimentTimeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Positive',
                    data: positiveData,
                    backgroundColor: '#4CAF50',
                    borderColor: '#388E3C',
                    borderWidth: 1,
                    order: 1  // Higher order value means it's drawn first (in the back)
                },
                {
                    label: 'Neutral',
                    data: neutralData,
                    backgroundColor: '#2196F3',
                    borderColor: '#1976D2',
                    borderWidth: 1,
                    order: 1  // Same order as other bars to maintain stacking
                },
                {
                    label: 'Negative',
                    data: negativeData,
                    backgroundColor: '#F44336',
                    borderColor: '#D32F2F',
                    borderWidth: 1,
                    order: 1  // Same order as other bars to maintain stacking
                },
                {
                    label: 'Post Count',
                    data: scaledCounts,
                    type: 'line',
                    borderColor: '#9C27B0',
                    backgroundColor: 'rgba(156, 39, 176, 0.2)',
                    borderWidth: 3,  // Increased for better visibility
                    pointRadius: 5,  // Slightly larger points for better visibility
                    pointBackgroundColor: '#9C27B0',
                    fill: false,
                    yAxisID: 'y1',
                    order: 0,  // Lower order value means it's drawn last (in the front)
                    z: 10  // Additional z property for increased specificity
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Date'
                    }
                },
                y: {
                    stacked: true,
                    min: 0,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Sentiment %'
                    },
                    ticks: {
                        callback: function (value) {
                            return value + '%';
                        }
                    }
                },
                y1: {
                    position: 'right',
                    grid: {
                        drawOnChartArea: false
                    },
                    min: 0,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Post Count (scaled)'
                    },
                    ticks: {
                        callback: function (value) {
                            return Math.round((value / 80) * maxCount);
                        }
                    }
                }
            },
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const label = context.dataset.label;
                            if (label === 'Post Count') {
                                const originalCount = timeSeriesData[context.dataIndex].count;
                                return `Post Count: ${originalCount}`;
                            } else {
                                return `${label}: ${context.raw}%`;
                            }
                        }
                    }
                },
                legend: {
                    position: 'bottom'
                },
                title: {
                    display: true,
                    text: 'Sentiment Trends Over Time'
                }
            }
        }
    });
}


/**
 * Hides the sentiment over time section and shows "no data" message
 */
function hideSentimentOverTime() {
    if (elements.sentimentTimeContainer) {
        elements.sentimentTimeContainer.style.display = 'none';
    }
    if (elements.noTimeDataMessage) {
        elements.noTimeDataMessage.style.display = 'block';
    }

    // If there's an existing chart, destroy it
    if (sentimentTimeChart) {
        sentimentTimeChart.destroy();
        sentimentTimeChart = null;
    }
}

/**
 * Formats a date string from API format to a more readable format
 * @param {string} dateStr - The date string from the API (YYYY-MM-DD or YYYY-WW or YYYY-MM-DD HH:MM)
 * @returns {string} - Formatted date string
 */
function formatDate(dateStr) {
    // If no date string, return empty
    if (!dateStr) return '';

    // Check for different date formats
    if (dateStr.includes(':')) {
        // Format with time (YYYY-MM-DD HH:MM)
        const [datePart, timePart] = dateStr.split(' ');
        const [year, month, day] = datePart.split('-');
        return `${month}/${day} ${timePart}`;
    } else if (dateStr.includes('-W')) {
        // Week format (YYYY-WW)
        const [year, week] = dateStr.split('-W');
        return `Week ${week}, ${year}`;
    } else {
        // Regular date (YYYY-MM-DD)
        const [year, month, day] = dateStr.split('-');
        return `${month}/${day}`;
    }
}

/**
 * Displays the related keywords
 * @param {Array} keywords - The array of related keywords
 */
function displayRelatedKeywords(keywords) {
    if (!elements.relatedKeywordsContainer) {
        console.error('Related keywords container not found');
        return;
    }

    // Clear previous keywords
    elements.relatedKeywordsContainer.innerHTML = '';

    // Hide "no keywords" message
    if (elements.noKeywordsMessage) {
        elements.noKeywordsMessage.style.display = 'none';
    }

    // Add each keyword as a badge
    keywords.forEach(keyword => {
        const badge = document.createElement('div');
        badge.className = 'badge bg-secondary fs-6 p-2';
        badge.textContent = keyword;
        elements.relatedKeywordsContainer.appendChild(badge);
    });
}

/**
 * Shows an error message
 * @param {string} message - The error message to show
 */
function showError(message) {
    if (elements.errorContainer) {
        elements.errorContainer.textContent = message;
        elements.errorContainer.style.display = 'block';
    } else {
        console.error('Error container not found, error message:', message);
        alert(`Error: ${message}`);
    }
}

/**
 * Ensures Chart.js is loaded and if not, loads it dynamically
 */
function ensureChartJsLoaded() {
    return new Promise((resolve, reject) => {
        if (typeof Chart !== 'undefined') {
            console.log('Chart.js is already loaded');
            resolve();
            return;
        }

        console.log('Chart.js not found, loading dynamically');
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js';
        script.onload = () => {
            console.log('Chart.js loaded successfully');
            resolve();
        };
        script.onerror = () => {
            console.error('Failed to load Chart.js');
            reject(new Error('Failed to load Chart.js'));
        };
        document.head.appendChild(script);
    });
}

// Initialize the app when the DOM is fully loaded
$(function () {
    console.log('Document ready, initializing app...');

    // Ensure Chart.js is loaded before initializing the app
    ensureChartJsLoaded()
        .then(() => {
            console.log('Chart.js loaded, initializing app');
            initApp();
        })
        .catch(error => {
            console.error('Failed to load Chart.js:', error);
            // Initialize app anyway, charts just won't work
            initApp();
        });
});
