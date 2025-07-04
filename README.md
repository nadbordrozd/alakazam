# Pokemon Pet Advisor Chatbot

A simple chatbot that follows a workflow defined in a YAML file to help determine if a Pokemon would make a good pet.

## Features

- **Interactive Chat Interface**: Chat window on the left with guided questions and responses
- **Dynamic Sidebar**: Right sidebar displays relevant reference information based on current conversation node
- **YAML-Driven Workflow**: Easily customizable decision tree defined in `workflows/good_pet_determination.yaml`
- **Contextual Information**: Sidebar automatically loads relevant articles from the `sidebars/` directory

## How It Works

The chatbot uses a decision tree workflow defined in the YAML file where:
- Each node has a question and multiple choice options
- Nodes can reference sidebar articles that provide additional context
- The conversation ends with a verdict about the Pokemon's suitability as a pet

## Installation & Usage

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Open your browser and go to:**
   ```
   http://localhost:5000
   ```

## Project Structure

```
ibis/
├── app.py                          # Flask backend application
├── requirements.txt                # Python dependencies
├── templates/
│   └── index.html                 # Web interface template
├── workflows/
│   └── good_pet_determination.yaml # Chatbot decision tree
└── sidebars/                      # Reference articles
    ├── legendary_pokemon.md
    ├── pokemon_accidents.md
    ├── pokemon_intelligence.md
    ├── size_categories.md
    ├── unusual_abilities.md
    └── ...
```

## API Endpoints

- `GET /` - Main chat interface
- `GET /api/start` - Start/restart conversation
- `POST /api/choice` - Process user choice
- `GET /api/current` - Get current conversation state  
- `GET /api/sidebar/<filename>` - Get sidebar content

## Customization

You can customize the chatbot by:
1. **Modifying the workflow**: Edit `workflows/good_pet_determination.yaml`
2. **Adding sidebar content**: Add new `.md` files to the `sidebars/` directory
3. **Styling**: Update the CSS in `templates/index.html`

## YAML Workflow Format

Each node in the workflow can have:
- `question`: The question to ask the user
- `options`: Dictionary of choices leading to other nodes
- `verdict`: Final answer/result
- `sidebars`: List of sidebar files to display

Example:
```yaml
node_name:
    question: "What size is the Pokemon?"
    options:
        small: small_pokemon_check
        large: large_pokemon_check
    sidebars:
        - size_categories.md
``` 