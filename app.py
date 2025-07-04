from flask import Flask, request, jsonify, render_template
import yaml
import os
from typing import Dict, Any, List, Optional

app = Flask(__name__)

class WorkflowChatbot:
    def __init__(self, workflow_file: str):
        self.workflow_file = workflow_file
        self.workflow_data = self._load_workflow()
        self.current_node = self._get_start_node()
        
    def _load_workflow(self) -> Dict[str, Any]:
        """Load and parse the YAML workflow file"""
        with open(self.workflow_file, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    
    def _get_start_node(self) -> str:
        """Get the first node in the workflow"""
        return list(self.workflow_data.keys())[0]
    
    def get_current_node_data(self) -> Dict[str, Any]:
        """Get data for the current node"""
        return self.workflow_data.get(self.current_node, {})
    
    def get_sidebars_for_current_node(self) -> List[str]:
        """Get sidebar files referenced by current node"""
        node_data = self.get_current_node_data()
        return node_data.get('sidebars', [])
    
    def process_user_choice(self, choice: str) -> Dict[str, Any]:
        """Process user's choice and move to next node"""
        current_node_data = self.get_current_node_data()
        
        if 'options' in current_node_data:
            next_node = current_node_data['options'].get(choice)
            if next_node:
                self.current_node = next_node
                return {
                    'success': True,
                    'current_node': self.current_node,
                    'node_data': self.get_current_node_data(),
                    'sidebars': self.get_sidebars_for_current_node()
                }
        
        return {
            'success': False,
            'error': 'Invalid choice or no options available'
        }
    
    def reset_conversation(self):
        """Reset to the beginning of the workflow"""
        self.current_node = self._get_start_node()

# Global chatbot instance
chatbot = WorkflowChatbot('workflows/good_pet_determination.yaml')

@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')

@app.route('/api/start', methods=['GET'])
def start_conversation():
    """Start or restart the conversation"""
    chatbot.reset_conversation()
    return jsonify({
        'current_node': chatbot.current_node,
        'node_data': chatbot.get_current_node_data(),
        'sidebars': chatbot.get_sidebars_for_current_node()
    })

@app.route('/api/choice', methods=['POST'])
def make_choice():
    """Process user's choice and get next step"""
    data = request.get_json()
    choice = data.get('choice')
    
    if not choice:
        return jsonify({'error': 'No choice provided'}), 400
    
    result = chatbot.process_user_choice(choice)
    return jsonify(result)

@app.route('/api/current', methods=['GET'])
def get_current_state():
    """Get current conversation state"""
    return jsonify({
        'current_node': chatbot.current_node,
        'node_data': chatbot.get_current_node_data(),
        'sidebars': chatbot.get_sidebars_for_current_node()
    })

@app.route('/api/sidebar/<filename>')
def get_sidebar_content(filename):
    """Get content of a sidebar file"""
    sidebar_path = os.path.join('sidebars', filename)
    
    if not os.path.exists(sidebar_path):
        return jsonify({'error': 'Sidebar file not found'}), 404
    
    try:
        with open(sidebar_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return jsonify({
            'filename': filename,
            'content': content
        })
    except Exception as e:
        return jsonify({'error': f'Error reading file: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 