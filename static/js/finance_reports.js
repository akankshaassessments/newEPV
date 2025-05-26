// Finance Reports JavaScript

// Chart color palette
const chartColors = [
    'rgba(54, 162, 235, 0.7)',  // Blue
    'rgba(255, 99, 132, 0.7)',   // Red
    'rgba(75, 192, 192, 0.7)',   // Green
    'rgba(255, 159, 64, 0.7)',   // Orange
    'rgba(153, 102, 255, 0.7)',  // Purple
    'rgba(255, 205, 86, 0.7)',   // Yellow
    'rgba(201, 203, 207, 0.7)',  // Grey
    'rgba(54, 162, 235, 0.5)',   // Light Blue
    'rgba(255, 99, 132, 0.5)',   // Light Red
    'rgba(75, 192, 192, 0.5)',   // Light Green
];

// Chart instances
let monthlyTrendChart;
let categoryDistributionChart;
let expenseTrendChart;
let costCenterChart;
let processingTimeChart;

// Initialize charts and event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize overview charts
    initializeOverviewCharts();
    
    // Add event listeners for tab changes
    document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('click', function(event) {
            const targetTab = event.target.getAttribute('data-bs-target').substring(1);
            handleTabChange(targetTab);
        });
    });
    
    // Add event listeners for filter buttons
    document.getElementById('applyOverviewFilter').addEventListener('click', function() {
        updateOverviewData();
    });
    
    document.getElementById('applyTrendFilter').addEventListener('click', function() {
        updateExpenseTrends();
    });
    
    document.getElementById('applyCostCenterFilter').addEventListener('click', function() {
        updateCostCenterAnalysis();
    });
    
    document.getElementById('applyProcessingFilter').addEventListener('click', function() {
        updateProcessingTimeData();
    });
    
    document.getElementById('applyDetailedFilter').addEventListener('click', function() {
        updateDetailedReport();
    });
    
    // Add event listeners for export buttons
    document.getElementById('exportOverview').addEventListener('click', function() {
        exportOverviewData();
    });
    
    document.getElementById('exportTrends').addEventListener('click', function() {
        exportTrendsData();
    });
    
    document.getElementById('exportCostCenter').addEventListener('click', function() {
        exportCostCenterData();
    });
    
    document.getElementById('exportProcessing').addEventListener('click', function() {
        exportProcessingData();
    });
    
    document.getElementById('exportDetailed').addEventListener('click', function() {
        exportDetailedData();
    });
});

// Handle tab changes
function handleTabChange(tabId) {
    console.log('Tab changed to:', tabId);
    
    switch(tabId) {
        case 'expense-trends':
            if (!expenseTrendChart) {
                initializeExpenseTrendChart();
                updateExpenseTrends();
            }
            break;
        case 'cost-center':
            if (!costCenterChart) {
                initializeCostCenterChart();
                updateCostCenterAnalysis();
            }
            break;
        case 'processing':
            if (!processingTimeChart) {
                initializeProcessingTimeChart();
                updateProcessingTimeData();
            }
            break;
        case 'detailed':
            updateDetailedReport();
            break;
    }
}

