// Enhanced Features JavaScript
class EnhancedFeatures {
    constructor() {
        this.socket = io();
        this.sessionId = this.generateSessionId();
        this.userId = this.generateUserId();
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
        this.initCodeExecution();
        this.initCollaboration();
        this.initAnalytics();
        this.initSmartContext();
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

    // Code Execution
    initCodeExecution() {
        this.addMessageProcessor(this.processCodeBlocks.bind(this));
    }

    processCodeBlocks(messageElement) {
        const codeBlocks = messageElement.querySelectorAll('pre code');
        codeBlocks.forEach(block => {
            const executeBtn = document.createElement('button');
            executeBtn.innerHTML = '▶️ Run';
            executeBtn.className = 'btn btn-sm btn-success mt-2';
            executeBtn.onclick = () => this.executeCode(block.textContent);
            block.parentElement.appendChild(executeBtn);
        });
    }

    async executeCode(code) {
        const result = await fetch('/api/execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({code, language: 'python'})
        }).then(r => r.json());
        
        this.showExecutionResult(result);
    }

    showExecutionResult(result) {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'code-result alert alert-info mt-2';
        resultDiv.innerHTML = `
            <strong>Output:</strong><br>
            <pre>${result.stdout || result.error || 'No output'}</pre>
        `;
        document.getElementById('chatbox').appendChild(resultDiv);
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
        document.querySelector('.d-flex.justify-content-center').appendChild(analyticsBtn);
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

    addMessageProcessor(processor) {
        const originalAddMessage = window.addMessage;
        window.addMessage = function(...args) {
            const result = originalAddMessage.apply(this, args);
            processor(result);
            return result;
        };
    }

    addInputProcessor(processor) {
        const messageInput = document.getElementById('message-input');
        messageInput.addEventListener('input', (e) => processor(e.target.value));
    }
}

// Initialize enhanced features
const enhancedFeatures = new EnhancedFeatures();