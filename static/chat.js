class ChatApp {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.goBackButton = document.getElementById('goBackButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.optionsContainer = document.getElementById('optionsContainer');
        this.sidebarContent = document.getElementById('sidebarContent');
        
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
        } catch (error) {
            this.showError('Failed to load messages');
        }
    }
    
    async sendMessage(text = null) {
        const messageText = text || this.messageInput.value.trim();
        if (!messageText) return;
        
        try {
            const response = await fetch('/api/send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: messageText })
            });
            
            const data = await response.json();
            
            if (data.error) {
                this.showError(data.error);
                return;
            }
            
            // Add new messages
            this.displayMessages(data.new_messages, true);
            this.updateOptions(data.current_options);
            this.loadSidebars(data.active_sidebars);
            this.updateGoBackButton(data.can_go_back);
            
            // Clear input
            this.messageInput.value = '';
            
        } catch (error) {
            this.showError('Failed to send message');
        }
    }
    
    async goBack() {
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
            
        } catch (error) {
            this.showError('Failed to go back');
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
}

// Initialize the app when page loads
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
}); 