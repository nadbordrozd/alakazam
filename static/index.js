class PokemonChatbot {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sidebarContent = document.getElementById('sidebarContent');
        this.currentNode = null;
        this.initializeChat();
    }

    async initializeChat() {
        try {
            const response = await fetch('/api/start');
            const data = await response.json();
            this.handleBotResponse(data);
        } catch (error) {
            this.showError('Failed to start conversation');
        }
    }

    async makeChoice(choice) {
        this.addUserMessage(choice);
        
        // Disable all buttons while processing
        this.setAllButtonsState(false);

        try {
            const response = await fetch('/api/choice', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ choice: choice })
            });
            
            const data = await response.json();
            this.handleBotResponse(data);
        } catch (error) {
            this.showError('Failed to process choice');
        } finally {
            // Re-enable all buttons
            this.setAllButtonsState(true);
        }
    }

    handleBotResponse(data) {
        if (data.error) {
            this.showError(data.error);
            return;
        }

        const nodeData = data.node_data;
        
        if (nodeData.question) {
            this.addBotMessage(nodeData.question);
            this.showOptions(nodeData.options);
        } else if (nodeData.verdict) {
            this.addVerdictMessage(nodeData.verdict);
            this.showRestartButton();
        }

        this.loadSidebarContent(data.sidebars || []);
    }

    addBotMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.textContent = message;
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addUserMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message';
        messageDiv.textContent = message;
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addVerdictMessage(verdict) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message verdict-message';
        
        // Determine verdict type based on emoji
        if (verdict.includes('🟢')) {
            messageDiv.classList.add('excellent');
        } else if (verdict.includes('🟡')) {
            messageDiv.classList.add('caution');
        } else if (verdict.includes('🟠')) {
            messageDiv.classList.add('caution');
        } else if (verdict.includes('🔴')) {
            messageDiv.classList.add('danger');
        }
        
        messageDiv.textContent = verdict;
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showOptions(options) {
        this.chatInput.innerHTML = '';
        
        if (options) {
            const optionsContainer = document.createElement('div');
            optionsContainer.className = 'options-container';
            
            Object.keys(options).forEach(option => {
                const button = document.createElement('button');
                button.className = 'option-button';
                button.textContent = option.replace(/_/g, ' ').toUpperCase();
                button.onclick = () => this.makeChoice(option);
                optionsContainer.appendChild(button);
            });
            
            this.chatInput.appendChild(optionsContainer);
        }
    }

    showRestartButton() {
        this.chatInput.innerHTML = '';
        const button = document.createElement('button');
        button.className = 'restart-button';
        button.textContent = 'Start New Assessment';
        button.onclick = () => this.restart();
        this.chatInput.appendChild(button);
    }

    async restart() {
        // Disable all buttons while restarting
        this.setAllButtonsState(false);
        
        this.chatMessages.innerHTML = '';
        this.sidebarContent.innerHTML = '<p class="loading">Loading...</p>';
        
        try {
            await this.initializeChat();
        } finally {
            // Re-enable all buttons
            this.setAllButtonsState(true);
        }
    }

    async loadSidebarContent(sidebarFiles) {
        this.sidebarContent.innerHTML = '';
        
        if (sidebarFiles.length === 0) {
            this.sidebarContent.innerHTML = '<p class="loading">No additional information available for this step.</p>';
            return;
        }

        for (const filename of sidebarFiles) {
            try {
                const response = await fetch(`/api/sidebar/${filename}`);
                const data = await response.json();
                
                if (data.error) {
                    console.error(`Failed to load ${filename}:`, data.error);
                    continue;
                }

                const articleDiv = document.createElement('div');
                articleDiv.className = 'sidebar-article';
                
                const title = document.createElement('h3');
                title.textContent = filename.replace('.md', '').replace(/_/g, ' ').toUpperCase();
                
                const content = document.createElement('p');
                content.textContent = data.content;
                
                articleDiv.appendChild(title);
                articleDiv.appendChild(content);
                this.sidebarContent.appendChild(articleDiv);
                
            } catch (error) {
                console.error(`Failed to load sidebar content for ${filename}:`, error);
            }
        }
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error';
        errorDiv.textContent = `Error: ${message}`;
        this.chatMessages.appendChild(errorDiv);
        this.scrollToBottom();
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    setAllButtonsState(enabled) {
        // Disable/enable all option buttons
        const optionButtons = this.chatInput.querySelectorAll('.option-button');
        optionButtons.forEach(button => {
            button.disabled = !enabled;
            button.style.opacity = enabled ? '1' : '0.6';
            button.style.cursor = enabled ? 'pointer' : 'not-allowed';
        });
        
        // Disable/enable restart button if it exists
        const restartButton = this.chatInput.querySelector('.restart-button');
        if (restartButton) {
            restartButton.disabled = !enabled;
            restartButton.style.opacity = enabled ? '1' : '0.6';
            restartButton.style.cursor = enabled ? 'pointer' : 'not-allowed';
        }
    }
}

// Initialize the chatbot when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new PokemonChatbot();
}); 