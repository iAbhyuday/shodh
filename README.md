# Shodh (शोध) 🚀
*The Intelligent Research Assistant for the Modern Scholar.*

![Status](https://img.shields.io/badge/Status-In_Development-orange)
![License](https://img.shields.io/badge/License-MIT-blue)

> [!IMPORTANT]
> **This project is currently under active development.** Features effectively act as a proof-of-concept and may change.

## 🌟 Overview
**Shodh** (Hindi for "Discovery") is an agentic AI platform designed to supercharge research workflows. It combines a real-time paper feed with a powerful personal library, allowing researchers to ingest, understand, and synthesize complex academic papers using RAG and AI Agents.

## ✨ Key Features
-   **🔍 Discovery**: Daily trending papers from Hugging Face with **Multi-Tag Filtering** and smart search.
-   **🧠 Analysis**: **Chat with Papers** using RAG, generate ideas, and visualize concepts with auto-generated Mind Maps.
-   **📂 Library**: Drag-and-drop PDF ingestion powered by **Docling** and **ChromaDB**, organized into Projects.
-   **🤖 Agentic Core**: Autonomous agents that can read, reason, and summarize research for you.

## 🛠️ Tech Stack

### Frontend
![Next.js](https://img.shields.io/badge/Next.js_16-black?style=for-the-badge&logo=next.js&logoColor=white)
![React](https://img.shields.io/badge/React_19-20232a?style=for-the-badge&logo=react&logoColor=61DAFB)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)
![React Flow](https://img.shields.io/badge/React_Flow-ff0072?style=for-the-badge&logo=react&logoColor=white)

### Backend
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-black?style=for-the-badge)

### AI & Agents
![LlamaIndex](https://img.shields.io/badge/LlamaIndex-black?style=for-the-badge&logo=llama)
![CrewAI](https://img.shields.io/badge/CrewAI-orange?style=for-the-badge)
![Ollama](https://img.shields.io/badge/Ollama-white?style=for-the-badge&logo=ollama&logoColor=black)
![Docling](https://img.shields.io/badge/Docling-PDF_Parsing-purple?style=for-the-badge)

## 🚀 Getting Started

### Installation

1.  **Clone & Setup Backend**
    ```bash
    git clone https://github.com/yourusername/shodh.git
    cd shodh
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    ```

2.  **Setup Frontend**
    ```bash
    cd frontend
    npm install
    ```

### Running
-   **Backend**: `uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000`
-   **Frontend**: `npm run dev` (Runs on `localhost:3000`)

---
*Created with ❤️ by Abhyuday.*
