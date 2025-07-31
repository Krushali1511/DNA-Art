# AI Voice Assistant

A web application where users can call and talk to an AI customer service agent to get questions answered about their account.

## Features

- 🎤 **Real-time Voice Calls**: WebRTC-powered voice communication
- 🤖 **AI Customer Service**: Powered by Groq for fast AI responses
- 🎯 **RAG Integration**: Uses company guidelines and user information for accurate responses
- 📊 **Admin Dashboard**: Analytics of user calls and common questions
- 🔊 **Natural Voice**: ElevenLabs text-to-speech for human-like responses
- 👂 **Speech Recognition**: DeepGram for accurate speech-to-text conversion

## Tech Stack

### Frontend
- **React** with **TypeScript**
- **WebRTC** for real-time voice communication
- **Socket.IO** for real-time updates
- **Chart.js** for analytics visualization

### Backend
- **FastAPI** (Python) for high-performance async API
- **WebSocket** support for real-time communication
- **SQLite/PostgreSQL** for data storage
- **Vector Database** for RAG implementation

### AI Services
- **DeepGram**: Speech-to-text conversion
- **ElevenLabs**: Text-to-speech synthesis
- **Groq**: Fast AI inference for responses

## Project Structure

```
voice-assistant/
├── frontend/          # React TypeScript frontend
├── backend/           # FastAPI Python backend
├── shared/            # Shared types and utilities
└── README.md
```

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.9+
- API keys for DeepGram, ElevenLabs, and Groq

### Installation

1. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm start
   ```

### Environment Variables

Create `.env` files in both frontend and backend directories:

**Backend (.env)**
```
DEEPGRAM_API_KEY=your_deepgram_key
ELEVENLABS_API_KEY=your_elevenlabs_key
GROQ_API_KEY=your_groq_key
DATABASE_URL=sqlite:///./voice_assistant.db
```

**Frontend (.env)**
```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
```

## Development

- Backend runs on `http://localhost:8000`
- Frontend runs on `http://localhost:3000`
- Admin dashboard available at `http://localhost:3000/admin`

## API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for interactive API documentation.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.
