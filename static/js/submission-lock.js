// Submission Lock - Prevents duplicate message submissions
(function() {
    console.log("Submission lock script loaded");
    
    // Global submission lock
    window.isSubmitting = false;
    window.lastSubmissionTime = 0;
    window.submissionCount = 0;
    const SUBMISSION_COOLDOWN = 2000; // 2 seconds cooldown between submissions
    
    // Function to intercept and control all form submissions and fetch requests
    function setupInterceptors() {
        // Intercept fetch requests
        const originalFetch = window.fetch;
        window.fetch = function(url, options) {
            // Only intercept POST requests to /chat or /api/conversations
            if (options && options.method === 'POST' && 
                (url === '/chat' || url === '/api/conversations')) {
                
                const currentTime = Date.now();
                
                // Check if we're already submitting or if we're within cooldown period
                if (window.isSubmitting || 
                    (currentTime - window.lastSubmissionTime < SUBMISSION_COOLDOWN)) {
                    
                    console.warn(`Blocking duplicate ${url} request. Submission already in progress or cooldown active.`);
                    console.log(`Time since last submission: ${currentTime - window.lastSubmissionTime}ms`);
                    
                    // Return a promise that resolves to a fake successful response
                    return new Promise((resolve) => {
                        resolve(new Response(JSON.stringify({
                            blocked: true,
                            message: "Duplicate request blocked by submission lock"
                        }), {
                            status: 200,
                            headers: { 'Content-Type': 'application/json' }
                        }));
                    });
                }
                
                // Set submission lock
                window.isSubmitting = true;
                window.lastSubmissionTime = currentTime;
                window.submissionCount++;
                
                console.log(`Processing ${url} request #${window.submissionCount}`);
                
                // Add a visual indicator that submission is in progress
                addSubmissionIndicator();
                
                // Process the request and release lock when done
                return originalFetch(url, options)
                    .then(response => {
                        console.log(`Request ${url} completed with status ${response.status}`);
                        return response;
                    })
                    .catch(error => {
                        console.error(`Request ${url} failed:`, error);
                        throw error;
                    })
                    .finally(() => {
                        // Release the lock after a short delay
                        setTimeout(() => {
                            window.isSubmitting = false;
                            removeSubmissionIndicator();
                            console.log(`Submission lock released for ${url}`);
                        }, 500);
                    });
            }
            
            // Pass through all other requests
            return originalFetch(url, options);
        };
        
        // Intercept click events on the send button
        document.addEventListener('click', function(e) {
            if (e.target && (e.target.id === 'send-button' || 
                            (e.target.closest && e.target.closest('#send-button')))) {
                
                const currentTime = Date.now();
                
                // Check if we're already submitting or if we're within cooldown period
                if (window.isSubmitting || 
                    (currentTime - window.lastSubmissionTime < SUBMISSION_COOLDOWN)) {
                    
                    console.warn("Blocking duplicate send button click. Submission already in progress or cooldown active.");
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Add visual feedback
                    const sendButton = document.getElementById('send-button');
                    if (sendButton) {
                        sendButton.classList.add('blocked');
                        setTimeout(() => {
                            sendButton.classList.remove('blocked');
                        }, 500);
                    }
                    
                    return false;
                }
            }
        }, true); // Use capture phase to intercept before other handlers
        
        // Intercept keypress events for Enter key
        document.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && e.target && e.target.id === 'message-input') {
                const currentTime = Date.now();
                
                // Check if we're already submitting or if we're within cooldown period
                if (window.isSubmitting || 
                    (currentTime - window.lastSubmissionTime < SUBMISSION_COOLDOWN)) {
                    
                    console.warn("Blocking duplicate Enter key press. Submission already in progress or cooldown active.");
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Add visual feedback
                    const messageInput = document.getElementById('message-input');
                    if (messageInput) {
                        messageInput.classList.add('blocked');
                        setTimeout(() => {
                            messageInput.classList.remove('blocked');
                        }, 500);
                    }
                    
                    return false;
                }
            }
        }, true); // Use capture phase to intercept before other handlers
        
        console.log("Submission interceptors set up");
    }
    
    // Function to add a visual indicator that submission is in progress
    function addSubmissionIndicator() {
        // Add a style for the blocked class if it doesn't exist
        if (!document.getElementById('submission-lock-style')) {
            const style = document.createElement('style');
            style.id = 'submission-lock-style';
            style.textContent = `
                .blocked {
                    animation: shake 0.5s;
                    border-color: #ff6b6b !important;
                }
                @keyframes shake {
                    0%, 100% { transform: translateX(0); }
                    10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                    20%, 40%, 60%, 80% { transform: translateX(5px); }
                }
                #submission-indicator {
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    background-color: rgba(0, 123, 255, 0.8);
                    color: white;
                    padding: 5px 10px;
                    border-radius: 5px;
                    z-index: 9999;
                    font-size: 12px;
                }
            `;
            document.head.appendChild(style);
        }
        
        // Add the indicator element if it doesn't exist
        if (!document.getElementById('submission-indicator')) {
            const indicator = document.createElement('div');
            indicator.id = 'submission-indicator';
            indicator.textContent = 'Sending...';
            document.body.appendChild(indicator);
        }
    }
    
    // Function to remove the submission indicator
    function removeSubmissionIndicator() {
        const indicator = document.getElementById('submission-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    // Set up the interceptors when the DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupInterceptors);
    } else {
        setupInterceptors();
    }
    
    // Also disable all existing event listeners for the send button
    function disableExistingListeners() {
        setTimeout(() => {
            const sendButton = document.getElementById('send-button');
            if (sendButton) {
                const newButton = sendButton.cloneNode(true);
                sendButton.parentNode.replaceChild(newButton, sendButton);
                console.log("Removed all existing event listeners from send button");
            }
            
            const messageInput = document.getElementById('message-input');
            if (messageInput) {
                const newInput = messageInput.cloneNode(true);
                messageInput.parentNode.replaceChild(newInput, messageInput);
                console.log("Removed all existing event listeners from message input");
                
                // Add a single event listener for Enter key
                newInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        const sendBtn = document.getElementById('send-button');
                        if (sendBtn) {
                            sendBtn.click();
                        }
                    }
                });
            }
        }, 1000);
    }
    
    // Call this function to disable existing listeners
    disableExistingListeners();
})();
