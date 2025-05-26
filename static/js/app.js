// App State
const state = {
    currentSection: 'dashboard',
    loading: false
};

// DOM Elements
const loadingOverlay = document.getElementById('loadingOverlay');
const contentSections = document.querySelectorAll('.content-section');
const navLinks = document.querySelectorAll('[href^="#"]');

// Loading Indicator
function showLoading() {
    loadingOverlay.classList.add('active');
    state.loading = true;
}

function hideLoading() {
    loadingOverlay.classList.remove('active');
    state.loading = false;
}

// Navigation
function navigateTo(sectionId) {
    // Remove '#' from the sectionId
    sectionId = sectionId.replace('#', '');

    // Update active section
    contentSections.forEach(section => {
        section.classList.remove('active');
        if (section.id === sectionId) {
            section.classList.add('active');
        }
    });

    // Update navigation
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${sectionId}`) {
            link.classList.add('active');
        }
    });

    // Update mobile navigation
    document.querySelectorAll('.mobile-nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('href') === `#${sectionId}`) {
            item.classList.add('active');
        }
    });

    state.currentSection = sectionId;
}

// Event Listeners
navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const sectionId = e.currentTarget.getAttribute('href');
        navigateTo(sectionId);
    });
});

// Initialize Dashboard Content
function initializeDashboard() {
    const dashboard = document.getElementById('dashboard');
    dashboard.innerHTML = `
        <div class="row g-4">
            <div class="col-md-6 col-lg-3">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Pending Claims</h5>
                        <h2 class="card-text">3</h2>
                        <small class="text-muted">Awaiting approval</small>
                    </div>
                </div>
            </div>
            <div class="col-md-6 col-lg-3">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Approved</h5>
                        <h2 class="card-text">12</h2>
                        <small class="text-muted">This month</small>
                    </div>
                </div>
            </div>
            <div class="col-md-6 col-lg-3">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Total Amount</h5>
                        <h2 class="card-text">₹24,500</h2>
                        <small class="text-muted">This month</small>
                    </div>
                </div>
            </div>
            <div class="col-md-6 col-lg-3">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Processing Time</h5>
                        <h2 class="card-text">2.3 days</h2>
                        <small class="text-muted">Average</small>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Fetch User Data
async function fetchUserData() {
    try {
        const response = await fetch('/api/user');
        if (response.ok) {
            const userData = await response.json();
            // Update user name in the navbar
            document.getElementById('userName').textContent = userData.name;
            return userData;
        }
    } catch (error) {
        console.error('Error fetching user data:', error);
    }
    return null;
}

// Handle Logout
document.addEventListener('click', (e) => {
    const target = e.target.closest('a[href="#logout"]');
    if (target) {
        e.preventDefault();
        window.location.href = '/logout';
    }
});

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', async () => {
    // Hide loading overlay initially
    hideLoading();

    // Fetch user data
    await fetchUserData();

    // Initialize dashboard
    initializeDashboard();

    // Navigate to the appropriate section
    navigateTo(window.location.hash || '#dashboard');
});
