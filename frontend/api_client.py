import os
from typing import IO, Any, Dict, List, Optional

import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder


class ApiClient:
    """
    A client to interact with the backend FastAPI application.
    """

    def __init__(self, base_url: str):
        """
        Initializes the API client.

        Args:
            base_url (str): The base URL of the FastAPI backend (e.g., http://127.0.0.1:8000).
        """
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        self.token: Optional[str] = None

    def set_token(self, token: str):
        """
        Sets the JWT token for subsequent authenticated requests.
        """
        self.token = token
        self.headers["Authorization"] = f"Bearer {self.token}"

    def register(
        self, email: str, password: str, role: str
    ) -> Optional[Dict[str, Any]]:
        """
        Registers a new user.

        Returns:
            The user data if successful, None otherwise.
        """
        url = f"{self.base_url}/auth/register"
        payload = {"email": email, "password": password, "role": role}
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Registration failed: {e}")
            return None

    def login(self, email: str, password: str) -> Optional[str]:
        """
        Logs in a user and retrieves a JWT token.

        Returns:
            The JWT token if successful, None otherwise.
        """
        url = f"{self.base_url}/auth/login"
        # OAuth2PasswordRequestForm expects form data, not JSON
        form_data = {"username": email, "password": password}
        try:
            response = requests.post(url, data=form_data)
            response.raise_for_status()
            token_data = response.json()
            return token_data.get("access_token")
        except requests.exceptions.RequestException as e:
            print(f"Login failed: {e}")
            return None

    def upload_pdfs(self, files: List[IO]) -> bool:
        """
        Uploads one or more PDF files to the backend for processing.
        Returns True if accepted (HTTP 202), False otherwise.
        """
        if not self.token:
            print("Authentication token not set.")
            return False

        url = f"{self.base_url}/pdfs/upload"
        multipart = [
            ("files", (os.path.basename(f.name), f, "application/pdf")) for f in files
        ]
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            resp = requests.post(url, headers=headers, files=multipart)
            return resp.status_code == 202
        except requests.exceptions.RequestException as e:
            print(f"Failed to upload PDFs: {e}")
            return False

    def list_pdfs(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches all PDFs uploaded by the authenticated user.
        """
        if not self.token:
            print("Authentication token not set.")
            return None

        url = f"{self.base_url}/pdfs/"
        try:
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            pdfs = resp.json()
            # Normalize each PDF dict
            for pdf in pdfs:
                pdf["id"] = pdf.get("_id")
            return pdfs
        except requests.exceptions.RequestException as e:
            print(f"Failed to list PDFs: {e}")
            return None

    def delete_pdf(self, pdf_id: str) -> bool:
        """
        Deletes a PDF by its ID. Returns True on 204, False otherwise.
        """
        if not self.token:
            print("Authentication token not set.")
            return False

        url = f"{self.base_url}/pdfs/{pdf_id}"
        try:
            resp = requests.delete(url, headers=self.headers)
            return resp.status_code == 204
        except requests.exceptions.RequestException as e:
            print(f"Failed to delete PDF {pdf_id}: {e}")
            return False

    # --- Chat Management Methods ---

    def create_chat(self) -> Optional[Dict[str, Any]]:
        """
        Creates a new, empty chat session.
        """
        if not self.token:
            print("Authentication token not set.")
            return None

        url = f"{self.base_url}/chats/"
        try:
            response = requests.post(url, headers=self.headers)
            # This will raise an error for 4xx/5xx responses
            response.raise_for_status()
            # Pydantic on the backend ensures the response JSON has the correct format
            data = response.json()
            # Normalize MongoDB '_id' to 'id'
            data["id"] = data.get("_id")
            return data
        except requests.exceptions.RequestException as e:
            print(f"Failed to create new chat: {e}")
            return None

    def list_chats(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches the list of past chat sessions for the authenticated user.
        """
        if not self.token:
            print("Authentication token not set.")
            return None

        url = f"{self.base_url}/chats/"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            chats = response.json()
            # Normalize each chat dict
            for chat in chats:
                chat["id"] = chat.get("_id")
            return chats
        except requests.exceptions.RequestException as e:
            print(f"Failed to list chats: {e}")
            return None

    def get_chat_messages(self, chat_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves all messages for a specific chat session.
        """
        if not self.token or not chat_id:
            return None

        url = f"{self.base_url}/chats/{chat_id}/messages"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            msgs = response.json()
            # Normalize message IDs (optional; for consistency)
            for msg in msgs:
                msg["id"] = msg.get("_id")
            return msgs
        except requests.exceptions.RequestException as e:
            print(f"Failed to get messages for chat {chat_id}: {e}")
            return None

    def post_query(self, chat_id: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Posts a new query to a chat and gets the assistant's response.
        """
        if not self.token or not chat_id:
            return None

        url = f"{self.base_url}/chats/{chat_id}/query"
        payload = {"query": query}
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            msg = response.json()
            # Normalize the returned message ID
            msg["id"] = msg.get("_id")
            return msg
        except requests.exceptions.RequestException as e:
            print(f"Failed to post query to chat {chat_id}: {e}")
            return None
