// Direct button fix
document.addEventListener('DOMContentLoaded', function() {
    console.log("Button fix script loaded");
    
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
            
            const message = messageInput.value.trim();
            if (!message) {
                console.log("No message to send");
                return;
            }
            
            console.log("Send button clicked, message:", message);
            
            // Disable button and show loading state
            newButton.disabled = true;
            
            // First check if there are any existing conversations
            fetch('/api/conversations')
                .then(response => response.json())
                .then(conversations => {
                    if (conversations && conversations.length > 0) {
                        // Use the first existing conversation
                        window.currentConversationId = conversations[0].id;
                        console.log("Using existing conversation:", window.currentConversationId);
                        sendMessageToServer(message);
                    } else if (!window.currentConversationId) {
                        // Only create a new conversation if none exist and we don't have one
                        console.log("No conversations found, creating new one");
                        fetch('/api/conversations', { method: 'POST' })
                            .then(response => response.json())
                            .then(data => {
                                window.currentConversationId = data.id;
                                console.log("Created new conversation:", window.currentConversationId);
                                sendMessageToServer(message);
                            })
                            .catch(error => {
                                console.error("Error creating conversation:", error);
                                newButton.disabled = false;
                            });
                    } else {
                        // We already have a conversation ID
                        sendMessageToServer(message);
                    }
                })
                .catch(error => {
                    console.error("Error fetching conversations:", error);
                    
                    // Fallback to original behavior
                    if (!window.currentConversationId) {
                        fetch('/api/conversations', { method: 'POST' })
                            .then(response => response.json())
                            .then(data => {
                                window.currentConversationId = data.id;
                                sendMessageToServer(message);
                            })
                            .catch(error => {
                                console.error("Error creating conversation:", error);
                                newButton.disabled = false;
                            });
                    } else {
                        sendMessageToServer(message);
                    }
                });
        });
        
        // Also fix Enter key
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                newButton.click();
            }
        });
        
        function sendMessageToServer(message) {
            // Add user message to UI
            const userMessageDiv = document.createElement('div');
            userMessageDiv.className = 'message user-message';
            userMessageDiv.textContent = message;
            document.getElementById('chatbox').appendChild(userMessageDiv);
            
            // Clear input
            messageInput.value = '';
            
            // Prepare request
            const requestBody = {
                message: message,
                conversation_id: window.currentConversationId,
                model_name: document.getElementById('model-select')?.value || 'gemini-2.5-flash',
                active_context: window.activeContextItems || []
            };
            
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
                
                // Create bot message container
                const botMessageDiv = document.createElement('div');
                botMessageDiv.className = 'message bot-message';
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                botMessageDiv.appendChild(contentDiv);
                document.getElementById('chatbox').appendChild(botMessageDiv);
                
                // Process stream
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                
                function readStream() {
                    return reader.read().then(({ value, done }) => {
                        if (done) {
                            console.log("Stream complete");
                            newButton.disabled = false;
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
                                        // Store raw content for accumulation
                                        const currentContent = botMessageDiv.dataset.rawContent || '';
                                        const newContent = currentContent + data.text;
                                        botMessageDiv.dataset.rawContent = newContent;
                                        
                                        // Use marked library to render markdown
                                        if (window.marked) {
                                            contentDiv.innerHTML = window.marked.parse(newContent);
                                            
                                            // Add syntax highlighting to code blocks
                                            if (window.hljs) {
                                                const codeBlocks = contentDiv.querySelectorAll('pre code');
                                                codeBlocks.forEach(block => {
                                                    window.hljs.highlightElement(block);
                                                });
                                            }
                                            
                                            // Add copy buttons to code blocks
                                            const preBlocks = contentDiv.querySelectorAll('pre');
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
                                            // Fallback if marked library is not available
                                            contentDiv.innerHTML += data.text;
                                        }
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
                newButton.disabled = false;
            });
        }
    }
    
    // Initialize activeContextItems if needed
    if (typeof window.activeContextItems === 'undefined') {
        window.activeContextItems = [];
    }
    
    // Apply the fix
    setTimeout(fixSendButton, 500); // Slight delay to ensure DOM is ready
});
