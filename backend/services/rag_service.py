# backend/services/rag_service.py

from typing import List, Dict, Any, Tuple
import os

from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.retrievers import ContextualCompressionRetriever

from backend.core.config import settings
from backend.core.logging_config import logger
from backend.core.models import Citation

# --- LangChain Component Imports ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_cohere import CohereRerank

# --- Initialize heavy components once on module load ---
logger.info("Initializing RAG service components...")
try:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0)
    embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)

    # Load ChromaDB from disk
    vector_store = Chroma(
        persist_directory=settings.CHROMA_DB_PATH, embedding_function=embeddings
    )

    # Create the advanced retriever
    base_retriever = vector_store.as_retriever(search_kwargs={"k": 10})
    compressor = CohereRerank(model="rerank-english-v3.0", top_n=4)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=base_retriever
    )
    logger.info("RAG service components initialized successfully.")
except Exception as e:
    logger.critical(f"Failed to initialize RAG service components: {e}", exc_info=True)
    # Handle failure gracefully, maybe set a flag
    llm = None
    compression_retriever = None


async def get_rag_response(
    query: str, chat_history: List[Dict[str, Any]]
) -> Tuple[str, List[Citation]]:
    """
    Gets a response from the RAG chain based on the query and chat history.

    Args:
        query (str): The user's current question.
        chat_history (List[Dict[str, Any]]): A list of previous messages in the chat.

    Returns:
        Tuple[str, List[Citation]]: A tuple containing the assistant's answer and a list of citations.
    """
    if not llm or not compression_retriever:
        raise RuntimeError(
            "RAG service is not available due to initialization failure."
        )

    # Create a new memory object for each request to isolate conversations
    # The `chat_history` is used to pre-populate this memory.
    memory = ConversationBufferMemory(
        memory_key="chat_history", return_messages=True, output_key="answer"
    )

    # Load past messages into memory
    for message in chat_history:
        if message["role"] == "user":
            memory.chat_memory.add_user_message(message["content"])
        elif message["role"] == "assistant":
            memory.chat_memory.add_ai_message(message["content"])

    # Create the conversational chain
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=compression_retriever,
        memory=memory,
        return_source_documents=True,
        verbose=True,
    )

    # Invoke the chain
    result = await chain.ainvoke({"question": query})
    answer = result.get(
        "answer", "I'm sorry, I encountered an error and cannot provide an answer."
    )

    # Format citations
    citations = []
    if result.get("source_documents"):
        unique_sources = set()
        for doc in result["source_documents"]:
            source_file = doc.metadata.get("source", "N/A")
            page_num = doc.metadata.get("page", -1) + 1
            unique_sources.add((os.path.basename(source_file), page_num))

        citations = [
            Citation(source_name=source, page_number=page)
            for source, page in sorted(list(unique_sources))
        ]

    return answer, citations
