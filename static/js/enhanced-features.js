// Enhanced Features JavaScript
class EnhancedFeatures {
    constructor() {
        this.socket = io();
        this.sessionId = this.generateSessionId();
        this.userId = this.generateUserId();
        this.commands = [];
        this.initializeFeatures();
    }

    generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9);
    }

    generateUserId() {
        return localStorage.getItem('userId') ||
               (() => {
                   const id = 'user_' + Math.random().toString(36).substr(2, 9);
                   localStorage.setItem('userId', id);
                   return id;
               })();
    }

    initializeFeatures() {
        this.initTemplates();
        this.initVoice();
        this.initMagicCodeActions(); // Replaces initCodeExecution
        this.initCollaboration();
        this.initAnalytics();
        this.initSmartContext();
        this.initCommandPalette(); // Add new feature
    }

    // Command Palette
    initCommandPalette() {
        this.palette = {
            modal: document.getElementById('command-palette-modal'),
            content: document.getElementById('command-palette-content'),
            input: document.getElementById('command-palette-input'),
            list: document.getElementById('command-palette-list'),
        };
        this.selectedCommandIndex = -1;

        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.toggleCommandPalette();
            }
        });

        this.palette.input.addEventListener('input', () => this.filterCommands());
        this.palette.input.addEventListener('keydown', (e) => this.handlePaletteNavigation(e));
        this.palette.modal.addEventListener('click', (e) => {
            if (e.target === this.palette.modal) {
                this.toggleCommandPalette(false);
            }
        });
    }

    async toggleCommandPalette(forceShow = null) {
        const shouldShow = forceShow !== null ? forceShow : this.palette.modal.style.display === 'none';
        if (shouldShow) {
            this.palette.modal.style.display = 'block';
            this.palette.input.focus();
            if (this.commands.length === 0) {
                this.commands = await fetch('/api/commands').then(res => res.json());
            }
            this.filterCommands();
        } else {
            this.palette.modal.style.display = 'none';
        }
    }

    filterCommands() {
        const query = this.palette.input.value.toLowerCase();
        const filteredCommands = this.commands.filter(cmd =>
            cmd.name.toLowerCase().includes(query) || cmd.description.toLowerCase().includes(query)
        );
        this.renderCommands(filteredCommands);
    }

    renderCommands(commands) {
        this.palette.list.innerHTML = '';
        commands.forEach((cmd, index) => {
            const li = document.createElement('li');
            li.className = 'command-item';
            li.dataset.commandId = cmd.id;
            li.innerHTML = `
                <div class="command-item-name">${cmd.name}</div>
                <div class="command-item-desc">${cmd.description}</div>
            `;
            li.addEventListener('click', () => this.executeCommand(cmd.id));
            this.palette.list.appendChild(li);
        });
        this.selectedCommandIndex = -1; // Reset selection
    }

    handlePaletteNavigation(e) {
        const items = this.palette.list.querySelectorAll('.command-item');
        if (items.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.selectedCommandIndex = (this.selectedCommandIndex + 1) % items.length;
            this.updateCommandSelection(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.selectedCommandIndex = (this.selectedCommandIndex - 1 + items.length) % items.length;
            this.updateCommandSelection(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (this.selectedCommandIndex > -1) {
                items[this.selectedCommandIndex].click();
            }
        } else if (e.key === 'Escape') {
            this.toggleCommandPalette(false);
        }
    }

    updateCommandSelection(items) {
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === this.selectedCommandIndex);
        });
    }

    executeCommand(commandId) {
        console.log(`Executing command: ${commandId}`);
        switch (commandId) {
            case 'upload_file':
                // This assumes a file input with id 'file-upload' exists
                document.getElementById('image-upload').click();
                break;
            case 'export_chat':
                // Assuming an export function exists
                alert('Exporting chat... (functionality to be implemented)');
                break;
            case 'clear_chat':
                document.getElementById('chatbox').innerHTML = '<div id="message-anchor"></div>';
                break;
            case 'search_history':
                document.getElementById('search-input').focus();
                break;
            case 'run_code':
                const code = prompt("Enter Python code to execute:");
                if (code) this.executeCode(code);
                break;
        }
        this.toggleCommandPalette(false); // Close palette after execution
    }


    // Template System
    initTemplates() {
        const templateBtn = document.createElement('button');
        templateBtn.innerHTML = '📋';
        templateBtn.className = 'btn btn-outline-secondary btn-sm';
        templateBtn.title = 'Templates';
        templateBtn.onclick = () => this.showTemplateModal();
        document.getElementById('input-area').appendChild(templateBtn);
    }

    async showTemplateModal() {
        const templates = await fetch('/api/templates').then(r => r.json());
        const modal = this.createModal('Templates', this.renderTemplates(templates));
        document.body.appendChild(modal);
    }

    renderTemplates(templates) {
        return `<style>
            .template-item {
                padding: 12px;
                margin: 8px 0;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            .template-item:hover {
                background: #f8f9fa;
                border-color: #007bff;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,123,255,0.15);
            }
        </style>` +
        Object.entries(templates).map(([id, template]) =>
            `<div class="template-item" onclick="enhancedFeatures.applyTemplate('${id}')">
                <h6>${template.name}</h6>
                <small class="text-muted">${template.category}</small>
            </div>`
        ).join('');
    }

    async applyTemplate(templateId) {
        const templates = await fetch('/api/templates').then(r => r.json());
        const template = templates[templateId];

        // Create default values for all variables
        const variables = {};
        if (template.variables) {
            template.variables.forEach(variable => {
                variables[variable] = `[${variable}]`; // Placeholder values
            });
        }

        const result = await fetch(`/api/templates/${templateId}/apply`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(variables)
        }).then(r => r.json());

        document.getElementById('message-input').value = result.result;
        this.closeModal();
    }

    // Voice Interface
    initVoice() {
        const voiceBtn = document.createElement('button');
        voiceBtn.innerHTML = '🎤';
        voiceBtn.className = 'btn btn-outline-primary btn-sm';
        voiceBtn.title = 'Voice Input';
        voiceBtn.onclick = () => this.startVoiceRecording();
        document.getElementById('input-area').appendChild(voiceBtn);
    }

    async startVoiceRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            const chunks = [];

            mediaRecorder.ondataavailable = e => chunks.push(e.data);
            mediaRecorder.onstop = async () => {
                const blob = new Blob(chunks, { type: 'audio/wav' });
                const formData = new FormData();
                formData.append('audio', blob);

                const result = await fetch('/api/voice/speech-to-text', {
                    method: 'POST',
                    body: formData
                }).then(r => r.json());

                if (result.success) {
                    document.getElementById('message-input').value = result.text;
                }
            };

            mediaRecorder.start();
            setTimeout(() => mediaRecorder.stop(), 5000); // 5 second recording
        } catch (error) {
            console.error('Voice recording error:', error);
        }
    }

    // Magic Code Actions (replaces Code Execution)
    initMagicCodeActions() {
        const chatbox = document.getElementById('chatbox');
        const observer = new MutationObserver((mutations) => {
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1 && node.matches('.bot-message')) {
                        const codeBlocks = node.querySelectorAll('pre');
                        codeBlocks.forEach(pre => this.addCodeActionButtons(pre));
                    }
                });
            });
        });

        observer.observe(chatbox, { childList: true, subtree: true });
    }

    addCodeActionButtons(preElement) {
        if (preElement.querySelector('.code-actions')) return; // Already has buttons

        const codeText = preElement.querySelector('code').innerText;

        const actionsContainer = document.createElement('div');
        actionsContainer.className = 'code-actions d-flex justify-content-end gap-2 p-2';
        actionsContainer.style.position = 'absolute';
        actionsContainer.style.top = '5px';
        actionsContainer.style.right = '5px';

        // Copy Button
        const copyBtn = document.createElement('button');
        copyBtn.innerText = 'Copy';
        copyBtn.className = 'btn btn-sm btn-secondary';
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(codeText).then(() => {
                copyBtn.innerText = 'Copied!';
                setTimeout(() => copyBtn.innerText = 'Copy', 2000);
            });
        };

        // Save Button
        const saveBtn = document.createElement('button');
        saveBtn.innerText = 'Save';
        saveBtn.className = 'btn btn-sm btn-secondary';
        saveBtn.onclick = () => this.saveCodeToFile(codeText);


        // Run Button
        const runBtn = document.createElement('button');
        runBtn.innerText = 'Run';
        runBtn.className = 'btn btn-sm btn-primary';
        runBtn.onclick = () => this.executeCode(codeText, preElement);

        actionsContainer.append(copyBtn, saveBtn, runBtn);
        preElement.style.position = 'relative'; // Needed for absolute positioning of children
        preElement.appendChild(actionsContainer);
    }

    async saveCodeToFile(code) {
        const fileName = prompt("Enter filename (e.g., script.py):", "script.py");
        if (!fileName) return;

        const response = await fetch('/api/save_code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: fileName, content: code })
        });

        const result = await response.json();
        if (result.success) {
            alert(`File saved successfully at ${result.path}`);
        } else {
            alert(`Error: ${result.error}`);
        }
    }

    async executeCode(code, preElement) {
        // Remove previous results if any
        const oldResult = preElement.parentElement.querySelector('.code-result');
        if (oldResult) oldResult.remove();

        const result = await fetch('/api/execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({code, language: 'python'})
        }).then(r => r.json());

        this.showExecutionResult(result, preElement);
    }

    showExecutionResult(result, preElement) {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'code-result alert alert-info mt-2';
        const output = result.stdout || result.stderr || 'No output';
        resultDiv.innerHTML = `<strong>Output:</strong><pre class="mb-0">${output}</pre>`;
        preElement.insertAdjacentElement('afterend', resultDiv);
    }


    // Collaboration
    initCollaboration() {
        this.socket.emit('join_session', {
            session_id: this.sessionId,
            user_id: this.userId
        });

        this.socket.on('user_joined', data => this.updateUserList(data.users));
        this.socket.on('new_message', data => this.handleCollaborativeMessage(data));
        this.socket.on('context_changed', data => this.handleContextChange(data));
    }

    updateUserList(users) {
        const userList = document.getElementById('user-list') || this.createUserList();
        userList.innerHTML = Object.values(users).map(user =>
            `<span class="badge bg-primary me-1">${user.username}</span>`
        ).join('');
    }

    createUserList() {
        const userList = document.createElement('div');
        userList.id = 'user-list';
        userList.className = 'mb-2';
        document.getElementById('chatbox').parentElement.insertBefore(userList, document.getElementById('chatbox'));
        return userList;
    }

    // Analytics
    initAnalytics() {
        const analyticsBtn = document.createElement('button');
        analyticsBtn.innerHTML = '📊';
        analyticsBtn.className = 'btn btn-outline-info btn-sm';
        analyticsBtn.title = 'Analytics';
        analyticsBtn.onclick = () => this.showAnalytics();

        // Find the button group container and insert the analytics button after the send button
        const buttonGroup = document.querySelector('#input-area .d-flex.gap-1');
        const sendButton = document.getElementById('send-button');

        if (buttonGroup && sendButton) {
            // Insert analytics button after the send button
            const nextSibling = sendButton.nextElementSibling;
            if (nextSibling) {
                buttonGroup.insertBefore(analyticsBtn, nextSibling);
            } else {
                buttonGroup.appendChild(analyticsBtn);
            }
        } else {
            // Fallback: append to input area if button group not found
            const inputArea = document.getElementById('input-area');
            if (inputArea) {
                inputArea.appendChild(analyticsBtn);
            }
        }
    }

    async showAnalytics() {
        const [usage, insights, productivity] = await Promise.all([
            fetch('/api/analytics/usage').then(r => r.json()),
            fetch('/api/analytics/insights').then(r => r.json()),
            fetch('/api/analytics/productivity').then(r => r.json())
        ]);

        const content = `
            <div class="row">
                <div class="col-md-4">
                    <h6>Usage Stats</h6>
                    <p>Messages: ${usage.daily_messages.reduce((a,b) => a + b.count, 0)}</p>
                    <p>Context Usage: ${usage.context_usage}%</p>
                </div>
                <div class="col-md-4">
                    <h6>Top Topics</h6>
                    ${insights.top_topics.slice(0,5).map(t => `<p>${t.topic}: ${t.count}</p>`).join('')}
                </div>
                <div class="col-md-4">
                    <h6>Productivity</h6>
                    <p>Peak Hour: ${productivity.peak_hour}:00</p>
                    <p>Avg Message Length: ${insights.avg_user_message_length}</p>
                </div>
            </div>
        `;

        const modal = this.createModal('Analytics Dashboard', content);
        document.body.appendChild(modal);
    }

    // Smart Context
    initSmartContext() {
        this.addInputProcessor(this.suggestSmartContext.bind(this));
    }

    async suggestSmartContext(inputText) {
        if (inputText.length > 50) { // Only for longer messages
            const suggestions = await fetch('/api/context/suggest', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({conversation: inputText})
            }).then(r => r.json());

            if (suggestions.length > 0) {
                this.showContextSuggestions(suggestions);
            }
        }
    }

    showContextSuggestions(suggestions) {
        const suggestionDiv = document.createElement('div');
        suggestionDiv.className = 'alert alert-info mt-2';
        suggestionDiv.innerHTML = `
            <strong>Suggested Context:</strong><br>
            ${suggestions.slice(0,3).map(s =>
                `<button class="btn btn-sm btn-outline-primary me-1"
                 onclick="enhancedFeatures.addSuggestedContext('${s.path}')">${s.path}</button>`
            ).join('')}
        `;
        document.getElementById('active-context-area').appendChild(suggestionDiv);
    }

    addSuggestedContext(path) {
        if (!activeContextItems.includes(path)) {
            activeContextItems.push(path);
            updateContextUI();
        }
    }

    // Utility Methods
    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${title}</h5>
                        <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                    </div>
                    <div class="modal-body">${content}</div>
                </div>
            </div>
        `;
        return modal;
    }

    closeModal() {
        document.querySelector('.modal')?.remove();
    }

    addInputProcessor(processor) {
        const messageInput = document.getElementById('message-input');
        messageInput.addEventListener('input', (e) => processor(e.target.value));
    }
}

// Initialize enhanced features
const enhancedFeatures = new EnhancedFeatures();
