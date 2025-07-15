
---

# Agentic RAG System

## 1. Project Overview

This project implements a complete, production-grade **Conversational Retrieval-Augmented Generation (RAG)** system. It provides a secure, multi-user web interface where users can upload private PDF documents and engage in a stateful dialogue to ask questions about their content.

The system is built on a robust, scalable backend using **FastAPI** and a clean, responsive frontend using **Streamlit**. The architecture has been meticulously optimized for **speed, reliability, and quality**, ensuring a seamless user experience. It provides direct, context-aware answers with precise citations and handles long-running background tasks like document processing efficiently.

### Key Features

*   **Secure Multi-User Authentication:** A complete user registration and login system using JWT tokens to secure all API endpoints.
*   **Asynchronous Bulk PDF Management:** Users can upload multiple PDFs at once. The system processes these files—extracting text, creating embeddings, and indexing them—as a non-blocking background task.
*   **Advanced RAG Pipeline:**
    *   **High-Quality Retrieval:** Uses a two-stage retrieval process. An initial broad search in a local **ChromaDB** vector store is intelligently refined by a **Cohere Re-ranker** to ensure maximum relevance.
    *   **Powerful Generation:** Leverages Google's **Gemini 2.5 Flash** model for superior comprehension and context-aware answer generation.
    *   **Conversational Memory:** The system remembers previous turns in the conversation to understand follow-up questions and provide contextually relevant answers.
*   **Cited and Verifiable Answers:** Automatically provides the source PDF filename and page number for the information used in each answer, ensuring trustworthiness.
*   **Efficient and Reliable Architecture:** Built around LangChain's robust `ConversationalRetrievalChain`, this system is optimized for speed and is not susceptible to the loops or parsing errors common in more complex agentic frameworks.
*   **Interactive Web Interface:** A user-friendly Streamlit application provides a complete chat experience, including chat history management and a dashboard for managing uploaded documents.

## 2. System Architecture

The application is a decoupled client-server system:

*   **Backend (FastAPI):** A powerful Python server that exposes a RESTful API for handling all core logic, including user authentication, file management, and the RAG pipeline. It uses MongoDB for persistent data storage.
*   **Frontend (Streamlit):** A modern Python web application that provides the user interface. It communicates with the backend via HTTP requests.

### The RAG Workflow

The core of the system is the RAG pipeline, which is designed for efficiency and quality:

1.  **Input & Memory:** The user's query and the chat session's history are sent to the backend.
2.  **Question Condensing (Internal LLM Call):** The `ConversationalRetrievalChain` uses the Gemini LLM in a quick, internal step to analyze the chat history and the new follow-up question. It synthesizes them into a single, standalone question (e.g., "What is the population of Paris?").
3.  **Broad-Phase Retrieval:** This new standalone question is used to perform a fast similarity search in our **ChromaDB** vector store, retrieving a broad set of 10 potentially relevant document chunks. This step maximizes **recall**.
4.  **Re-ranking Phase:** The retrieved documents and the condensed question are sent to the **Cohere Re-ranker API**. This specialized model re-orders the 10 documents based on true relevance and returns only the top 4. This step ensures **precision**.
5.  **Final Answer Generation:** The re-ranked, highly relevant documents, along with the original question and chat history, are passed to the Gemini 2.5 Flash LLM to generate a final, conversational answer.
6.  **Citation Extraction:** The source metadata (filename and page number) from the re-ranked documents is extracted and attached to the response.
7.  **Database Update:** The user's query and the assistant's full response (with citations) are saved to MongoDB.

## 3. Technology Stack

*   **Backend Framework:** FastAPI
*   **Frontend Framework:** Streamlit
*   **Database:** MongoDB (for users, PDFs, and chat logs)
*   **Vector Store:** ChromaDB (for document embeddings)
*   **LLM for Generation:** Google Gemini 2.5 Flash
*   **Re-ranker:** Cohere (`rerank-english-v3.0`)
*   **Embedding Model:** `all-MiniLM-L6-v2`
*   **Core AI/RAG Library:** LangChain
*   **Authentication:** JWT with `python-jose` and `passlib`

