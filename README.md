
---

# Production-Ready Conversational RAG System with RBAC

## 1. Project Overview

This project implements a complete, production-grade **Conversational Retrieval-Augmented Generation (RAG)** system with integrated **Role-Based Access Control (RBAC)**. It provides a secure, multi-user web interface where users can upload and manage PDF documents and web links. Users can then engage in a stateful dialogue to ask questions about the shared knowledge base, with the system's retrieval capabilities intelligently filtered based on their assigned role.

Built on a robust and scalable architecture using **FastAPI** for the backend and **Streamlit** for the frontend, this system is optimized for **speed, security, and reliability**. It delivers a seamless user experience with high-quality, cited answers from a shared pool of knowledge sources.

### Key Features

*   **Role-Based Access Control (RBAC):**
    *   **Manager:** Can upload/delete any content (PDFs/links) and retrieve answers from all sources.
    *   **Assistant Manager:** Can only upload/delete PDFs and can only retrieve answers from PDF sources.
    *   **Developer:** Can only upload/delete web links and can only retrieve answers from web sources.
*   **Secure Multi-User Authentication:** A complete user registration and login system using JWT tokens to secure all API endpoints and enforce role permissions.
*   **Unified Content Management:** Users can upload multiple PDFs or submit multiple URLs at once. The system processes this content asynchronously as a non-blocking background task.
*   **Advanced RAG Pipeline:**
    *   **Role-Aware Retrieval:** The retriever dynamically filters the vector store based on the user's role, ensuring they can only access information from permitted source types (`pdf` or `web`).
    *   **High-Quality Context:** A two-stage retrieval process uses a broad search in **ChromaDB** followed by a **Cohere Re-ranker** to ensure maximum relevance.
    *   **Powerful Generation:** Leverages Google's **Gemini 2.5 Flash** model for superior comprehension and answer generation.
    *   **Conversational Memory:** The system remembers the dialogue history to understand follow-up questions.
*   **Cited and Verifiable Answers:** Automatically provides the source for each answer, formatted as a filename and page number for PDFs, or a clickable link for web sources.
*   **Interactive Web Interface:** A user-friendly Streamlit application provides a complete chat experience, including chat history management and a content management dashboard.

## 2. System Architecture

The application is a decoupled client-server system designed for clarity and scalability.

*   **Backend (FastAPI):** A powerful Python server that exposes a RESTful API. It handles all core logic:
    *   User authentication and role management.
    *   API-level permission guards for content uploads/deletions.
    *   Asynchronous background processing for PDFs and web scraping.
    *   The core role-aware RAG pipeline.
    *   Interaction with MongoDB (for metadata) and ChromaDB (for vectors).
*   **Frontend (Streamlit):** A modern Python web application that provides the UI.

### The Role-Aware RAG Workflow

The heart of the system is the RAG pipeline, which intelligently adapts to the user's role:

1.  **Input & Authentication:** The user's query and their JWT token are sent to the backend. The user's role is extracted from the token.
2.  **Role-Based Retriever Selection:** A specific retriever is constructed based on the user's role. For an **Assistant Manager**, the retriever is configured to *only* search for documents where the metadata field `source_type` is `"pdf"`. For a **Developer**, it only searches where `source_type` is `"web"`. For a **Manager**, no filter is applied.
3.  **Question Condensing:** The `ConversationalRetrievalChain` uses the Gemini LLM to create a standalone question from the user's input and the chat history.
4.  **Filtered Retrieval & Re-ranking:** The standalone question is used to search the vector store **using the role-specific filtered retriever**. The top 10 results are then re-ranked by Cohere to select the best 4.
5.  **Final Answer Generation:** The re-ranked, role-appropriate documents are passed to Gemini 2.5 Flash to generate the final answer.
6.  **Citation & Storage:** Citations are formatted based on the source type, and the full conversation turn is saved to MongoDB.

## 3. Technology Stack

*   **Backend Framework:** FastAPI
*   **Frontend Framework:** Streamlit
*   **Database:** MongoDB
*   **Vector Store:** ChromaDB
*   **LLM for Generation:** Google Gemini 2.5 Flash
*   **Re-ranker:** Cohere (`rerank-english-v3.0`)
*   **Embedding Model:** `all-MiniLM-L6-v2`
*   **Core AI/RAG Library:** LangChain
*   **Web Scraping:** `langchain-community` with `BeautifulSoup4`
*   **Authentication:** JWT with `python-jose` and `passlib`

## 4. Full Project Setup (From Scratch)

### Step 1: Clone the Repository
```bash
git clone <your-repository-url>
cd your-project-folder
```

### Step 2: Set up a Python Virtual Environment
```bash
# Create the environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install CUDA and PyTorch (for NVIDIA GPUs)
This step is highly recommended for performance. If you don't have an NVIDIA GPU, PDF/web processing will be significantly slower.

1.  **Install NVIDIA CUDA Toolkit:** Download and install a version compatible with your drivers from the [NVIDIA CUDA Toolkit Archive](https://developer.nvidia.com/cuda-toolkit-archive) (e.g., CUDA 12.1).
2.  **Install PyTorch with CUDA Support:** Go to the [official PyTorch website](https://pytorch.org/get-started/locally/), use the configuration tool to generate the correct `pip` command for your system, and run it. It will look similar to this:
    ```bash
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    ```

### Step 4: Install Project Dependencies
Install all other required Python packages.
```bash
# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
pip install -r frontend-requirements.txt
```

### Step 5: Set up Environment Variables
Create a file named `.env` in the root directory and fill it with your credentials.

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

## 6. How to Run the Application

This application requires two separate terminal processes.

### Terminal 1: Run the Backend Server
```bash
# Make sure your virtual environment is activated
uvicorn backend.main:app --reload
```
Leave this terminal running.

### Terminal 2: Run the Frontend Application
```bash
# Open a new terminal and activate the virtual environment
streamlit run frontend/app.py
```
A new tab should automatically open in your web browser with the Streamlit application.

## 7. How to Use the App

1.  **Register Users:** Use the "Register" tab to create three users, one for each role: `manager`, `assistant_manager`, and `developer`.
2.  **Log In:** Log in as the `manager`.
3.  **Manage Content:**
    *   Click "Manage Content" in the sidebar.
    *   In the "Manage PDFs" tab, upload a few PDF documents.
    *   In the "Manage Web Links" tab, submit a few URLs for scraping.
4.  **Test RBAC:**
    *   **Log out** and log back in as the **developer**. Go to "Manage Content". You should only be able to add/delete links, not PDFs.
    *   Log back in as the **assistant manager**. You should only be able to add/delete PDFs, not links.
5.  **Chat:**
    *   Log in as each of the three roles and start a new chat.
    *   Ask questions whose answers are in the PDFs and questions whose answers are in the web links.
    *   Observe how the **manager** can get answers from both sources, while the **developer** and **assistant manager** can only get answers from their permitted source type.