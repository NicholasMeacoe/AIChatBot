// Core fix for chat functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log("Core fix script loaded");
    
    // Global variables
    let isSubmitting = false;
    let submissionTimeout = null;
    
    // Function to fix the send button
    function fixSendButton() {
        const sendButton = document.getElementById('send-button');
        const messageInput = document.getElementById('message-input');
        
        if (!sendButton || !messageInput) {
            console.error("Send button or message input not found");
            return;
        }
        
        console.log("Found send button, applying fix");
        
        // Remove existing event listeners by cloning
        const newButton = sendButton.cloneNode(true);
        sendButton.parentNode.replaceChild(newButton, sendButton);
        
        // Add our own event listener
        newButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Prevent duplicate submissions
            if (isSubmitting) {
                console.log("Already submitting, ignoring click");
                return;
            }
            
            const message = messageInput.value.trim();
            if (!message) {
                console.log("No message to send");
                return;
            }
            
            // Set submission lock
            isSubmitting = true;
            newButton.disabled = true;
            
            // Clear submission lock after timeout (safety measure)
            clearTimeout(submissionTimeout);
            submissionTimeout = setTimeout(() => {
                isSubmitting = false;
                newButton.disabled = false;
            }, 10000); // 10 second timeout
            
            console.log("Sending message:", message);
            
            // Get or create conversation
            ensureConversation().then(conversationId => {
                if (!conversationId) {
                    console.error("Failed to get or create conversation");
                    isSubmitting = false;
                    newButton.disabled = false;
                    return;
                }
                
                // Add user message to UI
                addUserMessage(message);
                
                // Clear input
                messageInput.value = '';
                
                // Send message to server
                sendMessageToServer(message, conversationId, newButton);
            });
        });
        
        // Fix Enter key
        const newInput = messageInput.cloneNode(true);
        messageInput.parentNode.replaceChild(newInput, messageInput);
        
        newInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                newButton.click();
            }
        });
    }
    
    // Function to ensure we have a conversation ID
    async function ensureConversation() {
        // Check if we already have a conversation ID
        if (window.currentConversationId) {
            return window.currentConversationId;
        }
        
        try {
            // Check for existing conversations
            const response = await fetch('/api/conversations');
            const conversations = await response.json();
            
            if (conversations && conversations.length > 0) {
                // Use the first existing conversation
                window.currentConversationId = conversations[0].id;
                console.log("Using existing conversation:", window.currentConversationId);
                return window.currentConversationId;
            }
            
            // Create a new conversation
            const createResponse = await fetch('/api/conversations', { method: 'POST' });
            const data = await createResponse.json();
            window.currentConversationId = data.id;
            console.log("Created new conversation:", window.currentConversationId);
            return window.currentConversationId;
        } catch (error) {
            console.error("Error ensuring conversation:", error);
            return null;
        }
    }
    
    // Function to add user message to UI
    function addUserMessage(message) {
        const chatbox = document.getElementById('chatbox');
        if (!chatbox) return;
        
        const userDiv = document.createElement('div');
        userDiv.className = 'message user-message';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = message;
        userDiv.appendChild(contentDiv);
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'timestamp';
        timeSpan.textContent = new Date().toLocaleString().replace(/:\d{2}\s/, ' ');
        userDiv.appendChild(timeSpan);
        
        chatbox.appendChild(userDiv);
        
        // Scroll to bottom
        chatbox.scrollTop = chatbox.scrollHeight;
    }
    
    // Function to send message to server
    function sendMessageToServer(message, conversationId, sendButton) {
        // Prepare request
        const requestBody = {
            message: message,
            conversation_id: conversationId,
            model_name: document.getElementById('model-select')?.value || 'gemini-2.5-flash',
            active_context: window.activeContextItems || []
        };
        
        // Create bot message container
        const chatbox = document.getElementById('chatbox');
        const botDiv = document.createElement('div');
        botDiv.className = 'message bot-message';
        botDiv.dataset.rawContent = '';
        
        const botContentDiv = document.createElement('div');
        botContentDiv.className = 'message-content';
        botDiv.appendChild(botContentDiv);
        
        chatbox.appendChild(botDiv);
        
        const botTimeSpan = document.createElement('span');
        botTimeSpan.className = 'timestamp';
        botTimeSpan.textContent = new Date().toLocaleString().replace(/:\d{2}\s/, ' ');
        botDiv.appendChild(botTimeSpan);
        
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
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            
            // Process stream
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            function readStream() {
                return reader.read().then(({ value, done }) => {
                    if (done) {
                        console.log("Stream complete");
                        isSubmitting = false;
                        if (sendButton) sendButton.disabled = false;
                        clearTimeout(submissionTimeout);
                        return;
                    }
                    
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n\n');
                    
                    for (let i = 0; i < lines.length - 1; i++) {
                        const line = lines[i];
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.substring(6));
                                if (data.text) {
                                    // Accumulate raw content
                                    const currentContent = botDiv.dataset.rawContent || '';
                                    const newContent = currentContent + data.text;
                                    botDiv.dataset.rawContent = newContent;
                                    
                                    // Render with markdown if available
                                    if (window.marked) {
                                        botContentDiv.innerHTML = window.marked.parse(newContent);
                                        
                                        // Apply syntax highlighting if available
                                        if (window.hljs) {
                                            const codeBlocks = botContentDiv.querySelectorAll('pre code');
                                            codeBlocks.forEach(block => {
                                                try {
                                                    window.hljs.highlightElement(block);
                                                } catch (e) {
                                                    // Ignore highlighting errors
                                                }
                                            });
                                        }
                                    } else {
                                        botContentDiv.innerHTML += data.text;
                                    }
                                    
                                    // Scroll to bottom
                                    chatbox.scrollTop = chatbox.scrollHeight;
                                }
                            } catch (e) {
                                console.error("Error parsing chunk:", e);
                            }
                        }
                    }
                    
                    buffer = lines[lines.length - 1];
                    return readStream();
                });
            }
            
            return readStream();
        })
        .catch(error => {
            console.error("Error sending message:", error);
            botContentDiv.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
            isSubmitting = false;
            if (sendButton) sendButton.disabled = false;
            clearTimeout(submissionTimeout);
        });
    }
    
    // Initialize activeContextItems if needed
    if (typeof window.activeContextItems === 'undefined') {
        window.activeContextItems = [];
    }
    
    // Apply the fix after a short delay
    setTimeout(fixSendButton, 1000);
    
    console.log("Core fix applied");
});