// Initialize overview charts
function initializeOverviewCharts() {
    // Monthly Trend Chart
    const monthlyTrendCtx = document.getElementById('monthlyTrendChart').getContext('2d');
    monthlyTrendChart = new Chart(monthlyTrendCtx, {
        type: 'bar',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            datasets: [{
                label: 'Total Amount (₹)',
                data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                backgroundColor: chartColors[0],
                borderColor: chartColors[0].replace('0.7', '1'),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString();
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Total: ₹' + context.raw.toLocaleString();
                        }
                    }
                }
            }
        }
    });
    
    // Category Distribution Chart
    const categoryDistributionCtx = document.getElementById('categoryDistributionChart').getContext('2d');
    categoryDistributionChart = new Chart(categoryDistributionCtx, {
        type: 'doughnut',
        data: {
            labels: ['Office Supplies', 'Travel', 'Meals', 'Equipment', 'Others'],
            datasets: [{
                data: [0, 0, 0, 0, 0],
                backgroundColor: chartColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                            return `${context.label}: ₹${value.toLocaleString()} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
    
    // Load initial data
    updateOverviewData();
}

// Initialize expense trend chart
function initializeExpenseTrendChart() {
    const expenseTrendCtx = document.getElementById('expenseTrendChart').getContext('2d');
    expenseTrendChart = new Chart(expenseTrendCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Total Expenses',
                data: [],
                borderColor: chartColors[0].replace('0.7', '1'),
                backgroundColor: chartColors[0],
                tension: 0.1,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// Initialize cost center chart
function initializeCostCenterChart() {
    const costCenterCtx = document.getElementById('costCenterChart').getContext('2d');
    costCenterChart = new Chart(costCenterCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Total Amount',
                data: [],
                backgroundColor: chartColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString();
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Total: ₹' + context.raw.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// Initialize processing time chart
function initializeProcessingTimeChart() {
    const processingTimeCtx = document.getElementById('processingTimeChart').getContext('2d');
    processingTimeChart = new Chart(processingTimeCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Average Processing Time (Days)',
                data: [],
                backgroundColor: chartColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toFixed(1) + ' days';
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Avg. Time: ' + context.raw.toFixed(1) + ' days';
                        }
                    }
                }
            }
        }
    });
}

// Update overview data
function updateOverviewData() {
    const dateRange = document.getElementById('overviewDateRange').value;
    const city = document.getElementById('overviewCity').value;
    
    // Show loading indicator
    showLoading();
    
    // Fetch data from API
    fetch(`/api/reports/overview?date_range=${dateRange}&city=${city}`)
        .then(response => response.json())
        .then(data => {
            // Update stats
            document.getElementById('totalExpenses').textContent = data.total_expenses;
            document.getElementById('totalAmount').textContent = data.total_amount;
            document.getElementById('avgAmount').textContent = data.avg_amount;
            document.getElementById('avgProcessingTime').textContent = data.avg_processing_time;
            
            // Update monthly trend chart
            updateMonthlyTrendChart(data.monthly_trend);
            
            // Update category distribution chart
            updateCategoryDistributionChart(data.category_distribution);
            
            // Hide loading indicator
            hideLoading();
        })
        .catch(error => {
            console.error('Error fetching overview data:', error);
            hideLoading();
            showError('Failed to load overview data. Please try again.');
        });
}

// Update monthly trend chart
function updateMonthlyTrendChart(data) {
    monthlyTrendChart.data.datasets[0].data = data;
    monthlyTrendChart.update();
}

// Update category distribution chart
function updateCategoryDistributionChart(data) {
    categoryDistributionChart.data.labels = data.labels;
    categoryDistributionChart.data.datasets[0].data = data.values;
    categoryDistributionChart.update();
}

// Update expense trends
function updateExpenseTrends() {
    const timePeriod = document.getElementById('trendTimePeriod').value;
    const expenseHead = document.getElementById('trendExpenseHead').value;
    
    // Show loading indicator
    showLoading();
    
    // Fetch data from API
    fetch(`/api/reports/expense-trends?time_period=${timePeriod}&expense_head=${expenseHead}`)
        .then(response => response.json())
        .then(data => {
            // Update expense trend chart
            expenseTrendChart.data.labels = data.labels;
            expenseTrendChart.data.datasets[0].data = data.values;
            expenseTrendChart.update();
            
            // Hide loading indicator
            hideLoading();
        })
        .catch(error => {
            console.error('Error fetching expense trends:', error);
            hideLoading();
            showError('Failed to load expense trends. Please try again.');
        });
}

// Helper functions for loading and error states
function showLoading() {
    // Show loading overlay
    if (typeof LoadingScreen !== 'undefined') {
        LoadingScreen.show('Loading report data...');
    }
}

function hideLoading() {
    // Hide loading overlay
    if (typeof LoadingScreen !== 'undefined') {
        LoadingScreen.hide();
    }
}

function showError(message) {
    // Show error message using SweetAlert2
    Swal.fire({
        icon: 'error',
        title: 'Error',
        text: message,
        confirmButtonColor: '#0070d2'
    });
}

// Export functions (to be implemented)
function exportOverviewData() {
    alert('Export functionality will be implemented soon.');
}

function exportTrendsData() {
    alert('Export functionality will be implemented soon.');
}

function exportCostCenterData() {
    alert('Export functionality will be implemented soon.');
}

function exportProcessingData() {
    alert('Export functionality will be implemented soon.');
}

function exportDetailedData() {
    alert('Export functionality will be implemented soon.');
}

// Placeholder functions for other updates (to be implemented)
function updateCostCenterAnalysis() {
    // Placeholder - will be implemented
    showLoading();
    setTimeout(hideLoading, 500);
}

function updateProcessingTimeData() {
    // Placeholder - will be implemented
    showLoading();
    setTimeout(hideLoading, 500);
}

function updateDetailedReport() {
    // Placeholder - will be implemented
    showLoading();
    setTimeout(hideLoading, 500);
}
