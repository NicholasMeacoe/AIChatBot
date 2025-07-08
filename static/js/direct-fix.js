// Direct fix for the send button
document.addEventListener('DOMContentLoaded', function() {
    console.log("Direct fix script loaded");
    
    // Get the send button element
    const sendButton = document.getElementById('send-button');
    
    if (!sendButton) {
        console.error("Send button not found!");
        return;
    }
    
    console.log("Send button found, adding direct event listener");
    
    // Remove any existing event listeners (not perfect but helps)
    sendButton.replaceWith(sendButton.cloneNode(true));
    
    // Get the fresh reference
    const newSendButton = document.getElementById('send-button');
    
    // Add our direct event listener
    newSendButton.addEventListener('click', function(event) {
        console.log("Send button clicked directly");
        event.preventDefault();
        
        // Initialize activeContextItems if needed
        if (typeof window.activeContextItems === 'undefined') {
            window.activeContextItems = [];
        }
        
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        
        if (!message) {
            console.log('No message to send');
            return;
        }
        
        // Get the model select element
        const modelSelect = document.getElementById('model-select');
        const selectedModel = modelSelect ? modelSelect.value : 'gemini-2.5-flash';
        
        // Get the conversation ID
        if (!window.currentConversationId) {
            console.log('Creating new conversation first');
            // We'll need to create a conversation first
            fetch('/api/conversations', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    window.currentConversationId = data.id;
                    console.log("Created conversation:", window.currentConversationId);
                    sendMessageToServer(message, window.currentConversationId, selectedModel);
                })
                .catch(error => {
                    console.error("Error creating conversation:", error);
                    addMessage('Error: Could not create conversation', 'error-message');
                });
        } else {
            sendMessageToServer(message, window.currentConversationId, selectedModel);
        }
    });
    
    // Function to send the message to the server
    function sendMessageToServer(message, conversationId, modelName) {
        console.log(`Sending message to server: "${message}" for conversation: ${conversationId}`);
        
        // Display user message
        const userMessageDiv = addMessage(message, 'user-message', new Date());
        messageInput.value = '';
        
        // Disable send button and show thinking indicator
        newSendButton.disabled = true;
        const stopButton = document.getElementById('stop-button');
        const thinkingIndicator = document.getElementById('thinking');
        
        if (stopButton) stopButton.style.display = 'inline-block';
        if (thinkingIndicator) thinkingIndicator.style.display = 'inline';
        newSendButton.style.display = 'none';
        
        // Create abort controller for cancellation
        window.abortController = new AbortController();
        const signal = window.abortController.signal;
        
        // Prepare request body
        const requestBody = {
            message: message,
            conversation_id: conversationId,
            model_name: modelName,
            active_context: window.activeContextItems || []
        };
        
        console.log("Request body:", requestBody);
        
        // Send the request
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            },
            body: JSON.stringify(requestBody),
            signal: signal
        })
        .then(response => {
            console.log("Response received:", response.status);
            
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `HTTP error ${response.status}`);
                });
            }
            
            if (!response.body || !response.headers.get('content-type')?.includes('text/event-stream')) {
                throw new Error('Expected streaming response but received something else');
            }
            
            // Create bot message container
            const messageAnchor = document.getElementById('message-anchor');
            const chatbox = document.getElementById('chatbox');
            
            const botMessageDiv = document.createElement('div');
            botMessageDiv.classList.add('message', 'bot-message');
            botMessageDiv.dataset.rawContent = '';
            
            const contentDiv = document.createElement('div');
            contentDiv.classList.add('message-content');
            botMessageDiv.appendChild(contentDiv);
            
            if (chatbox && messageAnchor) {
                chatbox.insertBefore(botMessageDiv, messageAnchor);
            } else {
                console.error("Chatbox or message anchor not found");
                document.body.appendChild(botMessageDiv); // Fallback
            }
            
            const timeSpan = document.createElement('span');
            timeSpan.classList.add('timestamp');
            timeSpan.textContent = new Date().toLocaleString().replace(/:\d{2}\s/, ' ');
            botMessageDiv.appendChild(timeSpan);
            
            // Process the stream
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            function readStream() {
                return reader.read().then(({ value, done }) => {
                    if (done) {
                        console.log('Stream finished');
                        return;
                    }
                    
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n\n');
                    
                    for (let i = 0; i < lines.length - 1; i++) {
                        const line = lines[i];
                        if (line.startsWith('data: ')) {
                            try {
                                const jsonData = JSON.parse(line.substring(6));
                                
                                if (jsonData.text) {
                                    // Add text to the bot message
                                    const currentContent = botMessageDiv.dataset.rawContent || '';
                                    const newContent = currentContent + jsonData.text;
                                    botMessageDiv.dataset.rawContent = newContent;
                                    contentDiv.innerHTML = marked.parse(newContent);
                                    
                                    // Add copy buttons to code blocks
                                    const codeBlocks = contentDiv.querySelectorAll('pre');
                                    codeBlocks.forEach(pre => {
                                        if (!pre.querySelector('.copy-button')) {
                                            const code = pre.querySelector('code');
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
                                    });
                                    
                                    if (messageAnchor) messageAnchor.scrollIntoView({ behavior: 'smooth' });
                                } else if (jsonData.context_error) {
                                    addMessage(`Context Warning: ${jsonData.context_error}`, 'context-warning', new Date());
                                } else if (jsonData.error) {
                                    addMessage(`Stream Error: ${jsonData.error}`, 'error-message', new Date());
                                }
                            } catch (e) {
                                console.error('Error parsing SSE data:', e, 'Raw line:', line);
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
            console.error('Fetch error:', error);
            if (error.name !== 'AbortError') {
                addMessage(`Error: ${error.message}`, 'error-message', new Date());
            } else {
                addMessage('Request was cancelled', 'error-message', new Date());
            }
        })
        .finally(() => {
            // Re-enable send button and hide thinking indicator
            newSendButton.disabled = false;
            newSendButton.style.display = 'inline-block';
            if (stopButton) stopButton.style.display = 'none';
            if (thinkingIndicator) thinkingIndicator.style.display = 'none';
            window.abortController = null;
            
            const messageAnchor = document.getElementById('message-anchor');
            if (messageAnchor) messageAnchor.scrollIntoView({ behavior: 'smooth' });
        });
    }
    
    console.log("Direct fix applied successfully");
});
