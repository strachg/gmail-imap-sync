"""
Gmail IMAP Sync - Firestore Manager
Handles all Firestore database operations for state tracking.
"""

from datetime import datetime, timedelta
from typing import Set, List, Dict
from google.cloud import firestore
from google.cloud.firestore import FieldFilter


# Collections in Firestore
MESSAGES_COLLECTION = 'synced_messages'
STATE_COLLECTION = 'sync_state'


class FirestoreManager:
    """
    Manages Firestore operations for tracking synced messages.
    Handles state persistence, queries, and cleanup.
    """
    
    def __init__(self, mailbox_id: str):
        """
        Initialize Firestore manager for a specific mailbox.
        
        Args:
            mailbox_id: Unique identifier for the mailbox
        """
        self.mailbox_id = mailbox_id
        self.db = firestore.Client()
        
    def get_synced_message_uids(self) -> Set[str]:
        """
        Get all UIDs of messages already synced for this mailbox.
        
        Returns:
            Set of UIDs that have been synced
        """
        try:
            docs = self.db.collection(MESSAGES_COLLECTION)\
                .where(filter=FieldFilter('mailbox_id', '==', self.mailbox_id))\
                .select(['uid'])\
                .stream()
            
            return {doc.to_dict()['uid'] for doc in docs}
            
        except Exception as e:
            print(f"Error fetching synced UIDs: {e}")
            return set()
    
    def save_synced_message(
        self,
        uid: str,
        gmail_id: str,
        subject: str,
        from_addr: str,
        message_id: str
    ):
        """
        Save a synced message record to Firestore.
        
        Args:
            uid: IMAP message UID
            gmail_id: Gmail message ID
            subject: Email subject
            from_addr: Sender address
            message_id: Email Message-ID header
        """
        try:
            # Create unique document ID combining mailbox and UID
            unique_id = f"{self.mailbox_id}:{uid}"
            
            doc_ref = self.db.collection(MESSAGES_COLLECTION).document(unique_id)
            doc_ref.set({
                'mailbox_id': self.mailbox_id,
                'uid': uid,
                'gmail_id': gmail_id,
                'synced_at': datetime.utcnow(),
                'subject': subject,
                'from': from_addr,
                'message_id': message_id,
                'deleted_from_source': False
            })
            
        except Exception as e:
            print(f"Error saving synced message: {e}")
    
    def get_pending_deletions(self, limit: int = 100) -> List[Dict]:
        """
        Get messages that have been synced but not yet deleted from source.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of message records with gmail_id, uid, unique_id, and subject
        """
        try:
            docs = self.db.collection(MESSAGES_COLLECTION)\
                .where(filter=FieldFilter('mailbox_id', '==', self.mailbox_id))\
                .where(filter=FieldFilter('deleted_from_source', '==', False))\
                .limit(limit)\
                .stream()
            
            records = []
            for doc in docs:
                data = doc.to_dict()
                records.append({
                    'unique_id': doc.id,
                    'gmail_id': data.get('gmail_id'),
                    'uid': data.get('uid'),
                    'subject': data.get('subject', '')
                })
            
            return records
            
        except Exception as e:
            print(f"Error fetching pending deletions: {e}")
            return []
    
    def mark_deleted_from_source(self, unique_id: str):
        """
        Mark a message as deleted from the IMAP source.
        
        Args:
            unique_id: Unique document ID (mailbox_id:uid)
        """
        try:
            doc_ref = self.db.collection(MESSAGES_COLLECTION).document(unique_id)
            doc_ref.update({
                'deleted_from_source': True,
                'deleted_at': datetime.utcnow()
            })
            
        except Exception as e:
            print(f"Error marking message as deleted: {e}")
    
    def get_mailbox_stats(self) -> Dict:
        """
        Get statistics for this mailbox.
        
        Returns:
            Dictionary with counts of total, synced, and deleted messages
        """
        try:
            # Total synced messages
            total_docs = self.db.collection(MESSAGES_COLLECTION)\
                .where(filter=FieldFilter('mailbox_id', '==', self.mailbox_id))\
                .count()\
                .get()
            
            # Deleted from source
            deleted_docs = self.db.collection(MESSAGES_COLLECTION)\
                .where(filter=FieldFilter('mailbox_id', '==', self.mailbox_id))\
                .where(filter=FieldFilter('deleted_from_source', '==', True))\
                .count()\
                .get()
            
            total_count = total_docs[0][0].value if total_docs else 0
            deleted_count = deleted_docs[0][0].value if deleted_docs else 0
            
            return {
                'total_synced': total_count,
                'deleted_from_source': deleted_count,
                'pending_deletion': total_count - deleted_count
            }
            
        except Exception as e:
            print(f"Error getting mailbox stats: {e}")
            return {
                'total_synced': 0,
                'deleted_from_source': 0,
                'pending_deletion': 0
            }


def cleanup_old_records(days: int = 30) -> int:
    """
    Remove Firestore records for messages deleted more than X days ago.
    This is a global cleanup function for all mailboxes.
    
    Args:
        days: Number of days after which to clean up deleted records
        
    Returns:
        Number of records cleaned up
    """
    try:
        db = firestore.Client()
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        docs = db.collection(MESSAGES_COLLECTION)\
            .where(filter=FieldFilter('deleted_from_source', '==', True))\
            .where(filter=FieldFilter('deleted_at', '<', cutoff))\
            .stream()
        
        count = 0
        for doc in docs:
            doc.reference.delete()
            count += 1
        
        if count > 0:
            print(f"Cleaned up {count} old records")
        
        return count
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return 0


def get_global_stats() -> Dict:
    """
    Get global statistics across all mailboxes.
    
    Returns:
        Dictionary with global counts
    """
    try:
        db = firestore.Client()
        
        # Total synced messages across all mailboxes
        total_docs = db.collection(MESSAGES_COLLECTION).count().get()
        
        # Total deleted from source
        deleted_docs = db.collection(MESSAGES_COLLECTION)\
            .where(filter=FieldFilter('deleted_from_source', '==', True))\
            .count()\
            .get()
        
        total_count = total_docs[0][0].value if total_docs else 0
        deleted_count = deleted_docs[0][0].value if deleted_docs else 0
        
        return {
            'total_synced': total_count,
            'deleted_from_source': deleted_count,
            'pending_deletion': total_count - deleted_count
        }
        
    except Exception as e:
        print(f"Error getting global stats: {e}")
        return {
            'total_synced': 0,
            'deleted_from_source': 0,
            'pending_deletion': 0
        }