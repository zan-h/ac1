# 🎙️ Voice Assistant with OpenAI Realtime API

A sophisticated voice-enabled AI assistant built with Chainlit and OpenAI's Realtime API, featuring natural voice conversations and powerful integrated tools.

## ✨ Features

- **🎤 Real-time Voice Communication**: Natural speech-to-speech conversations
- **🌐 Web Search**: Get current information from the internet
- **📈 Stock Market Data**: Real-time financial data and charts
- **🎨 Image Generation**: Create images from text descriptions
- **🌤️ Weather Information**: Current weather and forecasts
- **📝 Task Management**: Create and manage to-do items
- **💭 Sentiment Analysis**: Analyze emotional tone of text
- **🗄️ Database Queries**: Execute custom database searches
- **⏰ Time & Date**: Get current time for any timezone

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key (for Realtime API access)
- Additional API keys for enhanced features (optional)

### Installation

1. **Clone and navigate to the project**:
```bash
cd /Users/mizan/100MRR/ac1
```

2. **Activate the virtual environment**:
```bash
source venv/bin/activate
```

3. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required API keys:
- `OPENAI_API_KEY`: Your OpenAI API key (required for voice functionality)

Optional API keys for enhanced features:
- `GROQ_API_KEY`: For AI model inference
- `TAVILY_API_KEY`: For web search functionality
- `TOGETHER_API_KEY`: For image generation

4. **Run the application**:
```bash
chainlit run my_assistant.py
```

5. **Open your browser** to the URL shown (typically http://localhost:8000)

## 🎯 How to Use

### Voice Mode
1. Click the microphone button or press `P` to activate voice mode
2. Speak naturally - the assistant will respond with voice
3. You can interrupt the assistant at any time by speaking

### Text Mode
- Type your questions in the chat interface
- All the same features are available via text

### Example Commands

**Voice/Text Commands:**
- "What's the weather like in New York?"
- "Show me Apple's stock price"
- "Generate an image of a mountain sunset"
- "What time is it in Tokyo?"
- "Search for latest AI news"
- "Create a task to call the doctor"
- "Analyze the sentiment of this text: I'm feeling great today!"

## 🛠️ Configuration

### OpenAI Realtime API Setup

The application uses OpenAI's Realtime API for voice conversations. Make sure you have:

1. An OpenAI API key with access to the Realtime API
2. Sufficient credits in your OpenAI account
3. The API key set in your `.env` file

### Azure OpenAI (Alternative)

To use Azure OpenAI instead:

```env
USE_AZURE=true
AZURE_OPENAI_ENDPOINT=your-endpoint.openai.azure.com
AZURE_OPENAI_API_KEY=your-azure-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o-realtime-preview
```

### Database Configuration

The application uses SQLite by default. For PostgreSQL:

```env
DB_DIALECT=postgresql
DB_USERNAME=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_DATABASE=your_database
```

## 📁 Project Structure

```
/Users/mizan/100MRR/ac1/
├── my_assistant.py          # Main application file
├── chainlit.md             # Welcome page content
├── tools.py                # Tool definitions and handlers
├── config/                 # Configuration files
│   ├── realtime_config.py  # Realtime API configuration
│   ├── database.py         # Database configuration
│   └── realtime_instructions.txt # AI instructions
├── realtime/               # Realtime API implementation
│   └── __init__.py         # RealtimeClient implementation
├── utils/                  # Utility functions
│   ├── ai_models.py        # AI model configuration
│   ├── common.py           # Common utilities
│   └── realtime_helpers.py # Realtime-specific helpers
└── .env.example            # Environment variables template
```

## 🔧 Troubleshooting

### Common Issues

1. **"Voice mode unavailable"**
   - Check your OpenAI API key
   - Ensure you have Realtime API access
   - Verify your internet connection

2. **"Module not found" errors**
   - Make sure you're in the virtual environment
   - Install missing dependencies: `pip install -r app/frontend/requirements.txt`

3. **Audio issues**
   - Check browser microphone permissions
   - Ensure you're using a supported browser (Chrome, Firefox, Safari)
   - Test with headphones to avoid audio feedback

4. **Tool functionality limited**
   - Set up additional API keys in `.env` for full functionality
   - Check API key permissions and credits

### Performance Tips

- Use a stable internet connection for best voice quality
- Speak clearly in a quiet environment
- Keep conversations focused for better responses

## 🛡️ Security

- Keep your API keys secure and never commit them to version control
- The `.env` file is gitignored for security
- All API communications use HTTPS/WSS encryption

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the application logs in the terminal
3. Ensure all API keys are correctly configured

## 🎉 Ready to Go!

Your voice assistant is now ready to use! Start by running:

```bash
source venv/bin/activate
chainlit run my_assistant.py
```

Then open your browser and start talking! 🎙️