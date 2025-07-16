// Improved Markdown Rendering Fix
document.addEventListener('DOMContentLoaded', function() {
    console.log("Improved rendering fix loaded");
    
    // Configure marked options for optimal rendering
    if (window.marked) {
        marked.setOptions({
            breaks: true,           // Add line breaks when encountering \n
            gfm: true,              // Use GitHub Flavored Markdown
            headerIds: true,        // Generate IDs for headings
            mangle: false,          // Don't mangle header IDs
            pedantic: false,        // Don't be pedantic about markdown spec
            sanitize: false,        // Don't sanitize HTML (allows custom elements)
            smartLists: true,       // Use smarter list behavior
            smartypants: true,      // Use smart typography like quotes and dashes
            xhtml: false,           // Don't use XHTML compliant output
            highlight: function(code, lang) {
                if (window.hljs && lang) {
                    try {
                        if (hljs.getLanguage(lang)) {
                            return hljs.highlight(code, { language: lang }).value;
                        }
                    } catch (e) {
                        console.warn("Error highlighting:", e);
                    }
                }
                return code; // Return original code if highlighting fails
            }
        });
        console.log("Configured marked with optimal settings");
    } else {
        console.warn("Marked library not found, markdown rendering will be limited");
    }
    
    // Function to properly render markdown in a message
    function renderMarkdown(messageElement) {
        if (!window.marked) return;
        
        try {
            // Get the content element
            const contentElement = messageElement.querySelector('.message-content');
            if (!contentElement) return;
            
            // Get raw content from dataset or from the element itself
            const rawContent = messageElement.dataset.rawContent || contentElement.innerHTML;
            if (!rawContent) return;
            
            // Store raw content in dataset for future reference
            messageElement.dataset.rawContent = rawContent;
            
            // Render markdown
            contentElement.innerHTML = marked.parse(rawContent);
            
            // Apply syntax highlighting to code blocks
            if (window.hljs) {
                const codeBlocks = contentElement.querySelectorAll('pre code');
                codeBlocks.forEach(block => {
                    try {
                        hljs.highlightElement(block);
                    } catch (e) {
                        console.warn("Error highlighting code block:", e);
                    }
                });
            }
            
            // Add copy buttons to code blocks
            const preBlocks = contentElement.querySelectorAll('pre');
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
                try {
                    // Find all mermaid code blocks
                    const mermaidBlocks = contentElement.querySelectorAll('pre code.language-mermaid');
                    if (mermaidBlocks.length > 0) {
                        mermaidBlocks.forEach((block, index) => {
                            const mermaidCode = block.textContent;
                            const mermaidId = `mermaid-diagram-${Date.now()}-${index}`;
                            const mermaidDiv = document.createElement('div');
                            mermaidDiv.className = 'mermaid';
                            mermaidDiv.id = mermaidId;
                            mermaidDiv.textContent = mermaidCode;
                            
                            // Replace the pre element with the mermaid div
                            const preElement = block.closest('pre');
                            if (preElement && preElement.parentNode) {
                                preElement.parentNode.replaceChild(mermaidDiv, preElement);
                            }
                        });
                        
                        // Initialize mermaid
                        window.mermaid.init(undefined, document.querySelectorAll('.mermaid'));
                    }
                } catch (e) {
                    console.warn("Error rendering mermaid diagrams:", e);
                }
            }
        } catch (e) {
            console.error("Error rendering markdown:", e);
        }
    }
    
    // Function to render all bot messages
    function renderAllBotMessages() {
        const botMessages = document.querySelectorAll('.bot-message');
        botMessages.forEach(renderMarkdown);
    }
    
    // Override the addBotMessageChunk function to properly handle streaming content
    if (typeof window.addBotMessageChunk === 'function') {
        const originalAddBotMessageChunk = window.addBotMessageChunk;
        
        window.addBotMessageChunk = function(text, botMessageDiv) {
            try {
                // Get current content
                const currentContent = botMessageDiv.dataset.rawContent || '';
                const newContent = currentContent + text;
                
                // Store raw content
                botMessageDiv.dataset.rawContent = newContent;
                
                // Get content div
                const contentDiv = botMessageDiv.querySelector('.message-content');
                if (!contentDiv) return;
                
                // Render markdown
                if (window.marked) {
                    contentDiv.innerHTML = marked.parse(newContent);
                    
                    // Apply syntax highlighting
                    if (window.hljs) {
                        const codeBlocks = contentDiv.querySelectorAll('pre code');
                        codeBlocks.forEach(block => {
                            try {
                                hljs.highlightElement(block);
                            } catch (e) {
                                // Ignore highlighting errors during streaming
                            }
                        });
                    }
                } else {
                    // Fallback to simple text append
                    contentDiv.innerHTML += text;
                }
                
                // Scroll to bottom
                const messageAnchor = document.getElementById('message-anchor');
                if (messageAnchor) {
                    messageAnchor.scrollIntoView({ behavior: 'smooth' });
                }
            } catch (e) {
                console.error("Error in improved addBotMessageChunk:", e);
                // Fall back to original function
                return originalAddBotMessageChunk.apply(this, arguments);
            }
        };
        
        console.log("Enhanced addBotMessageChunk function for better rendering");
    } else {
        console.warn("Original addBotMessageChunk function not found, cannot enhance");
    }
    
    // Apply CSS fixes for better rendering
    const style = document.createElement('style');
    style.textContent = `
        /* Improved rendering styles */
        #chatbox {
            max-height: calc(100vh - 300px);
            overflow-y: auto;
            overflow-x: hidden;
            padding: 20px;
        }
        
        .message {
            margin-bottom: 20px;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .message-content {
            word-break: break-word;
            overflow-wrap: break-word;
            padding: 10px;
        }
        
        .message-content pre {
            max-width: 100%;
            overflow-x: auto;
            padding: 12px;
            border-radius: 6px;
            margin: 10px 0;
            background-color: #f6f8fa;
            border: 1px solid #e1e4e8;
        }
        
        .dark-mode .message-content pre {
            background-color: #2d333b;
            border-color: #444c56;
        }
        
        .message-content code {
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            padding: 0.2em 0.4em;
            margin: 0;
            font-size: 85%;
            background-color: rgba(27, 31, 35, 0.05);
            border-radius: 3px;
        }
        
        .dark-mode .message-content code {
            background-color: rgba(240, 246, 252, 0.15);
        }
        
        .message-content pre code {
            padding: 0;
            margin: 0;
            font-size: 100%;
            background-color: transparent;
            border-radius: 0;
        }
        
        .message-content img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 10px 0;
        }
        
        .message-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            overflow-x: auto;
            display: block;
        }
        
        .message-content th, .message-content td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        .dark-mode .message-content th, .dark-mode .message-content td {
            border-color: #444;
        }
        
        .message-content blockquote {
            border-left: 4px solid #ddd;
            padding-left: 16px;
            margin-left: 0;
            color: #6a737d;
        }
        
        .dark-mode .message-content blockquote {
            border-color: #444;
            color: #8b949e;
        }
        
        .message-content ul, .message-content ol {
            padding-left: 2em;
        }
        
        .message-content h1, .message-content h2, .message-content h3, 
        .message-content h4, .message-content h5, .message-content h6 {
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }
        
        .message-content h1 {
            font-size: 2em;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
        }
        
        .message-content h2 {
            font-size: 1.5em;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
        }
        
        .dark-mode .message-content h1, .dark-mode .message-content h2 {
            border-color: #444;
        }
        
        /* Fix for copy button */
        .copy-button {
            position: absolute;
            top: 5px;
            right: 5px;
            background-color: rgba(0, 0, 0, 0.1);
            color: #333;
            border: none;
            border-radius: 3px;
            padding: 3px 8px;
            font-size: 12px;
            cursor: pointer;
            opacity: 0.6;
            transition: opacity 0.2s;
        }
        
        .dark-mode .copy-button {
            background-color: rgba(255, 255, 255, 0.1);
            color: #eee;
        }
        
        .copy-button:hover {
            opacity: 1;
        }
        
        /* Fix for mermaid diagrams */
        .mermaid {
            margin: 16px 0;
            overflow-x: auto;
        }
        
        /* Fix for inline code */
        .message-content p code {
            white-space: normal;
        }
    `;
    document.head.appendChild(style);
    
    // Render all existing bot messages
    renderAllBotMessages();
    
    // Set up observer to render new messages
    const chatbox = document.getElementById('chatbox');
    if (chatbox) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1 && node.classList && node.classList.contains('bot-message')) {
                            renderMarkdown(node);
                        }
                    });
                }
            });
        });
        
        observer.observe(chatbox, { childList: true, subtree: true });
    }
    
    console.log("Improved rendering fix applied");
});
