// Streamlined rendering fix
document.addEventListener('DOMContentLoaded', function() {
    console.log("Streamlined rendering fix loaded");
    
    // Fix for clipping and rendering issues
    function fixRenderingIssues() {
        // 1. Fix chatbox height and scrolling
        const chatbox = document.getElementById('chatbox');
        if (chatbox) {
            // Ensure chatbox has proper height and overflow settings
            chatbox.style.maxHeight = 'calc(100vh - 300px)';
            chatbox.style.overflowY = 'auto';
            chatbox.style.overflowX = 'hidden';
            
            // Fix any clipping issues with message content
            const messages = chatbox.querySelectorAll('.message');
            messages.forEach(message => {
                const content = message.querySelector('.message-content');
                if (content) {
                    content.style.wordBreak = 'break-word';
                    content.style.overflowWrap = 'break-word';
                    
                    // Fix code blocks that might be causing clipping
                    const codeBlocks = content.querySelectorAll('pre');
                    codeBlocks.forEach(pre => {
                        pre.style.maxWidth = '100%';
                        pre.style.overflowX = 'auto';
                        pre.style.whiteSpace = 'pre-wrap';
                    });
                }
            });
        }
        
        // 2. Fix markdown rendering
        fixMarkdownRendering();
    }
    
    // Simplified markdown rendering fix
    function fixMarkdownRendering() {
        // Only proceed if marked library is available
        if (!window.marked) {
            console.warn("Marked library not found, skipping markdown rendering");
            return;
        }
        
        // Configure marked options
        marked.setOptions({
            breaks: true,
            gfm: true
        });
        
        // Find all bot messages
        const botMessages = document.querySelectorAll('.bot-message .message-content');
        
        botMessages.forEach(function(contentDiv) {
            try {
                // Get the raw content if available
                const messageDiv = contentDiv.closest('.bot-message');
                const rawContent = messageDiv && messageDiv.dataset.rawContent;
                
                if (rawContent) {
                    // Render markdown
                    contentDiv.innerHTML = marked.parse(rawContent);
                    
                    // Apply syntax highlighting
                    if (window.hljs) {
                        const codeBlocks = contentDiv.querySelectorAll('pre code');
                        codeBlocks.forEach(block => {
                            try {
                                window.hljs.highlightElement(block);
                            } catch (e) {
                                console.warn("Error highlighting code block:", e);
                            }
                        });
                    }
                }
            } catch (error) {
                console.error("Error rendering markdown:", error);
            }
        });
    }
    
    // Override the addBotMessageChunk function to fix streaming rendering
    if (typeof window.addBotMessageChunk === 'function') {
        const originalAddBotMessageChunk = window.addBotMessageChunk;
        
        window.addBotMessageChunk = function(text, botMessageDiv) {
            try {
                // Get the content div
                const contentDiv = botMessageDiv.querySelector('.message-content');
                if (!contentDiv) return;
                
                // Store raw content for accumulation
                const currentContent = botMessageDiv.dataset.rawContent || '';
                const newContent = currentContent + text;
                botMessageDiv.dataset.rawContent = newContent;
                
                // Use marked to render markdown if available
                if (window.marked) {
                    contentDiv.innerHTML = marked.parse(newContent);
                    
                    // Apply syntax highlighting
                    if (window.hljs) {
                        const codeBlocks = contentDiv.querySelectorAll('pre code');
                        codeBlocks.forEach(block => {
                            try {
                                window.hljs.highlightElement(block);
                            } catch (e) {
                                // Ignore highlighting errors during streaming
                            }
                        });
                    }
                } else {
                    // Fallback to original function
                    return originalAddBotMessageChunk.apply(this, arguments);
                }
                
                // Ensure proper scrolling
                const messageAnchor = document.getElementById('message-anchor');
                if (messageAnchor) {
                    messageAnchor.scrollIntoView({ behavior: 'smooth' });
                }
            } catch (error) {
                console.error("Error in addBotMessageChunk:", error);
                // Fallback to original function
                return originalAddBotMessageChunk.apply(this, arguments);
            }
        };
        
        console.log("Patched addBotMessageChunk function for better rendering");
    }
    
    // Apply fixes now
    fixRenderingIssues();
    
    // Also apply fixes whenever the DOM changes
    const observer = new MutationObserver(function(mutations) {
        fixRenderingIssues();
    });
    
    // Start observing the chatbox
    const chatbox = document.getElementById('chatbox');
    if (chatbox) {
        observer.observe(chatbox, { 
            childList: true, 
            subtree: true,
            characterData: true,
            attributes: true
        });
    }
    
    // Add CSS fixes for rendering issues
    const style = document.createElement('style');
    style.textContent = `
        #chatbox {
            max-height: calc(100vh - 300px);
            overflow-y: auto;
            overflow-x: hidden;
        }
        
        .message-content {
            word-break: break-word;
            overflow-wrap: break-word;
        }
        
        .message-content pre {
            max-width: 100%;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        
        .message-content code {
            white-space: pre-wrap;
        }
        
        .message-content img {
            max-width: 100%;
            height: auto;
        }
        
        .message-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        
        .message-content th, .message-content td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        .message-content blockquote {
            border-left: 4px solid #ddd;
            padding-left: 10px;
            margin-left: 0;
            color: #666;
        }
    `;
    document.head.appendChild(style);
    
    console.log("Rendering fixes applied");
});
