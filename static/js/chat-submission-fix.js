// Comprehensive Chat Submission Fix
document.addEventListener('DOMContentLoaded', function() {
    console.log("Chat submission fix loaded");
    
    // Global state management
    window.chatState = {
        isSubmitting: false,
        currentConversationId: null,
        abortController: null,
        messageQueue: [],
        retryCount: 0,
        maxRetries: 3
    };
    
    // Initialize activeContextItems if not defined
    if (typeof window.activeContextItems === 'undefined') {
        window.activeContextItems = [];
    }
    
    // Function to get or create conversation
    async function ensureConversation() {
        if (window.chatState.currentConversationId) {
            return window.chatState.currentConversationId;
        }
        
        try {
            console.log("Checking for existing conversations...");
            
            // First, try to get existing conversations
            const listResponse = await fetch('/api/conversations', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (listResponse.ok) {
                const conversations = await listResponse.json();
                if (conversations && conversations.length > 0) {
                    window.chatState.currentConversationId = conversations[0].id;
                    console.log("Using existing conversation:", window.chatState.currentConversationId);
                    return window.chatState.currentConversationId;
                }
            }
            
            // Create new conversation if none exist
            console.log("Creating new conversation...");
            const createResponse = await fetch('/api/conversations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    system_prompt: document.getElementById('system-prompt-input')?.value || '',
                    model: document.getElementById('model-select')?.value || 'gemini-2.5-flash'
                })
            });
            
            if (!createResponse.ok) {
                throw new Error(`Failed to create conversation: ${createResponse.status}`);
            }
            
            const data = await createResponse.json();
            window.chatState.currentConversationId = data.id;
            console.log("Created new conversation:", window.chatState.currentConversationId);
            return window.chatState.currentConversationId;
            
        } catch (error) {
            console.error("Error ensuring conversation:", error);
            throw error;
        }
    }
    
    // Function to validate message before sending
    function validateMessage(message) {
        if (!message || typeof message !== 'string') {
            throw new Error("Message must be a non-empty string");
        }
        
        if (message.trim().length === 0) {
            throw new Error("Message cannot be empty");
        }
        
        if (message.length > 10000) {
            throw new Error("Message is too long (max 10,000 characters)");
        }
        
        return message.trim();
    }
    
    // Function to prepare request payload
    function prepareRequestPayload(message, conversationId) {
        const modelSelect = document.getElementById('model-select');
        const selectedModel = modelSelect ? modelSelect.value : 'gemini-2.5-flash';
        
        // Validate model selection
        if (!selectedModel) {
            throw new Error("No model selected");
        }
        
        return {
            message: message,
            conversation_id: conversationId,
            model_name: selectedModel,
            active_context: window.activeContextItems || []
        };
    }
    
    // Function to add user message to UI
    function addUserMessage(message) {
        const chatbox = document.getElementById('chatbox');
        if (!chatbox) {
            throw new Error("Chatbox not found");
        }
        
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
        chatbox.scrollTop = chatbox.scrollHeight;
        
        return userDiv;
    }
    
    // Function to create bot message container
    function createBotMessageContainer() {
        const chatbox = document.getElementById('chatbox');
        if (!chatbox) {
            throw new Error("Chatbox not found");
        }
        
        const botDiv = document.createElement('div');
        botDiv.className = 'message bot-message';
        botDiv.dataset.rawContent = '';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        botDiv.appendChild(contentDiv);
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'timestamp';
        timeSpan.textContent = new Date().toLocaleString().replace(/:\d{2}\s/, ' ');
        botDiv.appendChild(timeSpan);
        
        chatbox.appendChild(botDiv);
        chatbox.scrollTop = chatbox.scrollHeight;
        
        return { botDiv, contentDiv };
    }
    
    // Function to process streaming response
    async function processStreamingResponse(response, botDiv, contentDiv) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullResponse = '';
        
        try {
            while (true) {
                const { value, done } = await reader.read();
                
                if (done) {
                    console.log("Stream completed");
                    break;
                }
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                
                // Process all complete lines
                for (let i = 0; i < lines.length - 1; i++) {
                    const line = lines[i].trim();
                    if (line.startsWith('data: ')) {
                        try {
                            const jsonData = line.substring(6);
                            if (jsonData === '[DONE]') {
                                console.log("Stream marked as done");
                                return fullResponse;
                            }
                            
                            const data = JSON.parse(jsonData);
                            
                            if (data.text) {
                                fullResponse += data.text;
                                botDiv.dataset.rawContent = fullResponse;
                                
                                // Render with markdown if available
                                if (window.marked) {
                                    contentDiv.innerHTML = window.marked.parse(fullResponse);
                                    
                                    // Apply syntax highlighting
                                    if (window.hljs) {
                                        const codeBlocks = contentDiv.querySelectorAll('pre code');
                                        codeBlocks.forEach(block => {
                                            try {
                                                window.hljs.highlightElement(block);
                                            } catch (e) {
                                                console.warn("Error highlighting code:", e);
                                            }
                                        });
                                    }
                                } else {
                                    contentDiv.textContent = fullResponse;
                                }
                                
                                // Scroll to bottom
                                const chatbox = document.getElementById('chatbox');
                                if (chatbox) {
                                    chatbox.scrollTop = chatbox.scrollHeight;
                                }
                            } else if (data.error) {
                                throw new Error(data.error);
                            } else if (data.context_error) {
                                console.warn("Context error:", data.context_error);
                                // You might want to display this to the user
                            }
                        } catch (e) {
                            console.error("Error parsing SSE data:", e, "Raw line:", line);
                        }
                    }
                }
                
                // Keep the last incomplete line in the buffer
                buffer = lines[lines.length - 1];
            }
            
            return fullResponse;
        } catch (error) {
            console.error("Error processing stream:", error);
            throw error;
        }
    }
    
    // Main function to send message
    async function sendMessage(message) {
        // Prevent multiple simultaneous submissions
        if (window.chatState.isSubmitting) {
            console.log("Already submitting, ignoring request");
            return;
        }
        
        try {
            // Set submitting state
            window.chatState.isSubmitting = true;
            window.chatState.retryCount = 0;
            
            // Validate message
            const validatedMessage = validateMessage(message);
            
            // Disable send button
            const sendButton = document.getElementById('send-button');
            if (sendButton) {
                sendButton.disabled = true;
            }
            
            // Add user message to UI
            addUserMessage(validatedMessage);
            
            // Clear input
            const messageInput = document.getElementById('message-input');
            if (messageInput) {
                messageInput.value = '';
            }
            
            // Ensure we have a conversation
            const conversationId = await ensureConversation();
            
            // Prepare request payload
            const requestPayload = prepareRequestPayload(validatedMessage, conversationId);
            console.log("Sending request:", requestPayload);
            
            // Create bot message container
            const { botDiv, contentDiv } = createBotMessageContainer();
            
            // Create abort controller for cancellation
            window.chatState.abortController = new AbortController();
            
            // Send request to server
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream'
                },
                body: JSON.stringify(requestPayload),
                signal: window.chatState.abortController.signal
            });
            
            if (!response.ok) {
                let errorMessage = `HTTP error ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (e) {
                    // Response might not be JSON
                }
                throw new Error(errorMessage);
            }
            
            // Check if response is actually a stream
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('text/event-stream')) {
                throw new Error('Expected streaming response but received: ' + contentType);
            }
            
            // Process streaming response
            const fullResponse = await processStreamingResponse(response, botDiv, contentDiv);
            console.log("Message sent successfully, full response length:", fullResponse.length);
            
        } catch (error) {
            console.error("Error sending message:", error);
            
            // Show error message to user
            const chatbox = document.getElementById('chatbox');
            if (chatbox) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'message bot-message error-message';
                errorDiv.innerHTML = `<div class="message-content">Error: ${error.message}</div>`;
                chatbox.appendChild(errorDiv);
                chatbox.scrollTop = chatbox.scrollHeight;
            }
            
            // Retry logic for certain errors
            if (window.chatState.retryCount < window.chatState.maxRetries && 
                (error.message.includes('network') || error.message.includes('timeout'))) {
                
                window.chatState.retryCount++;
                console.log(`Retrying message (attempt ${window.chatState.retryCount}/${window.chatState.maxRetries})`);
                
                setTimeout(() => {
                    window.chatState.isSubmitting = false;
                    sendMessage(message);
                }, 2000 * window.chatState.retryCount); // Exponential backoff
                
                return;
            }
            
        } finally {
            // Reset state
            window.chatState.isSubmitting = false;
            window.chatState.abortController = null;
            
            // Re-enable send button
            const sendButton = document.getElementById('send-button');
            if (sendButton) {
                sendButton.disabled = false;
            }
        }
    }
    
    // Function to setup send button
    function setupSendButton() {
        const sendButton = document.getElementById('send-button');
        const messageInput = document.getElementById('message-input');
        
        if (!sendButton || !messageInput) {
            console.error("Send button or message input not found");
            return;
        }
        
        // Remove existing event listeners by cloning
        const newButton = sendButton.cloneNode(true);
        sendButton.parentNode.replaceChild(newButton, sendButton);
        
        const newInput = messageInput.cloneNode(true);
        messageInput.parentNode.replaceChild(newInput, messageInput);
        
        // Add click event listener
        newButton.addEventListener('click', function(e) {
            e.preventDefault();
            const message = newInput.value.trim();
            if (message) {
                sendMessage(message);
            }
        });
        
        // Add Enter key listener
        newInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const message = newInput.value.trim();
                if (message) {
                    sendMessage(message);
                }
            }
        });
        
        console.log("Send button and input setup complete");
    }
    
    // Function to setup stop button
    function setupStopButton() {
        const stopButton = document.getElementById('stop-button');
        if (stopButton) {
            stopButton.addEventListener('click', function() {
                if (window.chatState.abortController) {
                    window.chatState.abortController.abort();
                    console.log("Request aborted by user");
                }
            });
        }
    }
    
    // Initialize everything
    function initialize() {
        setupSendButton();
        setupStopButton();
        
        // Initialize conversation on page load
        setTimeout(() => {
            ensureConversation().catch(error => {
                console.error("Failed to initialize conversation:", error);
            });
        }, 1000);
        
        console.log("Chat submission fix initialized");
    }
    
    // Run initialization
    initialize();
    
    // Expose sendMessage function globally for debugging
    window.debugSendMessage = sendMessage;
});
