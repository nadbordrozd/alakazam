from flask import Flask, request, jsonify, render_template
import os
from bot import Bot

app = Flask(__name__)

# Global bot instance
bot = Bot()

def initialize_bot():
    """Initialize the bot with workflows"""
    bot.load_workflow("edibility_determination", "workflows/edibility_determination.yaml")
    bot.load_workflow("good_pet_determination", "workflows/good_pet_determination.yaml")
    
    # Add greeting message
    bot.get_greeting_message()

# Initialize on startup
initialize_bot()

@app.route('/')
def index():
    """Render the main chat interface"""
    return render_template('chat.html')

@app.route('/api/messages', methods=['GET'])
def get_messages():
    """Get all messages in the conversation"""
    messages = [msg.to_dict() for msg in bot.messages]
    
    # Get current options and sidebars
    current_options = list(bot.active_node.options.keys()) if bot.active_node else []
    active_sidebars = bot.get_active_sidebars()
    
    return jsonify({
        'messages': messages,
        'current_options': current_options,
        'active_sidebars': active_sidebars,
        'can_go_back': bot.can_go_back()
    })

@app.route('/api/send_message', methods=['POST'])
def send_message():
    """Process user input and return new messages"""
    data = request.get_json()
    user_text = data.get('text', '').strip()
    
    if not user_text:
        return jsonify({'error': 'No message provided'}), 400
    
    # Process user input with bot
    messages = list(bot.process_user_input(user_text))
    
    # Convert to dict format
    new_messages = [msg.to_dict() for msg in messages]
    
    # Get updated state
    current_options = list(bot.active_node.options.keys()) if bot.active_node else []
    active_sidebars = bot.get_active_sidebars()
    
    return jsonify({
        'new_messages': new_messages,
        'current_options': current_options,
        'active_sidebars': active_sidebars,
        'can_go_back': bot.can_go_back()
    })

@app.route('/api/go_back', methods=['POST'])
def go_back():
    """Go back one step in the conversation"""
    removed_message_ids = bot.go_back()
    
    # Get updated state
    current_options = list(bot.active_node.options.keys()) if bot.active_node else []
    active_sidebars = bot.get_active_sidebars()
    
    return jsonify({
        'removed_message_ids': removed_message_ids,
        'current_options': current_options,
        'active_sidebars': active_sidebars,
        'can_go_back': bot.can_go_back()
    })

@app.route('/api/sidebar/<filename>')
def get_sidebar_content(filename):
    """Get sidebar file content"""
    try:
        sidebar_path = os.path.join('sidebars', filename)
        if os.path.exists(sidebar_path):
            with open(sidebar_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({'content': content})
        else:
            return jsonify({'error': 'Sidebar file not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 