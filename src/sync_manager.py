"""
Gmail IMAP Sync - Sync Manager
Manages the synchronization process for a single mailbox.
"""

from typing import Dict, List, Optional
from datetime import datetime

from .gmail_client import GmailClient
from .imap_client import IMAPClient
from .firestore_manager import FirestoreManager


class EmailSyncManager:
    """
    Manages email synchronization for a single mailbox.
    Coordinates IMAP fetching, Gmail importing, and state tracking.
    """
    
    def __init__(self, mailbox_config: dict):
        """
        Initialize sync manager for a mailbox.
        
        Args:
            mailbox_config: Configuration dictionary containing:
                - id: Unique mailbox identifier
                - host: IMAP server hostname
                - port: IMAP port (default 993)
                - user: IMAP username
                - password: IMAP password
                - gmail_label: Optional Gmail label to apply
        """
        self.config = mailbox_config
        self.mailbox_id = mailbox_config['id']
        
        # Initialize clients
        self.imap_client = IMAPClient(
            host=mailbox_config['host'],
            port=int(mailbox_config.get('port', 993)),
            user=mailbox_config['user'],
            password=mailbox_config['password']
        )
        
        self.gmail_client = GmailClient(
            gmail_label=mailbox_config.get('gmail_label')
        )
        
        self.firestore = FirestoreManager(self.mailbox_id)
        
    def connect_imap(self) -> bool:
        """
        Connect to IMAP server.
        
        Returns:
            True if connection successful, False otherwise
        """
        success = self.imap_client.connect()
        if success:
            print(f"[{self.mailbox_id}] Connected to IMAP: {self.config['host']}")
        else:
            print(f"[{self.mailbox_id}] IMAP connection failed")
        return success
    
    def connect_gmail(self) -> bool:
        """
        Connect to Gmail API.
        
        Returns:
            True if connection successful, False otherwise
        """
        success = self.gmail_client.connect()
        if success:
            print(f"[{self.mailbox_id}] Connected to Gmail API")
        else:
            print(f"[{self.mailbox_id}] Gmail API connection failed")
        return success
    
    def sync_new_messages(self, limit: int = 50) -> dict:
        """
        Fetch and import new messages from IMAP to Gmail.
        
        Args:
            limit: Maximum number of messages to fetch per sync
            
        Returns:
            Dictionary with sync statistics:
                - mailbox_id: Mailbox identifier
                - fetched: Number of messages fetched
                - imported: Number of messages successfully imported
                - errors: Number of errors encountered
        """
        stats = {
            'mailbox_id': self.mailbox_id,
            'fetched': 0,
            'imported': 0,
            'errors': 0
        }
        
        # Get already synced message UIDs
        synced_uids = self.firestore.get_synced_message_uids()
        
        # Fetch new messages from IMAP
        new_messages = self.imap_client.fetch_new_messages(
            synced_uids=synced_uids,
            limit=limit
        )
        stats['fetched'] = len(new_messages)
        
        # Import each message to Gmail
        for msg in new_messages:
            gmail_id = self.gmail_client.import_message(msg['raw'])
            
            if gmail_id:
                # Save to Firestore
                self.firestore.save_synced_message(
                    uid=msg['uid'],
                    gmail_id=gmail_id,
                    subject=msg['subject'],
                    from_addr=msg['from'],
                    message_id=msg['message_id']
                )
                stats['imported'] += 1
                print(f"[{self.mailbox_id}] Imported: {msg['subject']}")
            else:
                stats['errors'] += 1
        
        return stats
    
    def check_deletions(self, limit: int = 100) -> dict:
        """
        Check for messages deleted in Gmail and remove from IMAP source.
        
        Args:
            limit: Maximum number of messages to check per run
            
        Returns:
            Dictionary with deletion statistics:
                - mailbox_id: Mailbox identifier
                - checked: Number of messages checked
                - deleted_from_source: Number deleted from IMAP
                - errors: Number of errors encountered
        """
        stats = {
            'mailbox_id': self.mailbox_id,
            'checked': 0,
            'deleted_from_source': 0,
            'errors': 0
        }
        
        # Get messages not yet deleted from source
        pending_deletions = self.firestore.get_pending_deletions(limit=limit)
        stats['checked'] = len(pending_deletions)
        
        for record in pending_deletions:
            gmail_id = record['gmail_id']
            uid = record['uid']
            
            # Check if message is in Gmail trash
            is_deleted = self.gmail_client.is_message_deleted(gmail_id)
            
            if is_deleted:
                # Delete from IMAP
                if self.imap_client.delete_message(uid):
                    # Mark as deleted in Firestore
                    self.firestore.mark_deleted_from_source(record['unique_id'])
                    stats['deleted_from_source'] += 1
                    print(f"[{self.mailbox_id}] Deleted from source: {record.get('subject', 'Unknown')}")
                else:
                    stats['errors'] += 1
        
        return stats
    
    def close(self):
        """Close all client connections."""
        self.imap_client.close()
        # Gmail client doesn't need explicit closing