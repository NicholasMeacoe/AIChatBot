// History loading fix
document.addEventListener('DOMContentLoaded', function() {
    console.log("History fix script loaded");
    
    // Function to fix history loading
    function fixHistoryLoading() {
        const historyDateSelect = document.getElementById('history-date-select');
        
        if (!historyDateSelect) {
            console.error("History date select not found");
            return;
        }
        
        console.log("Found history date select, applying fix");
        
        // Remove existing event listeners by cloning
        const newSelect = historyDateSelect.cloneNode(true);
        historyDateSelect.parentNode.replaceChild(newSelect, historyDateSelect);
        
        // Add our own event listener
        newSelect.addEventListener('change', function() {
            const selectedDate = newSelect.value;
            console.log("History date selected:", selectedDate);
            
            // Enable/disable delete button
            const deleteHistoryBtn = document.getElementById('delete-history-btn');
            if (deleteHistoryBtn) {
                deleteHistoryBtn.disabled = !selectedDate;
            }
            
            // Load history for selected date
            loadHistoryForSelectedDate(selectedDate);
        });
        
        // Load history dates
        loadAllHistoryDates();
        
        console.log("History fix applied");
    }
    
    // Function to load all history dates
    async function loadAllHistoryDates() {
        try {
            console.log("Loading history dates");
            
            const response = await fetch('/fetch_history');
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            
            const data = await response.json();
            const dates = new Set();
            
            if (data.history && Array.isArray(data.history)) {
                data.history.forEach(item => {
                    if (item.timestamp) {
                        const date = new Date(item.timestamp).toISOString().split('T')[0];
                        dates.add(date);
                    }
                });
                
                const historyDateSelect = document.getElementById('history-date-select');
                if (historyDateSelect) {
                    // Clear existing options except "All History"
                    historyDateSelect.innerHTML = '<option value="">All History</option>';
                    
                    // Add date options (sorted newest first)
                    Array.from(dates).sort().reverse().forEach(date => {
                        const option = document.createElement('option');
                        option.value = date;
                        option.textContent = new Date(date).toLocaleDateString();
                        historyDateSelect.appendChild(option);
                    });
                    
                    console.log(`Loaded ${dates.size} history dates`);
                }
            } else {
                console.error("Invalid history data format:", data);
            }
        } catch (error) {
            console.error("Error loading history dates:", error);
        }
    }
    
    // Function to load history for selected date
    async function loadHistoryForSelectedDate(selectedDate) {
        try {
            console.log(`Loading history for date: ${selectedDate || 'all'}`);
            
            const url = selectedDate ? `/fetch_history?date=${selectedDate}` : '/fetch_history';
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            
            const data = await response.json();
            
            // Get chatbox and clear it
            const chatbox = document.getElementById('chatbox');
            if (!chatbox) {
                console.error("Chatbox not found");
                return;
            }
            
            chatbox.innerHTML = '<div id="message-anchor"></div>';
            
            // Display history
            if (data.history && Array.isArray(data.history)) {
                console.log(`Displaying ${data.history.length} history items`);
                
                data.history.forEach(item => {
                    // Create user message
                    const userMsgDiv = document.createElement('div');
                    userMsgDiv.className = 'message user-message';
                    
                    const userContentDiv = document.createElement('div');
                    userContentDiv.className = 'message-content';
                    userContentDiv.textContent = item.user_message;
                    userMsgDiv.appendChild(userContentDiv);
                    
                    if (item.timestamp) {
                        const userTimeSpan = document.createElement('span');
                        userTimeSpan.className = 'timestamp';
                        userTimeSpan.textContent = new Date(item.timestamp).toLocaleString().replace(/:\d{2}\s/, ' ');
                        userMsgDiv.appendChild(userTimeSpan);
                    }
                    
                    chatbox.appendChild(userMsgDiv);
                    
                    // Create bot message
                    const botMsgDiv = document.createElement('div');
                    botMsgDiv.className = 'message bot-message';
                    
                    const botContentDiv = document.createElement('div');
                    botContentDiv.className = 'message-content';
                    
                    // Use marked library to render markdown if available
                    if (window.marked && item.bot_response) {
                        botContentDiv.innerHTML = window.marked.parse(item.bot_response);
                        
                        // Add syntax highlighting to code blocks
                        if (window.hljs) {
                            const codeBlocks = botContentDiv.querySelectorAll('pre code');
                            codeBlocks.forEach(block => {
                                window.hljs.highlightElement(block);
                            });
                        }
                        
                        // Add copy buttons to code blocks
                        const preBlocks = botContentDiv.querySelectorAll('pre');
                        preBlocks.forEach(pre => {
                            if (!pre.querySelector('.copy-button')) {
                                const code = pre.querySelector('code');
                                if (code) {
                                    const copyButton = document.createElement('button');
                                    copyButton.className = 'copy-button';
                                    copyButton.textContent = 'Copy';
                                    copyButton.addEventListener('click', () => {
                                        navigator.clipboard.writeText(code.innerText)
                                            .then(() => {
                                                copyButton.textContent = 'Copied!';
                                                setTimeout(() => {
                                                    copyButton.textContent = 'Copy';
                                                }, 2000);
                                            });
                                    });
                                    pre.appendChild(copyButton);
                                }
                            }
                        });
                    } else {
                        botContentDiv.innerHTML = item.bot_response || '';
                    }
                    
                    botMsgDiv.appendChild(botContentDiv);
                    
                    if (item.timestamp) {
                        const botTimeSpan = document.createElement('span');
                        botTimeSpan.className = 'timestamp';
                        botTimeSpan.textContent = new Date(item.timestamp).toLocaleString().replace(/:\d{2}\s/, ' ');
                        botMsgDiv.appendChild(botTimeSpan);
                    }
                    
                    chatbox.appendChild(botMsgDiv);
                });
                
                // Scroll to bottom
                const messageAnchor = document.getElementById('message-anchor');
                if (messageAnchor) {
                    messageAnchor.scrollIntoView({ behavior: 'smooth' });
                }
            } else {
                console.error("Invalid history data format:", data);
            }
        } catch (error) {
            console.error("Error loading history:", error);
            
            // Show error message in chatbox
            const chatbox = document.getElementById('chatbox');
            if (chatbox) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'message error-message';
                errorDiv.textContent = `Error loading history: ${error.message}`;
                chatbox.appendChild(errorDiv);
            }
        }
    }
    
    // Apply the fix after a short delay
    setTimeout(fixHistoryLoading, 1000);
});
