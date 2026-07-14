---
title: Bowen AI
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Bowen AI
# Bowen AI

An AI-powered academic assistant designed to help students access university information, understand course materials, search institutional knowledge, and receive personalized educational support through Retrieval-Augmented Generation (RAG).

## Overview

Bowen AI is a modern AI platform built to improve how students interact with academic resources. The system combines Large Language Models (LLMs), vector search, document processing, and conversational AI to deliver accurate and contextual responses.

The platform is designed around scalability, maintainability, and production-ready engineering practices.

---

## Key Features

### AI Assistant

* Natural language conversations
* Context-aware responses
* Conversation history
* Follow-up question support

### Retrieval-Augmented Generation (RAG)

* Semantic search
* Hybrid retrieval pipeline
* Citation support
* Document-grounded responses

### Document Intelligence

* PDF ingestion
* Automatic text extraction
* Chunking and embedding generation
* Knowledge indexing

### User Management

* Authentication and authorization
* Role-based access control
* User activity tracking

### Background Processing

* Automated document updates
* Scheduled knowledge synchronization
* Asynchronous task execution

---

## Architecture

The system follows a modular backend architecture with clear separation of concerns.

```text
Client
  ↓
FastAPI API Layer
  ↓
Business Services
  ↓
Retrieval Engine
  ↓
Vector Database (Qdrant)
  ↓
Large Language Model
```

Core Components:

* FastAPI
* Firestore
* Qdrant
* Gemini
* APScheduler
* JWT Authentication

---

## Technology Stack

### Backend

* Python
* FastAPI
* Pydantic
* APScheduler

### AI & Search

* Gemini
* Qdrant
* Embedding Models

### Database

* Firestore

### Security

* JWT Authentication
* Role-Based Access Control
* Security Middleware

---

## Project Structure

```text
app/

├── core/
├── middleware/
├── routes/
├── services/
├── schemas/
├── utils/
└── main.py
```

---

## Getting Started

### Clone Repository

```bash
git clone <repository-url>
cd bowen-ai
```

### Create Virtual Environment

```bash
python -m venv .venv
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

Create a `.env` file and configure required environment variables.

### Run Application

```bash
uvicorn app.main:app --reload
```

---

## Roadmap

* Vertical Slice Architecture migration
* MySQL migration
* Redis caching
* Improved observability
* Advanced analytics
* Expanded AI capabilities
* Comprehensive testing suite

---

## Engineering Goals

This project is intended to explore modern AI system design, retrieval-augmented generation, scalable backend architecture, and production engineering practices.

---

## Author

Badmus Samad

Computer Science Student

Focused on AI Systems, Backend Engineering, Cloud Computing, and Software Architecture.
