class ChatApp {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.goBackButton = document.getElementById('goBackButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.optionsContainer = document.getElementById('optionsContainer');
        this.sidebarContent = document.getElementById('sidebarContent');
        this.workflowIndicator = document.getElementById('workflowIndicator');
        this.workflowName = document.getElementById('workflowName');
        
        this.initializeEventListeners();
        this.loadMessages();
    }
    
    initializeEventListeners() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.goBackButton.addEventListener('click', () => this.goBack());
        
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
    }
    
    async loadMessages() {
        try {
            const response = await fetch('/api/messages');
            const data = await response.json();
            
            this.displayMessages(data.messages);
            this.updateOptions(data.current_options);
            this.loadSidebars(data.active_sidebars);
            this.updateGoBackButton(data.can_go_back);
            this.updateWorkflowIndicator(data.current_workflow);
        } catch (error) {
            this.showError('Failed to load messages');
        }
    }
    
    async sendMessage(text = null) {
        const messageText = text || this.messageInput.value.trim();
        if (!messageText) return;
        
        // Disable all buttons and inputs while bot is thinking
        this.setAllButtonsState(false);
        
        try {
            // Step 1: Send user message immediately
            const userResponse = await fetch('/api/send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: messageText })
            });
            
            const userData = await userResponse.json();
            
            if (userData.error) {
                this.showError(userData.error);
                this.setAllButtonsState(true);
                return;
            }
            
            // Display user message immediately
            this.displayMessages([userData.user_message], true);
            this.updateGoBackButton(userData.can_go_back);
            
            // Clear input
            this.messageInput.value = '';
            
            // Step 2: Process bot response (this may take time with LLM)
            const botResponse = await fetch('/api/process_bot_response', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const botData = await botResponse.json();
            
            if (botData.error) {
                this.showError(botData.error);
                this.setAllButtonsState(true);
                return;
            }
            
            // Display bot messages as they arrive
            if (botData.bot_messages && botData.bot_messages.length > 0) {
                this.displayMessages(botData.bot_messages, true);
            }
            
            this.updateOptions(botData.current_options);
            this.loadSidebars(botData.active_sidebars);
            this.updateGoBackButton(botData.can_go_back);
            this.updateWorkflowIndicator(botData.current_workflow);
            
        } catch (error) {
            this.showError('Failed to send message');
        } finally {
            // Re-enable all buttons and inputs
            this.setAllButtonsState(true);
        }
    }
    
    setSendButtonState(enabled) {
        this.sendButton.disabled = !enabled;
        if (enabled) {
            this.sendButton.textContent = 'Send';
            this.sendButton.style.opacity = '1';
        } else {
            this.sendButton.textContent = 'Sending...';
            this.sendButton.style.opacity = '0.6';
        }
    }
    
    setAllButtonsState(enabled) {
        // Disable/enable send button with visual feedback
        this.setSendButtonState(enabled);
        
        // Disable/enable message input
        this.messageInput.disabled = !enabled;
        
        // Disable/enable go back button
        this.goBackButton.disabled = !enabled;
        this.goBackButton.style.opacity = enabled ? '1' : '0.6';
        
        // Disable/enable all option buttons
        const optionButtons = this.optionsContainer.querySelectorAll('.option-button');
        optionButtons.forEach(button => {
            button.disabled = !enabled;
            button.style.opacity = enabled ? '1' : '0.6';
            button.style.cursor = enabled ? 'pointer' : 'not-allowed';
        });
    }
    
    async goBack() {
        // Disable all buttons while processing go back
        this.setAllButtonsState(false);
        
        try {
            const response = await fetch('/api/go_back', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            // Remove messages with the specified IDs
            data.removed_message_ids.forEach(id => {
                const messageElement = document.querySelector(`[data-message-id="${id}"]`);
                if (messageElement) {
                    messageElement.remove();
                }
            });
            
            this.updateOptions(data.current_options);
            this.loadSidebars(data.active_sidebars);
            this.updateGoBackButton(data.can_go_back);
            this.updateWorkflowIndicator(data.current_workflow);
            
        } catch (error) {
            this.showError('Failed to go back');
        } finally {
            // Re-enable all buttons and inputs
            this.setAllButtonsState(true);
        }
    }
    
    displayMessages(messages, append = false) {
        if (!append) {
            this.chatMessages.innerHTML = '';
        }
        
        messages.forEach(message => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${message.role}-message`;
            messageDiv.setAttribute('data-message-id', message.id);
            messageDiv.textContent = message.text;
            this.chatMessages.appendChild(messageDiv);
        });
        
        this.scrollToBottom();
    }
    
    updateOptions(options) {
        this.optionsContainer.innerHTML = '';
        
        options.forEach(option => {
            const button = document.createElement('button');
            button.className = 'option-button';
            button.textContent = option;
            button.addEventListener('click', () => this.sendMessage(option));
            this.optionsContainer.appendChild(button);
        });
    }
    
    updateGoBackButton(canGoBack) {
        this.goBackButton.disabled = !canGoBack;
    }
    
    async loadSidebars(sidebarFiles) {
        this.sidebarContent.innerHTML = '';
        
        if (sidebarFiles.length === 0) {
            this.sidebarContent.innerHTML = '<p>No additional information available.</p>';
            return;
        }
        
        for (const filename of sidebarFiles) {
            try {
                const response = await fetch(`/api/sidebar/${filename}`);
                const data = await response.json();
                
                if (data.content) {
                    const sidebarDiv = document.createElement('div');
                    sidebarDiv.className = 'sidebar-content';
                    
                    const title = document.createElement('div');
                    title.className = 'sidebar-title';
                    title.textContent = filename.replace('.md', '').replace('_', ' ');
                    
                    const content = document.createElement('div');
                    content.className = 'sidebar-text';
                    content.innerHTML = data.content.replace(/\n/g, '<br>');
                    
                    sidebarDiv.appendChild(title);
                    sidebarDiv.appendChild(content);
                    this.sidebarContent.appendChild(sidebarDiv);
                }
            } catch (error) {
                console.error(`Failed to load sidebar: ${filename}`, error);
            }
        }
    }
    
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        this.chatMessages.appendChild(errorDiv);
        this.scrollToBottom();
        
        // Remove error after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    updateWorkflowIndicator(workflowName) {
        if (workflowName && workflowName !== 'none') {
            // Format workflow name for display
            const displayName = workflowName
                .replace(/_/g, ' ')
                .replace(/\b\w/g, l => l.toUpperCase());
            
            this.workflowName.textContent = displayName;
            this.workflowIndicator.classList.remove('hidden');
        } else {
            this.workflowName.textContent = 'None Active';
            this.workflowIndicator.classList.add('hidden');
        }
    }
}

// Initialize the app when page loads
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
}); 