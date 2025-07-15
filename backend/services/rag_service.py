# backend/services/rag_service.py

from typing import List, Dict, Any, Tuple
import os

from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.retrievers import ContextualCompressionRetriever
from langchain_core.retrievers import BaseRetriever

from backend.core.config import settings
from backend.core.logging_config import logger
from backend.core.models import Citation, Role
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_cohere import CohereRerank

logger.info("Initializing RAG service components...")
try:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0)
    embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)
    vector_store = Chroma(
        persist_directory=settings.CHROMA_DB_PATH, embedding_function=embeddings
    )
    logger.info("RAG service components initialized successfully.")
except Exception as e:
    logger.critical(f"Failed to initialize RAG service components: {e}", exc_info=True)
    llm = None
    vector_store = None


def get_retriever_for_role(role: Role) -> BaseRetriever:
    """
    Factory function to create a role-specific retriever.
    This version correctly handles the 'manager' case by omitting the filter.
    """
    logger.info(f"Creating retriever for role: '{role}'")

    # Start with the base search arguments
    search_kwargs = {"k": 10}

    # Conditionally add the filter based on the user's role
    if role == "assistant_manager":
        logger.info("Applying 'pdf' source filter for assistant_manager.")
        search_kwargs["filter"] = {"source_type": "pdf"}
    elif role == "developer":
        logger.info("Applying 'web' source filter for developer.")
        search_kwargs["filter"] = {"source_type": "web"}
    elif role == "manager":
        logger.info("No filter applied for manager role.")
    else:
        logger.warning(f"Unknown role '{role}'. Defaulting to restrictive filter.")
        search_kwargs["filter"] = {"source_type": "none"}

    base_retriever = vector_store.as_retriever(search_kwargs=search_kwargs)

    compressor = CohereRerank(model="rerank-english-v3.0", top_n=4)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=base_retriever
    )

    return compression_retriever


def get_rag_response(
    query: str, chat_history: List[Dict[str, Any]], role: Role
) -> Tuple[str, List[Citation]]:
    """
    Gets a response from the RAG chain using a role-specific retriever.

    Args:
        query (str): The user's current question.
        chat_history (List[Dict[str, Any]]): The past messages.
        role (Role): The role of the user making the query.

    Returns:
        A tuple containing the assistant's answer and a list of citations.
    """
    if not llm or not vector_store:
        raise RuntimeError(
            "RAG service is not available due to initialization failure."
        )

    role_specific_retriever = get_retriever_for_role(role)

    memory = ConversationBufferMemory(
        memory_key="chat_history", return_messages=True, output_key="answer"
    )
    for message in chat_history:
        if message["role"] == "user":
            memory.chat_memory.add_user_message(message["content"])
        elif message["role"] == "assistant":
            memory.chat_memory.add_ai_message(message["content"])

    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=role_specific_retriever,
        memory=memory,
        return_source_documents=True,
        verbose=True,
    )

    result = chain.invoke({"question": query})
    answer = result.get("answer", "I'm sorry, I encountered an error.")

    citations = []
    unique_sources = set()

    if result.get("source_documents"):
        for doc in result["source_documents"]:
            metadata = doc.metadata
            source = metadata.get("source")

            if not source:
                continue

            if source.startswith("http"):
                if source not in unique_sources:
                    title = metadata.get("title", source)
                    citations.append(
                        Citation(
                            source_name=source, source_title=title, page_number=None
                        )
                    )
                    unique_sources.add(source)
            else:
                filename = os.path.basename(source)
                page = metadata.get("page", -1) + 1
                unique_key = (filename, page)

                if unique_key not in unique_sources:
                    citations.append(
                        Citation(
                            source_name=filename, page_number=page, source_title=None
                        )
                    )
                    unique_sources.add(unique_key)

    return answer, citations
