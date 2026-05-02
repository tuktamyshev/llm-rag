# 🧠 RAG PLATFORM — FULL SYSTEM ARCHITECTURE

## 📌 Overview

This project is an API-first Retrieval-Augmented Generation (RAG) platform implemented as a modular monolith backend with multiple client applications.

The system allows:
- creation of isolated user projects
- ingestion of external data sources (web + telegram)
- semantic search over knowledge base
- LLM-based question answering
- external API access for third-party applications
- offline evaluation using RAGAS

---

# 🏗️ HIGH-LEVEL ARCHITECTURE

                    ┌──────────────────────┐
                    │     FRONTEND        │
                    │ ChatGPT-like UI     │
                    └─────────┬────────────┘
                              │
                              ▼
        ┌────────────────────────────────────┐
        │        BACKEND API                 │
        │   (FastAPI Modular Monolith)      │
        │                                    │
        │  API Layer (REST)                 │
        │  /chat /users /projects /sources  │
        │                                    │
        │  MODULES LAYER                    │
        │  users                            │
        │  projects                         │
        │  sources                          │
        │  ingestion                        │
        │  embeddings                       │
        │  vectordb                         │
        │  rag                              │
        │  chat                             │
        └──────────────┬─────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   INFRASTRUCTURE LAYER       │
        │                              │
        │ PostgreSQL (users/projects)  │
        │ Qdrant (vector DB)           │
        │ LLM API (OpenRouter/OpenAI)  │
        │ Scrapy / Telethon            │
        └──────────────┬───────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   EVALUATION LAYER          │
        │   (RAGAS OFFLINE)           │
        │                              │
        │ metrics + datasets + reports │
        └──────────────────────────────┘

---

# 🧱 BACKEND ARCHITECTURE (MODULAR MONOLITH)

## Core principle

Single backend application with strict module boundaries.

---

## 📦 Modules

Each module contains:

- models.py
- schemas.py
- repository.py
- service.py
- router.py

---

## Modules list:

### 👤 users
- registration
- authentication (JWT)
- user management

---

### 📁 projects
- project creation
- prompt configuration
- user-project relations

---

### 🌐 sources
- web sources
- telegram sources
- metadata storage

---

### 📥 ingestion
- data collection pipeline
- cleaning
- chunking
- scheduling

---

### 🧠 embeddings
- text embedding generation
- chunk transformation

---

### 📦 vectordb
- Qdrant integration
- vector storage
- similarity search (top-k)

---

### 🤖 rag
Core RAG pipeline:
- retrieval
- prompt building
- LLM interaction
- response orchestration

---

### 💬 chat
- user interaction layer
- connects API → RAG pipeline

---

# 🔄 RAG PIPELINE FLOW

User Question
   ↓
Chat Module
   ↓
RAG Service
   ↓
Retriever (Vector DB search)
   ↓
Context Builder
   ↓
Prompt Builder
   ↓
LLM (OpenRouter / GPT)
   ↓
Final Answer

---

# 🗄️ DATA STORAGE

## PostgreSQL
Stores:
- users
- projects
- sources
- metadata
- chat logs

---

## Vector DB (Qdrant)
Stores:
- text chunks
- embeddings
- metadata (project_id, source_id)

---

# 📥 INGESTION PIPELINE

Sources → Scraping → Cleaning → Chunking → Embeddings → Vector DB

Sources:
- Web (Scrapy)
- Telegram (Telethon)

---

# 🌐 API-FIRST DESIGN

Backend exposes REST API:

- POST /auth/*
- POST /projects/*
- POST /chat/{project_id}
- POST /sources/*

External systems do NOT access internal modules.

---

# 🖥️ FRONTEND (MAIN APP)

Main UI:
- ChatGPT-like interface
- project selection
- source management
- chat history

Tech:
- React + TypeScript

---

# 📦 EXAMPLES APPS (IMPORTANT)

Folder:
examples/

Contains external applications that consume backend API.

Example:
- cyber_threat_ui

Rules:
- ONLY HTTP API usage
- NO shared backend code
- fully independent frontend apps

---

# 🧪 EVALUATION LAYER (RAGAS)

RAGAS scores answers against retrieved context and `ground_truth` (faithfulness, answer relevancy, context precision, context recall). The same logic runs from the **CLI** (`evaluation/ragas/run_eval.py`) or from **optional HTTP** endpoints under `/api/v1/evaluation/` (`ragas`, `ragas-compare`). The compare endpoint, **per JSONL line**, creates an **ephemeral project**, ingests that line’s **`contexts`** into the vector index, runs the **RAG pipeline** (retrieve + LLM), **deletes** the project and vectors, and in parallel builds **no-RAG** answers (direct LLM, no documents). RAGAS runs on both branches (`rag` / `no_rag`, `rag_answers` / `no_rag_answers`). Ephemeral projects are owned by the user id from **`RAGAS_COMPARE_USER_ID`** (default `1`). These calls are not on the interactive chat hot path.

---

# 🚀 DESIGN PRINCIPLES

- API-first architecture
- modular monolith backend
- strict separation of concerns
- extensibility (easy to add microservices later)
- multi-project isolation
- production-like RAG pipeline

---

# 🧠 SYSTEM GOAL

To provide a scalable RAG-as-a-Service platform that allows external applications to use custom knowledge bases via API.