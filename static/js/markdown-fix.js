// Markdown rendering fix
document.addEventListener('DOMContentLoaded', function() {
    console.log("Markdown fix script loaded");
    
    // Function to apply markdown rendering to all bot messages
    function applyMarkdownRendering() {
        // Check if marked library is available
        if (!window.marked) {
            console.error("Marked library not found, cannot apply markdown rendering");
            return;
        }
        
        // Configure marked options
        marked.setOptions({
            highlight: function(code, lang) {
                if (window.hljs) {
                    const language = window.hljs.getLanguage(lang) ? lang : 'plaintext';
                    return window.hljs.highlight(code, { language }).value;
                }
                return code;
            },
            langPrefix: 'hljs language-',
            breaks: true,
            gfm: true
        });
        
        // Find all bot messages
        const botMessages = document.querySelectorAll('.bot-message .message-content');
        
        botMessages.forEach(function(messageContent) {
            // Get the parent message element
            const messageElement = messageContent.closest('.bot-message');
            
            // Get the raw content (if available) or use the HTML content
            const rawContent = messageElement.dataset.rawContent || messageContent.innerHTML;
            
            // Render markdown
            try {
                messageContent.innerHTML = marked.parse(rawContent);
                
                // Store the raw content for future reference
                messageElement.dataset.rawContent = rawContent;
                
                // Apply syntax highlighting to code blocks
                if (window.hljs) {
                    const codeBlocks = messageContent.querySelectorAll('pre code');
                    codeBlocks.forEach(block => {
                        window.hljs.highlightElement(block);
                    });
                }
                
                // Add copy buttons to code blocks
                const preBlocks = messageContent.querySelectorAll('pre');
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
                
                // Render Mermaid diagrams if available
                if (window.mermaid) {
                    const mermaidDiagrams = messageContent.querySelectorAll('pre code.language-mermaid');
                    mermaidDiagrams.forEach(diagram => {
                        const diagramCode = diagram.textContent;
                        const diagramContainer = document.createElement('div');
                        diagramContainer.className = 'mermaid';
                        diagramContainer.textContent = diagramCode;
                        
                        // Replace the pre element with the diagram container
                        const preElement = diagram.closest('pre');
                        if (preElement && preElement.parentNode) {
                            preElement.parentNode.replaceChild(diagramContainer, preElement);
                        }
                    });
                    
                    // Initialize Mermaid
                    try {
                        window.mermaid.init();
                    } catch (e) {
                        console.error("Error initializing Mermaid:", e);
                    }
                }
            } catch (error) {
                console.error("Error rendering markdown:", error);
            }
        });
    }
    
    // Apply markdown rendering now
    setTimeout(applyMarkdownRendering, 1000);
    
    // Also apply markdown rendering whenever new content is added to the chatbox
    const chatbox = document.getElementById('chatbox');
    if (chatbox) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    // Apply markdown rendering with a slight delay to ensure content is fully loaded
                    setTimeout(applyMarkdownRendering, 100);
                }
            });
        });
        
        observer.observe(chatbox, { childList: true, subtree: true });
    }
    
    // Override the addMessage function to apply markdown rendering
    if (typeof window.addMessage === 'function') {
        const originalAddMessage = window.addMessage;
        
        window.addMessage = function(text, type, timestamp, messageId) {
            const messageDiv = originalAddMessage.apply(this, arguments);
            
            // Apply markdown rendering if this is a bot message
            if (type === 'bot-message') {
                setTimeout(applyMarkdownRendering, 100);
            }
            
            return messageDiv;
        };
        
        console.log("Patched addMessage function");
    }
    
    // Override the addBotMessageChunk function to apply markdown rendering
    if (typeof window.addBotMessageChunk === 'function') {
        const originalAddBotMessageChunk = window.addBotMessageChunk;
        
        window.addBotMessageChunk = function(text, botMessageDiv) {
            originalAddBotMessageChunk.apply(this, arguments);
            
            // Apply markdown rendering
            setTimeout(applyMarkdownRendering, 100);
            
            return botMessageDiv;
        };
        
        console.log("Patched addBotMessageChunk function");
    }
    
    console.log("Markdown fix applied");
});
