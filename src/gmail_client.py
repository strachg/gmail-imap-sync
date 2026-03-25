"""
Gmail IMAP Sync - Gmail Client
Handles all Gmail API interactions.
"""

import os
import json
import base64
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GmailClient:
    """
    Wrapper for Gmail API operations.
    Handles authentication, message import, and trash checking.
    """
    
    def __init__(self, gmail_label: Optional[str] = None):
        """
        Initialize Gmail client.
        
        Args:
            gmail_label: Optional label to apply to imported messages
        """
        self.gmail_label = gmail_label
        self.service = None
        self.label_id = None
        
    def connect(self) -> bool:
        """
        Authenticate and connect to Gmail API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            credentials_json = os.environ.get('GMAIL_CREDENTIALS')
            if not credentials_json:
                print("Error: GMAIL_CREDENTIALS environment variable not set")
                return False
            
            creds_data = json.loads(credentials_json)
            creds = Credentials.from_authorized_user_info(creds_data)
            self.service = build('gmail', 'v1', credentials=creds)
            
            # Resolve label ID if configured
            if self.gmail_label:
                self.label_id = self.get_label_id(self.gmail_label)
                if not self.label_id:
                    print(f"Error: Failed to resolve label ID for '{self.gmail_label}'. Aborting to prevent unlabeled import.")
                    return False
                print(f"Resolved label '{self.gmail_label}' to ID: {self.label_id}")
            
            return True
            
        except Exception as e:
            print(f"Gmail API connection failed: {e}")
            return False
    
    def import_message(self, raw_email: bytes) -> Optional[str]:
        """
        Import a message to Gmail using the Gmail API.
        
        Args:
            raw_email: Raw email message as bytes
            
        Returns:
            Gmail message ID if successful, None otherwise
        """
        if not self.service:
            print("Error: Gmail service not connected")
            return None
        
        try:
            # Encode message in base64url format
            message_bytes = base64.urlsafe_b64encode(raw_email).decode().rstrip('=')
            
            # Add 'INBOX' to make messages appear in the main inbox view,
            # and 'UNREAD' to ensure they are marked as new.
            labels = ['INBOX', 'UNREAD']
            
            if self.label_id:
                labels.append(self.label_id)
            
            message = {
                'raw': message_bytes,
                'labelIds': labels
            }
            
            # Import message
            result = self.service.users().messages().import_(
                userId='me',
                body=message,
                internalDateSource='dateHeader'
            ).execute()
            
            return result.get('id')
            
        except HttpError as error:
            print(f"Gmail import error: {error}")
            return None
        except Exception as e:
            print(f"Unexpected error during Gmail import: {e}")
            return None
    
    def is_message_deleted(self, gmail_id: str) -> bool:
        """
        Check if a message is in Gmail trash or permanently deleted.
        
        Args:
            gmail_id: Gmail message ID
            
        Returns:
            True if message is deleted or in trash, False otherwise
        """
        if not self.service:
            print("Error: Gmail service not connected")
            return False
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=gmail_id,
                format='minimal'
            ).execute()
            
            # Check if message is in trash
            labels = message.get('labelIds', [])
            return 'TRASH' in labels
            
        except HttpError as error:
            if error.resp.status == 404:
                # Message permanently deleted
                return True
            print(f"Error checking Gmail message {gmail_id}: {error}")
            return False
        except Exception as e:
            print(f"Unexpected error checking Gmail message: {e}")
            return False
    
    def get_label_id(self, label_name: str) -> Optional[str]:
        """
        Get or create a Gmail label.
        
        Args:
            label_name: Name of the label (can include hierarchy with /)
            
        Returns:
            Label ID if successful, None otherwise
        """
        if not self.service:
            return None
        
        try:
            # List all labels
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            # Check if label exists
            for label in labels:
                if label['name'] == label_name:
                    return label['id']
            
            # Create label if it doesn't exist
            label_object = {
                'name': label_name,
                'messageListVisibility': 'show',
                'labelListVisibility': 'labelShow'
            }
            
            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()
            
            return created_label['id']
            
        except HttpError as error:
            print(f"Error getting/creating label {label_name}: {error}")
            return None