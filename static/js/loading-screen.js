// Loading Screen JavaScript

// Global loading screen controller
const LoadingScreen = {
    // Store start time when showing the loading screen
    startTime: 0,
    // Minimum display time in milliseconds (ensures animation completes)
    minDisplayTime: 1000, // Reduced to make the loading screen disappear faster
    // Animation duration in milliseconds (from CSS)
    animationDuration: 1000, // Reduced to match minDisplayTime
    // Reference to the loading screen element
    element: null,
    // CSS variables for animation control
    cssVars: {
        fillDuration: '--fill-duration'
    },
    // Track if we're currently measuring load time
    isMeasuring: false,
    // Store measured load times for different operations
    loadTimes: {
        login: 4, // Increased default starting value in seconds
        dashboard: 3,
        expenseForm: 3,
        dataLoad: 3
    },
    // Track the current operation being timed
    currentOperation: null,
    // Track if logo is loaded
    logoLoaded: false,
    // Track if we're in the authentication flow
    authInProgress: false,

    // Initialize the loading screen
    init: function() {
        this.element = document.getElementById('loadingScreen');

        // Preload the logo image
        if (this.element) {
            const logoImg = this.element.querySelector('.loading-logo-color');
            if (logoImg) {
                // If logo is already loaded
                if (logoImg.complete) {
                    this.logoLoaded = true;
                } else {
                    // Wait for logo to load
                    logoImg.onload = () => {
                        this.logoLoaded = true;
                        console.log('Logo image loaded successfully');
                    };
                    logoImg.onerror = () => {
                        console.error('Error loading logo image');
                        this.logoLoaded = true; // Proceed anyway to avoid blocking
                    };
                }
            }

            // Set up default event listener for page load
            window.addEventListener('load', function() {
                // Always hide the loading screen when page is fully loaded
                setTimeout(function() {
                    LoadingScreen.hide();
                }, 500); // Small delay to ensure smooth transition
            });

            // Add event listener for login form submission
            const loginForm = document.getElementById('loginForm');
            if (loginForm) {
                loginForm.addEventListener('submit', function() {
                    LoadingScreen.startMeasuring('login');
                });
            }

            // Listen for Google login button click
            const googleLoginBtn = document.querySelector('.google-login-btn');
            if (googleLoginBtn) {
                googleLoginBtn.addEventListener('click', function() {
                    LoadingScreen.startMeasuring('login');
                });
            }
        }
    },

    // Start measuring load time for a specific operation
    startMeasuring: function(operation) {
        this.currentOperation = operation;
        this.isMeasuring = true;
        this.startTime = Date.now();

        // Use the previously measured time (or default) for this operation
        const estimatedTime = this.loadTimes[operation] || 3;
        this.show(estimatedTime);
    },

    // Stop measuring and record the time
    stopMeasuring: function() {
        if (!this.isMeasuring || !this.currentOperation) return;

        const elapsedTime = (Date.now() - this.startTime) / 1000; // Convert to seconds

        // Update the stored load time with a weighted average (80% new, 20% old)
        // This helps smooth out variations while still adapting quickly
        const oldTime = this.loadTimes[this.currentOperation] || 3;
        const newTime = oldTime * 0.2 + elapsedTime * 0.8;

        // Cap between 1-10 seconds
        this.loadTimes[this.currentOperation] = Math.max(1, Math.min(10, newTime));

        console.log(`Measured load time for ${this.currentOperation}: ${elapsedTime.toFixed(2)}s, new average: ${this.loadTimes[this.currentOperation].toFixed(2)}s`);

        this.isMeasuring = false;
        this.currentOperation = null;

        // Hide the loading screen
        this.hide();
    },

    // Show the loading screen
    show: function(estimatedLoadTime) {
        // Check if we're already in the auth flow to prevent multiple loading screens
        if (this.authInProgress || sessionStorage.getItem('authFlowInProgress') === 'true') {
            console.log('Auth flow in progress, not showing another loading screen');
            return;
        }

        if (!this.element) {
            this.element = document.getElementById('loadingScreen');
        }

        if (this.element) {
            // Store the current time if not already measuring
            if (!this.isMeasuring) {
                this.startTime = Date.now();
            }

            // Set a consistent, faster animation speed
            // Cap the animation duration at 1 second
            const duration = '1s';
            this.element.style.setProperty(this.cssVars.fillDuration, duration);
            this.animationDuration = 1000;
            this.minDisplayTime = 1000; // Ensure minDisplayTime matches animation duration

            // Show the loading screen
            this.element.style.display = 'flex';
            this.element.classList.remove('fade-out');

            // Make sure the progress bar is visible with sunny yellow color
            const progressBar = this.element.querySelector('.loading-progress-bar');
            if (progressBar) {
                progressBar.style.backgroundColor = '#FFD700'; // Sunny yellow color
            }

            console.log('Loading screen shown');
        }
    },

    // Hide the loading screen
    hide: function() {
        if (!this.element) {
            this.element = document.getElementById('loadingScreen');
        }

        if (this.element && this.element.style.display !== 'none') {
            console.log('Hiding loading screen...');

            // Add fade-out class for smooth transition
            this.element.classList.add('fade-out');

            // Hide the element after a short transition
            setTimeout(() => {
                this.element.style.display = 'none';
                this.element.classList.remove('fade-out');

                // Reset flags
                this.authInProgress = false;
                this.isMeasuring = false;
                sessionStorage.removeItem('authFlowInProgress');

                console.log('Loading screen hidden successfully');
            }, 300);
        }
    }
};

// Initialize loading screen on DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    LoadingScreen.init();

    // Preload the logo image to avoid flashing
    const logoImg = document.querySelector('.loading-logo-color');
    if (logoImg) {
        const img = new Image();
        img.onload = function() {
            LoadingScreen.logoLoaded = true;
            console.log('Logo preloaded successfully');
        };
        img.onerror = function() {
            console.error('Error preloading logo');
            LoadingScreen.logoLoaded = true; // Proceed anyway
        };
        img.src = logoImg.src;
    }

    // Failsafe: Always hide loading screen after 5 seconds maximum
    setTimeout(function() {
        if (LoadingScreen.element && LoadingScreen.element.style.display !== 'none') {
            console.log('Failsafe: Force hiding loading screen after 5 seconds');
            LoadingScreen.hide();
        }
    }, 5000);

    // Fix for back buttons - prevent loading screen from showing on simple navigation links
    document.addEventListener('click', function(e) {
        // Check if the clicked element is a back button or navigation link
        const isBackButton = e.target.closest('a.btn-secondary') ||
                            (e.target.closest('a') && e.target.closest('a').textContent.includes('Back'));

        if (isBackButton) {
            // Don't show loading screen for back buttons
            e.preventDefault();
            const href = e.target.closest('a').getAttribute('href');
            console.log('Back button clicked, navigating to:', href);
            window.location.href = href;
        }
    });
});
