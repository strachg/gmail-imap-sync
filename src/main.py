"""
Gmail IMAP Sync - Cloud Function Entry Points
Main module containing Cloud Function entry points and orchestration.
"""

import os
import json
from datetime import datetime
from typing import List, Dict
import functions_framework

from .sync_manager import EmailSyncManager
from .firestore_manager import cleanup_old_records


def get_mailbox_configs() -> List[dict]:
    """
    Parse mailbox configurations from environment variable.
    
    Returns:
        List of mailbox configuration dictionaries
    """
    mailboxes_config = os.environ.get('MAILBOXES_CONFIG')
    
    if not mailboxes_config:
        return []
    
    try:
        configs = json.loads(mailboxes_config)
        # If the config is not a list, wrap it in a list 
        return configs if isinstance(configs, list) else [configs]
    except Exception as e:
        print(f"Error parsing mailbox configs: {e}")
        return []


def process_all_mailboxes(mailboxes: List[dict]) -> Dict:
    """
    Process sync for all configured mailboxes.
    
    Args:
        mailboxes: List of mailbox configurations
        
    Returns:
        Dictionary containing results for all mailboxes
    """
    all_results = {
        'success': True,
        'timestamp': datetime.utcnow().isoformat(),
        'mailboxes': []
    }
    
    # Process each mailbox
    for mailbox_config in mailboxes:
        manager = EmailSyncManager(mailbox_config)
        result = {
            'mailbox_id': mailbox_config['id'],
            'success': False
        }
        
        try:
            if not manager.connect_imap():
                result['error'] = 'Failed to connect to IMAP'
                all_results['mailboxes'].append(result)
                continue
            
            if not manager.connect_gmail():
                result['error'] = 'Failed to connect to Gmail API'
                all_results['mailboxes'].append(result)
                continue
            
            # Sync new messages
            sync_stats = manager.sync_new_messages()
            
            # Check for deletions
            deletion_stats = manager.check_deletions()
            
            result['success'] = True
            result['sync'] = sync_stats
            result['deletions'] = deletion_stats
            
        except Exception as e:
            result['error'] = str(e)
            print(f"[{mailbox_config['id']}] Error: {e}")
            
        finally:
            manager.close()
            all_results['mailboxes'].append(result)
    
    # Cleanup old records (once for all mailboxes)
    cleanup_count = cleanup_old_records(days=30)
    all_results['cleanup_count'] = cleanup_count
    
    # Check if any mailbox failed
    failed = [r for r in all_results['mailboxes'] if not r.get('success')]
    if failed:
        all_results['success'] = False
    
    return all_results


@functions_framework.http
def sync_emails(request):
    """
    HTTP Cloud Function entry point.
    Syncs all configured mailboxes when triggered via HTTP.
    
    Args:
        request: HTTP request object
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    # Validate environment variables
    gmail_credentials = os.environ.get('GMAIL_CREDENTIALS')
    if not gmail_credentials:
        return {'error': 'Missing GMAIL_CREDENTIALS'}, 500
    
    mailboxes = get_mailbox_configs()
    if not mailboxes:
        return {'error': 'No mailboxes configured'}, 500
    
    # Process all mailboxes
    all_results = process_all_mailboxes(mailboxes)
    
    print(f"Sync completed: {len(all_results['mailboxes'])} mailboxes processed")
    return all_results, 200


@functions_framework.cloud_event
def sync_emails_scheduled(cloud_event):
    """
    Cloud Scheduler entry point.
    Syncs all configured mailboxes when triggered by Cloud Scheduler.
    
    Args:
        cloud_event: Cloud event object from scheduler
    """
    mailboxes = get_mailbox_configs()
    results = []
    
    for mailbox_config in mailboxes:
        manager = EmailSyncManager(mailbox_config)
        try:
            if manager.connect_imap() and manager.connect_gmail():
                sync_stats = manager.sync_new_messages()
                deletion_stats = manager.check_deletions()
                results.append({
                    'mailbox': mailbox_config['id'],
                    'imported': sync_stats['imported'],
                    'deleted': deletion_stats['deleted_from_source']
                })
        finally:
            manager.close()
    
    cleanup_old_records(days=30)
    print(f"Scheduled sync completed: {results}")