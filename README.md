# 🤖 Twitter Bot Assistant

> A smart Twitter bot built with FastAPI that automatically responds to mentions using AI. Simple, fast, and respects API limits.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.97.0-009688.svg)](https://fastapi.tiangolo.com)
[![Twitter API](https://img.shields.io/badge/Twitter_API-v2-1DA1F2.svg)](https://developer.twitter.com/en/docs/twitter-api)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## ✨ Features

- 🔄 **Auto-Reply**: Responds to mentions automatically
- 🧠 **AI Integration**: Optional LLM-powered responses
- 📊 **Usage Tracking**: Monitors Twitter API limits
- 🚀 **Fast & Async**: Built with FastAPI
- 🔑 **Simple Auth**: Easy Twitter API setup

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Twitter Developer Account
- Twitter API v2 Credentials

### Setup in 3 Steps

1. **Clone & Install**
   ```bash
   git clone <your-repo-url>
   cd twitter-bot-assistant
   pip install -r requirements.txt
   ```

2. **Configure**
   ```bash
   # Create .env file with your Twitter credentials
   cp .env.example .env
   # Edit .env with your details
   ```

3. **Run**
   ```bash
   python main.py
   ```

Visit `http://localhost:8000/docs` for the interactive API documentation.

## 🎮 Basic Usage

### Enable the Bot
```bash
curl -X POST "http://localhost:8000/bot/enable"
```

### Configure Auto-Replies
```bash
curl -X POST "http://localhost:8000/bot/configure" \
  -H "Content-Type: application/json" \
  -d '{
    "check_interval_seconds": 120,
    "response_prefix": "🤖",
    "use_llm": false
  }'
```

### Post a Tweet
```bash
curl -X POST "http://localhost:8000/tweet" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from my Twitter Bot! 🚀"}'
```

## 🧠 AI Integration

Enable AI-powered responses by:

1. Add your OpenAI key to `.env`:
   ```
   OPENAI_API_KEY=your_key_here
   ```

2. Enable LLM responses:
   ```bash
   curl -X POST "http://localhost:8000/bot/configure-llm" \
     -d '{"use_llm": true}'
   ```

## 📈 API Limits

Free tier limits are automatically tracked:
- 500 posts/month (app)
- 500 posts/month (user)
- 100 reads/month

## 🤝 Contributing

Feel free to:
- Open issues
- Submit PRs
- Suggest features
- Share your experience

## 📝 License

MIT © Mahimai Raja

---

<div align="center">
Made with ❤️ by <a href="https://github.com/mahimairaja">Mahimai Raja</a>
</div>
