"""
Gmail IMAP Sync - IMAP Client
Handles all IMAP server interactions.
"""

import imaplib
import email
from email import policy
from typing import List, Dict, Set, Optional


class IMAPClient:
    """
    Wrapper for IMAP server operations.
    Handles connection, message fetching, and deletion.
    """
    
    def __init__(self, host: str, port: int, user: str, password: str):
        """
        Initialize IMAP client.
        
        Args:
            host: IMAP server hostname
            port: IMAP port (typically 993 for SSL)
            user: IMAP username
            password: IMAP password
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.connection = None
        
    def connect(self) -> bool:
        """
        Connect and authenticate to IMAP server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.connection = imaplib.IMAP4_SSL(self.host, self.port)
            self.connection.login(self.user, self.password)
            return True
        except Exception as e:
            print(f"IMAP connection failed to {self.host}:{self.port} - {e}")
            return False
    
    def fetch_new_messages(
        self, 
        synced_uids: Set[str], 
        limit: int = 50,
        folder: str = 'INBOX'
    ) -> List[Dict]:
        """
        Fetch messages from IMAP that haven't been synced yet.
        
        Args:
            synced_uids: Set of UIDs that have already been synced
            limit: Maximum number of messages to fetch
            folder: IMAP folder to fetch from (default: INBOX)
            
        Returns:
            List of message dictionaries containing:
                - uid: Message UID
                - raw: Raw email bytes
                - subject: Email subject
                - from: Sender address
                - date: Date header
                - message_id: Message-ID header
        """
        if not self.connection:
            print("Error: IMAP connection not established")
            return []
        
        new_messages = []
        
        try:
            # Select the folder
            status, _ = self.connection.select(folder)
            if status != 'OK':
                print(f"Error: Could not select folder {folder}")
                return []
            
            # Search for all messages
            status, message_ids = self.connection.search(None, 'ALL')
            if status != 'OK':
                print("Error: Could not search messages")
                return []
            
            if not message_ids[0]:
                print("No messages found in folder")
                return []
            
            # Get list of message IDs
            msg_id_list = message_ids[0].split()
            
            # Process messages in reverse (newest first), up to limit
            for msg_id in reversed(msg_id_list[-limit:]):
                try:
                    # Fetch UID for this message
                    status, uid_data = self.connection.fetch(msg_id, '(UID)')
                    if status != 'OK':
                        continue
                    
                    # Extract UID from response
                    uid_str = uid_data[0].decode() if isinstance(uid_data[0], bytes) else str(uid_data[0])
                    uid = self._extract_uid(uid_str, msg_id)
                    
                    # Skip if already synced
                    if uid in synced_uids:
                        continue
                    
                    # Fetch the full message
                    status, msg_data = self.connection.fetch(msg_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email, policy=policy.default)
                    
                    new_messages.append({
                        'uid': uid,
                        'raw': raw_email,
                        'subject': msg.get('Subject', ''),
                        'from': msg.get('From', ''),
                        'date': msg.get('Date', ''),
                        'message_id': msg.get('Message-ID', '')
                    })
                    
                except Exception as e:
                    print(f"Error processing message {msg_id}: {e}")
                    continue
            
            return new_messages
            
        except Exception as e:
            print(f"Error fetching messages: {e}")
            return []
    
    def delete_message(self, uid: str, folder: str = 'INBOX') -> bool:
        """
        Delete a message from IMAP server by UID.
        
        Args:
            uid: Message UID to delete
            folder: IMAP folder (default: INBOX)
            
        Returns:
            True if deletion successful, False otherwise
        """
        if not self.connection:
            print("Error: IMAP connection not established")
            return False
        
        try:
            # Select the folder
            self.connection.select(folder)
            
            # Search for message by UID
            status, msg_ids = self.connection.uid('SEARCH', None, f'UID {uid}')
            if status != 'OK' or not msg_ids[0]:
                print(f"Message with UID {uid} not found")
                return False
            
            # Mark for deletion
            self.connection.uid('STORE', uid, '+FLAGS', '\\Deleted')
            
            # Expunge to permanently delete
            self.connection.expunge()
            
            print(f"Deleted message UID {uid} from IMAP")
            return True
            
        except Exception as e:
            print(f"Error deleting message UID {uid}: {e}")
            return False
    
    def _extract_uid(self, uid_str: str, msg_id: bytes) -> str:
        """
        Extract UID from IMAP fetch response.
        
        Args:
            uid_str: UID response string from IMAP
            msg_id: Message ID as fallback
            
        Returns:
            Extracted UID as string
        """
        try:
            if 'UID ' in uid_str:
                # Extract UID from response like "1 (UID 12345)"
                uid = uid_str.split('UID ')[1].split(')')[0].strip()
                return uid
        except:
            pass
        
        # Fallback to message ID
        return msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
    
    def get_folder_list(self) -> List[str]:
        """
        Get list of available folders/mailboxes.
        
        Returns:
            List of folder names
        """
        if not self.connection:
            return []
        
        try:
            status, folders = self.connection.list()
            if status != 'OK':
                return []
            
            folder_names = []
            for folder in folders:
                # Parse folder name from response
                # Format: (flags) "delimiter" "name"
                parts = folder.decode().split('"')
                if len(parts) >= 3:
                    folder_names.append(parts[-2])
            
            return folder_names
            
        except Exception as e:
            print(f"Error getting folder list: {e}")
            return []
    
    def close(self):
        """Close IMAP connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass