import time

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
    st.session_state.managing_pdfs = False
    st.session_state.chat_list = []
    st.session_state.current_chat_id = None
    st.session_state.messages = []


# --- UI Rendering Functions ---


def display_pdf_manager():
    """
    Displays the UI for uploading, viewing, and deleting PDFs.
    """
    import requests

    st.header("📚 PDF Management")

    # --- PDF Upload Section ---
    with st.expander("Upload New PDFs", expanded=True):
        uploaded_files = st.file_uploader(
            "Choose PDF files", accept_multiple_files=True, type="pdf"
        )
        if st.button("Upload and Process PDFs", key="upload_pdfs_btn"):
            if uploaded_files:
                with st.spinner(
                    "Uploading and processing PDFs... This may take a few minutes."
                ):
                    # Inline upload to avoid overriding Content-Type header
                    url = f"{api_client.base_url}/pdfs/upload"
                    # Prepare multipart payload
                    files_payload = [
                        (
                            "files",
                            (f.name, f, "application/pdf"),
                        )
                        for f in uploaded_files
                    ]
                    # Only send Authorization header
                    headers = {"Authorization": f"Bearer {api_client.token}"}
                    try:
                        resp = requests.post(url, headers=headers, files=files_payload)
                        success = resp.status_code == 202
                    except Exception as e:
                        success = False
                        st.error(f"Upload error: {e}")

                    if success:
                        st.success("Files submitted for processing.")
                        # Rerun to refresh the list
                        st.rerun()
                    else:
                        st.error(f"Upload failed (status code: {resp.status_code}).")
            else:
                st.warning("Please select at least one PDF file to upload.")

    st.markdown("---")

    # --- PDF List Section ---
    st.subheader("Your Uploaded Documents")
    pdfs = api_client.list_pdfs()
    if pdfs is None:
        st.error("Could not retrieve your PDF list. Is the backend running?")
        return

    if not pdfs:
        st.info("You haven't uploaded any PDFs yet. Use the form above to get started.")
    else:
        for pdf in pdfs:
            col1, col2, col3, col4 = st.columns([4, 3, 2, 1])
            with col1:
                title = pdf.get("title") or "_No title provided_"
                st.write(f"**Title:** {title}")
            with col2:
                st.write(f"**Filename:** {pdf.get('filename')}")
            with col3:
                st.write(f"**Pages:** {pdf.get('page_count')}")
            with col4:
                if st.button("Delete", key=f"delete_{pdf['id']}_{pdf.get('filename')}"):
                    with st.spinner("Deleting PDF..."):
                        success = api_client.delete_pdf(pdf["id"])
                        if success:
                            st.success(f"Deleted {pdf.get('filename')}")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete {pdf.get('filename')}")

    # Back to Chat button - only one instance with unique key
    if st.button("← Back to Chat", key="back_to_chat_unique"):
        st.session_state.managing_pdfs = False
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
                new_chat_data = api_client.create_chat()

            if new_chat_data:
                st.session_state.chat_list.insert(0, new_chat_data)
                st.session_state.current_chat_id = new_chat_data["id"]
                st.session_state.messages = []
                st.rerun()
            else:
                st.error("Failed to create new chat.")

        if st.button("📚 Manage PDFs", use_container_width=True, key="manage_pdfs_btn"):
            st.session_state.managing_pdfs = True
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
                    st.session_state.managing_pdfs = False
                    st.session_state.messages = []
                    st.rerun()

        if st.button("Logout", use_container_width=True, key="logout_btn"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


def display_main_chat_area():
    """
    Displays the main chat interface, including messages and the input form.
    """
    st.title("🤖 Agentic RAG Chat")

    if st.session_state.current_chat_id is None:
        st.info("Select a chat from the sidebar or start a new one.")
        return

    if not st.session_state.messages:
        with st.spinner("Loading chat history..."):
            msgs = api_client.get_chat_messages(st.session_state.current_chat_id)
            if msgs is not None:
                st.session_state.messages = msgs
            else:
                st.error("Could not load messages for this chat.")
                return

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("citations"):
                with st.expander("Sources"):
                    for cit in msg["citations"]:
                        st.caption(
                            f"- {cit['source_name']} (Page {cit['page_number']})"
                        )

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
            with st.chat_message("assistant"):
                st.markdown(response["content"])
                if response.get("citations"):
                    with st.expander("Sources"):
                        for cit in response["citations"]:
                            st.caption(
                                f"- {cit['source_name']} (Page {cit['page_number']})"
                            )

            if len(st.session_state.messages) <= 2:
                st.session_state.chat_list = []
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
    if st.session_state.managing_pdfs:
        display_pdf_manager()
    else:
        display_main_chat_area()
