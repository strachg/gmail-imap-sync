"""
Gmail IMAP Sync
Automatically sync emails from IMAP mailboxes to Gmail using Google Cloud Functions.
"""

__version__ = "0.1.0"
__author__ = "Grant Strachan"
__license__ = "MIT"

from .main import sync_emails, sync_emails_scheduled
from .sync_manager import EmailSyncManager
from .gmail_client import GmailClient
from .imap_client import IMAPClient
from .firestore_manager import FirestoreManager, cleanup_old_records, get_global_stats

__all__ = [
    'sync_emails',
    'sync_emails_scheduled',
    'EmailSyncManager',
    'GmailClient',
    'IMAPClient',
    'FirestoreManager',
    'cleanup_old_records',
    'get_global_stats',
]