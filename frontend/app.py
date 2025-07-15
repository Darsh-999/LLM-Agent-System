import os
import time

import requests
import streamlit as st
from api_client import ApiClient

# --- Page Configuration ---
st.set_page_config(page_title="Agentic RAG System", page_icon="🤖", layout="wide")

# --- API Client Initialization ---
api_client = ApiClient(base_url="http://127.0.0.1:8000")

# --- Session State Management ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.jwt_token = None
    st.session_state.user_email = ""
    st.session_state.error_message = ""
    st.session_state.managing_content = False  # Fixed: Added missing initialization
    st.session_state.chat_list = []
    st.session_state.current_chat_id = None
    st.session_state.messages = []


# --- UI Rendering Functions ---


def display_content_manager():
    """
    Displays a unified UI for managing both PDFs and Web Links using tabs.
    """
    st.header("📚 Content Management")
    st.info("Manage the knowledge sources for your RAG system.")

    pdf_tab, link_tab = st.tabs(["Manage PDFs", "Manage Web Links"])

    # --- PDF Management Tab ---
    with pdf_tab:
        st.subheader("Upload New PDFs")
        with st.form("pdf_upload_form", clear_on_submit=True):
            uploaded_files = st.file_uploader(
                "Choose PDF files",
                accept_multiple_files=True,
                type="pdf",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Upload and Process PDFs")
            if submitted and uploaded_files:
                with st.spinner(
                    "Uploading and processing... This may take a few minutes."
                ):
                    # Using the direct requests call we validated earlier
                    url = f"{api_client.base_url}/pdfs/upload"
                    files_payload = [
                        ("files", (f.name, f, "application/pdf"))
                        for f in uploaded_files
                    ]
                    headers = {"Authorization": f"Bearer {api_client.token}"}
                    try:
                        resp = requests.post(url, headers=headers, files=files_payload)
                        if resp.status_code == 202:
                            st.success(
                                "Files submitted for processing! The list will refresh shortly."
                            )
                        else:
                            st.error(
                                f"Upload failed (status code: {resp.status_code})."
                            )
                    except Exception as e:
                        st.error(f"An error occurred during upload: {e}")
                time.sleep(2)  # Give a moment for the user to see the message
                st.rerun()
            elif submitted:
                st.warning("Please select at least one PDF file.")

        st.markdown("---")
        st.subheader("Your Uploaded Documents")
        pdfs = api_client.list_pdfs()
        if pdfs:
            for pdf in pdfs:
                c1, c2, c3 = st.columns([4, 4, 1])
                c1.write(f"**Title:** {pdf.get('title', 'N/A')}")
                c2.write(f"**Filename:** {os.path.basename(pdf.get('filename', ''))}")
                if c3.button("Delete", key=f"del_pdf_{pdf.get('id')}"):
                    with st.spinner("Deleting PDF..."):
                        success = api_client.delete_pdf(pdf.get("id"))
                        if success:
                            st.success(f"PDF deleted successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to delete PDF.")
        else:
            st.info("No PDFs uploaded yet.")

    # --- Web Link Management Tab ---
    with link_tab:
        st.subheader("Submit New Web Links")
        with st.form("link_submit_form", clear_on_submit=True):
            urls_input = st.text_area("Enter one URL per line")
            submitted = st.form_submit_button("Scrape and Process URLs")
            if submitted and urls_input:
                urls = [url.strip() for url in urls_input.split("\n") if url.strip()]
                if urls:
                    with st.spinner("Submitting URLs for scraping..."):
                        success = api_client.submit_links(urls)
                    if success:
                        st.success(
                            "URLs submitted for processing! The list will refresh shortly."
                        )
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Failed to submit URLs.")
                else:
                    st.warning("Please enter at least one valid URL.")

        st.markdown("---")
        st.subheader("Your Scraped Web Links")
        links = api_client.list_links()
        if links:
            for link in links:
                c1, c2, c3 = st.columns([4, 4, 1])
                c1.write(f"**Title:** {link.get('title', 'N/A')}")
                c2.link_button(link.get("url"), link.get("url"))
                if c3.button("Delete", key=f"del_link_{link.get('id')}"):
                    with st.spinner("Deleting link..."):
                        success = api_client.delete_link(link.get("id"))
                        if success:
                            st.success("Link deleted successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to delete link.")
        else:
            st.info("No web links submitted yet.")

    if st.button("← Back to Chat", key="back_to_chat"):
        st.session_state.managing_content = False
        st.rerun()


def display_sidebar():
    """
    Displays the sidebar with chat history and controls.
    """
    with st.sidebar:
        st.title("Navigation")
        st.write(f"Welcome, {st.session_state.user_email}!")

        if st.button("✨ New Chat", use_container_width=True, key="new_chat_btn"):
            with st.spinner("Creating new chat..."):
                new_chat = api_client.create_chat()
            if new_chat:
                st.session_state.chat_list.insert(0, new_chat)
                st.session_state.current_chat_id = new_chat.get("id")
                st.session_state.messages = []
                st.session_state.managing_content = False  # Ensure we're in chat mode
                st.rerun()
            else:
                st.error("Failed to create new chat.")

        if st.button(
            "📚 Manage Content", use_container_width=True, key="manage_content_btn"
        ):
            st.session_state.managing_content = True
            st.rerun()

        st.subheader("Recent Chats")
        if not st.session_state.chat_list:
            chats = api_client.list_chats()
            if chats is not None:
                st.session_state.chat_list = chats

        if not st.session_state.chat_list:
            st.info("No chats yet.")
        else:
            for index, chat in enumerate(st.session_state.chat_list):
                title = chat.get("title", f"Chat {index+1}")
                chat_id = chat["id"]
                key = f"chat_btn_{index}_{chat_id}"
                if st.button(title, key=key, use_container_width=True):
                    st.session_state.current_chat_id = chat_id
                    st.session_state.managing_content = False
                    st.session_state.messages = []
                    st.rerun()

        if st.button("Logout", use_container_width=True, key="logout_btn"):
            logout()


def logout():
    """Resets the session state to log the user out."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def display_main_chat_area():
    """
    Displays the main chat interface.
    """
    st.title("🤖 Agentic RAG Chat")

    if st.session_state.current_chat_id is None:
        st.info("Select a chat from the sidebar or start a new one.")
        return

    # Load and display chat history
    if not st.session_state.messages:
        with st.spinner("Loading chat history..."):
            messages = api_client.get_chat_messages(st.session_state.current_chat_id)
            st.session_state.messages = messages if messages else []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("citations"):
                with st.expander("Sources"):
                    for citation in msg["citations"]:
                        # Check if it's a web link or a PDF
                        if citation.get('page_number') is not None:
                            # It's a PDF citation
                            st.caption(f"- {citation['source_name']} (Page {citation['page_number']})")
                        else:
                            # It's a web link citation
                            title = citation['source_title'] or citation['source_name']
                            st.caption(f"- [{title}]({citation['source_name']})")

    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        st.session_state.messages.append(
            {"role": "user", "content": prompt, "citations": []}
        )
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Thinking..."):
            response = api_client.post_query(st.session_state.current_chat_id, prompt)

        if response:
            st.session_state.messages.append(response)
            # Rerun to display the new message and citations
            st.rerun()
        else:
            st.error("Failed to get a response from the assistant.")


def display_login_page():
    """
    Displays the login and registration forms.
    """
    st.title("Welcome to the Agentic RAG System")

    if st.session_state.error_message:
        st.error(st.session_state.error_message)
        st.session_state.error_message = ""

    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.form_submit_button("Login"):
                if not email or not password:
                    st.session_state.error_message = (
                        "Please enter both email and password."
                    )
                else:
                    token = api_client.login(email, password)
                    if token:
                        st.session_state.logged_in = True
                        st.session_state.jwt_token = token
                        st.session_state.user_email = email
                        api_client.set_token(token)
                        st.rerun()
                    else:
                        st.session_state.error_message = (
                            "Login failed. Please check your credentials."
                        )
                        st.rerun()

    with register_tab:
        with st.form("register_form"):
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input(
                "Password", type="password", key="reg_password"
            )
            reg_role = st.selectbox(
                "Role", ["manager", "assistant_manager", "developer"], key="reg_role"
            )
            if st.form_submit_button("Register"):
                if not reg_email or not reg_password:
                    st.session_state.error_message = "Please fill all fields."
                else:
                    user = api_client.register(reg_email, reg_password, reg_role)
                    if user:
                        st.success("Registration successful! Please login.")
                    else:
                        st.session_state.error_message = (
                            "Registration failed. The email might already be in use."
                        )
                        st.rerun()


# --- Main Application Logic ---
if not st.session_state.logged_in:
    display_login_page()
else:
    if api_client.token is None:
        api_client.set_token(st.session_state.jwt_token)

    display_sidebar()

    if st.session_state.get("managing_content", False):
        display_content_manager()
    else:
        display_main_chat_area()
