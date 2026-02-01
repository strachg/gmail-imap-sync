"""
Cloud Function Entry Point
This file imports the actual function implementations from the src package.
Required because Google Cloud Functions expects main.py at the source root.
"""

from src import sync_emails, sync_emails_scheduled