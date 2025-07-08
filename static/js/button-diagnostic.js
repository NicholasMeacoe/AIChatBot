// Button diagnostic script
console.log("=== BUTTON DIAGNOSTIC SCRIPT LOADED ===");

// Function to run diagnostics
function runButtonDiagnostics() {
    console.log("Running button diagnostics...");
    
    // Check if key elements exist
    const sendButton = document.getElementById('send-button');
    const messageInput = document.getElementById('message-input');
    const stopButton = document.getElementById('stop-button');
    const chatbox = document.getElementById('chatbox');
    
    console.log("Send button exists:", !!sendButton);
    console.log("Message input exists:", !!messageInput);
    console.log("Stop button exists:", !!stopButton);
    console.log("Chatbox exists:", !!chatbox);
    
    if (sendButton) {
        console.log("Send button properties:", {
            disabled: sendButton.disabled,
            display: sendButton.style.display,
            classList: Array.from(sendButton.classList),
            parentNode: sendButton.parentNode.tagName
        });
        
        // Check for event listeners (indirect method)
        const clone = sendButton.cloneNode(true);
        const parent = sendButton.parentNode;
        
        // Add a direct click handler that will definitely work
        clone.addEventListener('click', function(e) {
            console.log("DIRECT CLICK HANDLER TRIGGERED");
            e.preventDefault();
            e.stopPropagation();
            
            // Show a visual indicator that the button was clicked
            document.body.style.backgroundColor = '#ffdddd';
            setTimeout(() => {
                document.body.style.backgroundColor = '';
            }, 500);
            
            // Try to send a message directly
            sendMessageDirect();
            
            return false;
        });
        
        // Replace the button
        parent.replaceChild(clone, sendButton);
        console.log("Replaced send button with direct handler");
    }
    
    // Check global variables
    console.log("currentConversationId:", typeof window.currentConversationId !== 'undefined' ? window.currentConversationId : 'undefined');
    console.log("activeContextItems:", typeof window.activeContextItems !== 'undefined' ? window.activeContextItems : 'undefined');
    console.log("abortController:", typeof window.abortController !== 'undefined' ? 'exists' : 'undefined');
    
    // Check if sendMessage function exists
    console.log("sendMessage function exists:", typeof window.sendMessage === 'function');
    
    // Add a global direct send function
    window.sendMessageDirect = function() {
        console.log("Direct send function called");
        
        const messageInput = document.getElementById('message-input');
        if (!messageInput) {
            console.error("Message input not found!");
            return;
        }
        
        const message = messageInput.value.trim();
        if (!message) {
            console.log("No message to send");
            return;
        }
        
        console.log(`Attempting to send message: "${message}"`);
        
        // Create a conversation if needed
        if (!window.currentConversationId) {
            console.log("No conversation ID, creating one...");
            fetch('/api/conversations', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    console.log("Created conversation:", data);
                    window.currentConversationId = data.id;
                    performSend(message, data.id);
                })
                .catch(error => {
                    console.error("Error creating conversation:", error);
                    alert("Error: Could not create conversation. See console for details.");
                });
        } else {
            performSend(message, window.currentConversationId);
        }
    };
    
    // Function to perform the actual send
    function performSend(message, conversationId) {
        console.log(`Sending message "${message}" to conversation ${conversationId}`);
        
        // Show user message
        const chatbox = document.getElementById('chatbox');
        const userDiv = document.createElement('div');
        userDiv.className = 'message user-message';
        userDiv.textContent = message;
        chatbox.appendChild(userDiv);
        
        // Clear input
        document.getElementById('message-input').value = '';
        
        // Prepare request
        const requestBody = {
            message: message,
            conversation_id: conversationId,
            model_name: document.getElementById('model-select')?.value || 'gemini-2.5-flash',
            active_context: window.activeContextItems || []
        };
        
        console.log("Request body:", requestBody);
        
        // Send request
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            },
            body: JSON.stringify(requestBody)
        })
        .then(response => {
            console.log("Response received:", response.status);
            
            if (!response.ok) {
                return response.text().then(text => {
                    console.error("Error response:", text);
                    throw new Error(`Server error: ${response.status}`);
                });
            }
            
            // Handle streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            // Create bot message container
            const botDiv = document.createElement('div');
            botDiv.className = 'message bot-message';
            const botContent = document.createElement('div');
            botContent.className = 'message-content';
            botDiv.appendChild(botContent);
            chatbox.appendChild(botDiv);
            
            // Read the stream
            function readStream() {
                return reader.read().then(({ value, done }) => {
                    if (done) {
                        console.log("Stream complete");
                        return;
                    }
                    
                    const chunk = decoder.decode(value, { stream: true });
                    console.log("Received chunk:", chunk);
                    
                    // Process the chunk (simplified)
                    const lines = chunk.split('\n\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.substring(6));
                                if (data.text) {
                                    botContent.innerHTML += data.text;
                                }
                            } catch (e) {
                                console.error("Error parsing chunk:", e);
                            }
                        }
                    }
                    
                    // Continue reading
                    return readStream();
                });
            }
            
            return readStream();
        })
        .catch(error => {
            console.error("Fetch error:", error);
            alert("Error sending message. See console for details.");
        });
    }
    
    // Add keyboard handler for Enter key
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                console.log("Enter key pressed");
                e.preventDefault();
                window.sendMessageDirect();
            }
        });
        console.log("Added direct Enter key handler");
    }
    
    console.log("Button diagnostics complete");
}

// Run diagnostics when the page is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded, running diagnostics...");
    setTimeout(runButtonDiagnostics, 1000); // Slight delay to ensure everything is loaded
});

// Also run diagnostics now in case DOMContentLoaded already fired
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    console.log("Document already loaded, running diagnostics immediately...");
    setTimeout(runButtonDiagnostics, 100);
}

console.log("=== BUTTON DIAGNOSTIC SCRIPT SETUP COMPLETE ===");
