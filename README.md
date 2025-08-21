# QuizStream 🎥🧠

QuizStream is an AI-powered RAG (Retrieval-Augmented Generation) learning platform that transforms educational videos into intelligent quizzes and interactive chat-based study sessions. It leverages Gemini 2.5 Flash, Deepgram, LangChain, and ChromaDB to generate transcripts, create MCQs/True-False questions, and enable retrieval-based chatbot interactions.

## 🚀 Features

### Role-Based Access Control

Teachers: Upload videos or provide YouTube links, approve transcripts, and auto-generate quizzes.

Students: Access video-specific MCQs (without answers) and interact with a transcript-powered chatbot.

### RAG-Powered System

Transcript chunks created using LangChain text splitters.

Embeddings stored in ChromaDB as a vector store.

Queries resolved using a Maximum Marginal Relevance (MMR) retriever for better contextual answers.

Gemini 2.5 Flash generates chatbot responses grounded in retrieved transcript context.

### Video & Transcript Processing

Extracts audio from uploaded videos or YouTube links.

Generates high-quality transcripts using Deepgram.

Stores transcript embeddings for efficient retrieval.

### Quiz Generation

Once a transcript is approved, Gemini 2.5 Flash generates MCQs and True/False questions.

Questions are stored in PostgreSQL for persistent access.

### Chatbot

Retrieval-Augmented chatbot powered by Gemini 2.5 Flash + LangChain retrievers.

Answers student queries based on the transcript of the selected video.

### Authentication & Authorization

Secure JWT-based authentication.

Role-based access (Teacher/Student) to endpoints and features.

## 🛠️ Tech Stack

Backend: FastAPI

AI & NLP:

Gemini 2.5 Flash
 for quiz generation and chatbot

Deepgram
 for transcription

LangChain
 for text splitting & RAG pipeline

ChromaDB
 as vector store with retrievers

Database: PostgreSQL

Authentication: JWT Tokens

Containerization: Docker

## 📂 Project Workflow

Teacher uploads video / YouTube link

System extracts audio → generates transcript (Deepgram)

Transcript chunked via LangChain text splitters → embeddings stored in ChromaDB

Teacher approves transcript

Gemini 2.5 Flash generates MCQs/True-False → stored in PostgreSQL

Students:

View MCQs (without answers)

Chat with the QuizBot using video title (responses powered by RAG-based retrieval from transcript embeddings)

## 🔑 Endpoints Overview

### Auth

POST `/auth/signup` – Register user (Teacher/Student)

POST `/auth/login` – Login & get JWT token

### Teacher Endpoints

POST `/videos/upload` – Upload a video file or YouTube link

GET `/videos/list` – View all uploaded videos

POST `/videos/{id}/approve` – Approve transcript & trigger quiz generation

### Student Endpoints

GET `/quiz/{video_title}` – Fetch MCQs/TF questions (no answers)

POST `/chat/{video_title}` – Chat with the AI chatbot about the video (RAG-based)

## ⚡ Installation

Clone the repo:

```
git clone https://gitlab.com/divedeepai/nihal-videolessonschat.git


cd QuizStream
```


Create a virtual environment & install dependencies:

```
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Set up environment variables in .env:


Start the FastAPI server:

`uvicorn app.main:app --reload`

FastAPI available at: http://127.0.0.1:8000/ 

## 🐳 Docker Support

Build and run using Docker:

`docker compose up -d --build`

FASTAPI available at: http://localhost:8000

Swagger UI: http://localhost:8000/docs

## 📖 Future Enhancements

Add student quiz scoring & analytics

Integrate leaderboards & progress tracking


## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