## 4. Full Project Setup (From Scratch)

Follow these steps to set up and run the project locally.

### Step 1: Clone the Repository

First, get the code onto your local machine.
```bash
git clone <your-repository-url>
cd your-project-folder
```

### Step 2: Set up a Python Virtual Environment

It is crucial to use a virtual environment to manage dependencies.

```bash
# Create the virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install CUDA and PyTorch (for NVIDIA GPUs)

This is the most critical step for performance. The embedding process is significantly faster on a GPU. If you do not have an NVIDIA GPU, you can skip to Step 4, but be aware that PDF processing will be much slower.

1.  **Install NVIDIA CUDA Toolkit:**
    *   Check your NVIDIA driver version by running `nvidia-smi` in your terminal.
    *   Go to the [NVIDIA CUDA Toolkit Archive](https://developer.nvidia.com/cuda-toolkit-archive) and download a version compatible with your driver (e.g., CUDA 12.1 is a common choice).
    *   Install the CUDA Toolkit.

2.  **Install PyTorch with CUDA Support:**
    *   Go to the [official PyTorch website](https://pytorch.org/get-started/locally/).
    *   Use the configuration tool to select your settings (e.g., `Stable`, `Windows/Linux`, `Pip`, `Python`, `CUDA 12.1`).
    *   It will generate a command. **Copy and run this exact command.** It will look something like this:
        ```bash
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
        ```
    This command installs the version of PyTorch that is compiled to work with your GPU.

### Step 4: Install Project Dependencies

Install all other required Python packages for both the frontend and backend.

```bash
# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
pip install -r frontend-requirements.txt
```

### Step 5: Set up Environment Variables

1.  Find the `.env.example` file in the project root (if provided) and rename it to `.env`.
2.  If not provided, create a file named `.env` in the root directory.
3.  Fill in the required values:

    ```env
    # /rag_project/.env

    # MongoDB: Replace with your connection string
    MONGO_URI="mongodb://localhost:27017" 
    DATABASE_NAME="rag_app_db"

    # JWT: Generate a long, random string for the secret key
    JWT_SECRET_KEY="your-super-secret-key-that-is-long-and-random"
    ALGORITHM="HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES=60

    # API Keys: Fill in your keys from Google and Cohere
    GOOGLE_API_KEY="your-google-api-key"
    COHERE_API_KEY="your-cohere-api-key"
    ```

## 5. How to Run the Application

This application requires two separate terminal processes.

### Terminal 1: Run the Backend Server

```bash
# Make sure your virtual environment is activated
# Navigate to the project root directory

uvicorn backend.main:app --reload
```
Leave this terminal running. It serves the API that the frontend will call.

### Terminal 2: Run the Frontend Application

```bash
# Make sure your virtual environment is activated
# Open a new terminal and navigate to the project root directory

streamlit run frontend/app.py
```
A new tab should automatically open in your web browser with the Streamlit application.

## 6. How the System Was Optimized

During development, we explored several architectures, including a fully "agentic" model where the LLM made every decision. We ultimately chose the current `ConversationalRetrievalChain` architecture for two key reasons: **speed** and **reliability**.

*   **Efficiency:** The final architecture minimizes API calls to the expensive Gemini LLM. It uses a single, efficient call to both condense the user's question and generate the final answer. The previous "true agentic" model required multiple back-and-forth LLM calls per query, which was slow and costly.
*   **Reliability:** The chain-based approach is deterministic and not prone to the parsing errors (`Invalid Format: Missing 'Action:'`) that plagued the ReAct agent. It also avoids low-level network errors (`WinError 10054`) by using synchronous calls for libraries that are not natively async, which is a more stable pattern.
*   **High-Quality Context:** We retained the most important enhancement from our experiments: the **Cohere Re-ranker**. By first retrieving a broad set of documents and then using a specialized model to re-rank for precision, we ensure the LLM receives the highest quality context possible, leading to better, more factual answers.