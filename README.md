# Gmail IMAP Sync

A Google Cloud Function that automatically syncs emails from multiple IMAP mailboxes to Gmail with intelligent deletion tracking. Designed to run entirely within Google Cloud's free tier limits.

## 🎯 Why This Project?

Google discontinued POP3 support for Gmail sync. This solution provides a free, automated way to:
- Import emails from any IMAP server (Siteground, cPanel, etc.) to Gmail
- Support multiple mailboxes in a single deployment
- Safely delete emails from source only after they're deleted in Gmail
- Run completely free using Google Cloud's generous free tier

## ✨ Features

### Core Functionality
- **Multi-Mailbox Support**: Sync many ( see - Usage Scenarios ) IMAP mailboxes to a single Gmail account. ( only limited when trying to stay within free tier, theoretically unlimited otherwise )
- **Safe Deletion**: Only deletes emails from source AFTER they're moved to Gmail trash
- **State Tracking**: Uses Firestore to track which emails have been synced and deleted
- **Deduplication**: Prevents duplicate imports using message UIDs
- **Automatic Cleanup**: Removes old tracking records after 30 days
- **Error Recovery**: Individual mailbox failures don't affect others

### Technical Features
- **Gmail API Integration**: Official API for reliable email import
- **IMAP Support**: Works with any IMAP server (Siteground, cPanel, Office365, etc.)
- **Scheduled Execution**: Configurable sync frequency via Cloud Scheduler
- **Organized Labels**: Optional Gmail labels per mailbox (e.g., "Imported/Work")
- **Comprehensive Logging**: Detailed logs for each mailbox operation
- **Stateful Processing**: Tracks sync progress and deletion status
- **Batch Processing**: Processes up to 50 messages per sync to stay within limits

### Operational Features
- **Zero Maintenance**: Runs automatically once configured
- **Cost Monitoring**: Built-in awareness of quota usage
- **Flexible Configuration**: JSON-based mailbox configuration
- **Easy Scaling**: Add/remove mailboxes by editing config
- **HTTP Endpoint**: Manual trigger available for testing

## 📊 Google Cloud Free Tier Limits & Usage

### Free Tier Limits (Monthly)

| Service | Free Tier Limit | Notes |
|---------|----------------|-------|
| **Cloud Functions** | | |
| Invocations | 2,000,000 | Number of times function runs |
| Compute Time (GB-seconds) | 400,000 | Memory × execution time |
| Compute Time (GHz-seconds) | 200,000 | CPU × execution time |
| Outbound Data | 5 GB | Network egress |
| **Firestore** | | |
| Stored Data | 1 GB | Document storage |
| Document Reads | 50,000/day | Read operations |
| Document Writes | 20,000/day | Write/update operations |
| Document Deletes | 20,000/day | Delete operations |
| **Cloud Scheduler** | | |
| Jobs | 3 free jobs | Scheduled triggers |

### Usage Scenarios & Headroom

#### Scenario 1: Single Mailbox
**Configuration:** 1 mailbox, 15-minute sync, ~50 emails/day

| Resource | Usage | Limit | Headroom | % Used |
|----------|-------|-------|----------|--------|
| Invocations | 2,880/mo | 2,000,000 | 1,997,120 | **0.14%** |
| GB-seconds | ~960/mo | 400,000 | 399,040 | **0.24%** |
| Firestore Reads | 500/day | 50,000 | 49,500 | **1%** |
| Firestore Writes | 200/day | 20,000 | 19,800 | **1%** |

**Verdict:** ✅ Massive headroom - could run 600+ single mailboxes

---

#### Scenario 2: Three Mailboxes (Typical)
**Configuration:** 3 mailboxes, 15-minute sync, ~50 emails/day each

| Resource | Usage | Limit | Headroom | % Used |
|----------|-------|-------|----------|--------|
| Invocations | 2,880/mo | 2,000,000 | 1,997,120 | **0.14%** |
| GB-seconds | ~2,880/mo | 400,000 | 397,120 | **0.72%** |
| Firestore Reads | 1,500/day | 50,000 | 48,500 | **3%** |
| Firestore Writes | 600/day | 20,000 | 19,400 | **3%** |

**Verdict:** ✅ Excellent headroom - could add 47+ more mailboxes

---

#### Scenario 3: Five Mailboxes (Heavy Usage)
**Configuration:** 5 mailboxes, 15-minute sync, ~100 emails/day each

| Resource | Usage | Limit | Headroom | % Used |
|----------|-------|-------|----------|--------|
| Invocations | 2,880/mo | 2,000,000 | 1,997,120 | **0.14%** |
| GB-seconds | ~4,800/mo | 400,000 | 395,200 | **1.2%** |
| Firestore Reads | 2,500/day | 50,000 | 47,500 | **5%** |
| Firestore Writes | 1,000/day | 20,000 | 19,000 | **5%** |

**Verdict:** ✅ Great headroom - could handle 20+ mailboxes easily

---

#### Scenario 4: Ten Mailboxes (Enterprise)
**Configuration:** 10 mailboxes, 30-minute sync, ~100 emails/day each

| Resource | Usage | Limit | Headroom | % Used |
|----------|-------|-------|----------|--------|
| Invocations | 1,440/mo | 2,000,000 | 1,998,560 | **0.07%** |
| GB-seconds | ~7,200/mo | 400,000 | 392,800 | **1.8%** |
| Firestore Reads | 5,000/day | 50,000 | 45,000 | **10%** |
| Firestore Writes | 2,000/day | 20,000 | 18,000 | **10%** |

**Verdict:** ✅ Still comfortable - 90% headroom remaining

---

#### Scenario 5: Twenty Mailboxes (Maximum Practical)
**Configuration:** 20 mailboxes, 30-minute sync, ~50 emails/day each

| Resource | Usage | Limit | Headroom | % Used |
|----------|-------|-------|----------|--------|
| Invocations | 1,440/mo | 2,000,000 | 1,998,560 | **0.07%** |
| GB-seconds | ~14,400/mo | 400,000 | 385,600 | **3.6%** |
| Firestore Reads | 8,000/day | 50,000 | 42,000 | **16%** |
| Firestore Writes | 3,200/day | 20,000 | 16,800 | **16%** |

**Verdict:** ✅ Well within limits - 84% headroom remaining

---

### Key Insights

**Why Multi-Mailbox is So Efficient:**
- ✅ **Same invocation count** regardless of mailbox count (one function run processes all)
- ✅ **Linear scaling** of execution time, not invocations
- ✅ **Shared connections** to Gmail API
- ✅ **Batch cleanup** operations across all mailboxes

**Invocation Bottleneck:**
- Single mailbox uses 0.14% of invocation quota
- Could theoretically run **600+ mailboxes** before hitting invocation limits
- Real limit is execution time (540s timeout) at ~15-20 mailboxes per function

**Firestore Bottleneck:**
- Most generous free tier resource
- At 20 mailboxes, still 84% headroom
- Would need 100+ active mailboxes with high email volume to approach limits

**Practical Limits:**
- **1-10 mailboxes**: Single function, 15-minute sync - *effortless*
- **11-20 mailboxes**: Single function, 30-minute sync - *comfortable*
- **21-40 mailboxes**: Two functions (split mailboxes) - *still free*
- **40+ mailboxes**: Consider batch processing optimizations

## 🚀 Quick Start

### Prerequisites
- Google Cloud account with billing enabled (free tier)
   - see __Examples__ for more details
- Siteground (or any IMAP) email account(s)
- Gmail account to sync to

### Installation

1. **Create Your own infrastructure repo**
   ```bash
   git clone https://github.com/strachg/gmail-imap-sync.git
   cd gmail-imap-sync

   mkdir gmail-imap-sync-infra
   cd gmail-imap-sync-infra
   git init gmail-imap-sync-infra
   cp -r ../gmail-imap-sync/examples/infra .
   ```

2. **Set up Google Cloud APIs**

   This step requires the billing to be configured on your google cloud account. I also suggest putting cost alerts just in case you do start getting charged. Bill shock is never fun.

   ```bash
   gcloud config set project YOUR_PROJECT_ID
   gcloud services enable cloudfunctions.googleapis.com
   gcloud services enable cloudscheduler.googleapis.com
   gcloud services enable firestore.googleapis.com
   gcloud services enable gmail.googleapis.com
   ```

3. **Create Firestore database**
   ```bash
   gcloud firestore databases create --location=us-central1
   ```

4. **Get Gmail API credentials**
   - See detailed instructions in [SETUP.md](SETUP.md)
   - Run `python get_gmail_token.py` to generate OAuth token

5. **Configure mailboxes**
   ```bash
   cp .env.yaml.example .env.yaml
   # Edit .env.yaml with your credentials
   ```

6. **Deploy**
   ```bash
   chmod +x deployment-script.sh
   ./deployment-script.sh
   ```

### Configuration Example

```yaml
# .env.yaml
GMAIL_CREDENTIALS: '{"token": "...", "refresh_token": "...", ...}'

MAILBOXES_CONFIG: |
  [
    {
      "id": "personal",
      "host": "mail.yourdomain.com",
      "port": 993,
      "user": "personal@yourdomain.com",
      "password": "your-password",
      "gmail_label": "Imported/Personal"
    },
    {
      "id": "work",
      "host": "mail.yourdomain.com",
      "port": 993,
      "user": "work@yourdomain.com",
      "password": "your-password",
      "gmail_label": "Imported/Work"
    }
  ]
```

## 📖 How It Works

### 1. Sync Phase (Every 15 minutes)
```
IMAP Server → Cloud Function → Gmail API
     ↓              ↓              ↓
  Fetch 50    Track UIDs     Import emails
  messages    in Firestore   with labels
```

### 2. Deletion Check Phase
```
Firestore → Check Gmail → Delete from IMAP
    ↓           ↓              ↓
Find undeleted  Is in trash?  Mark deleted
messages        Yes → Delete  in Firestore
```

### 3. Cleanup Phase (Every 30 days)
```
Firestore → Find old records → Delete
    ↓
Messages deleted >30 days ago
```

## 🔍 Monitoring

### View logs
```bash
gcloud functions logs read gmail-sync --gen2 --region=us-central1 --limit=50
```

### Check quota usage
```bash
gcloud monitoring time-series list \
  --filter='metric.type="cloudfunctions.googleapis.com/function/execution_count"'
```

### Manual trigger
```bash
gcloud functions call gmail-sync --gen2 --region=us-central1
```

Or visit the function URL in your browser.

## 🛡️ Security

- **Never commit `.env.yaml`** - contains passwords
- OAuth tokens stored securely in environment variables
- Consider using Secret Manager for production
- IMAP connections use SSL/TLS (port 993)
- Cloud Function can be restricted to authenticated access

## 🔧 Customization

### Adjust sync frequency
```bash
# Change schedule in deployment-script.sh
# Every 30 minutes instead of 15:
--schedule="*/30 * * * *"
```

### Adjust message batch size
```python
# In main.py, change limit parameter:
new_messages = self.fetch_new_messages(limit=100)
```

### Adjust cleanup period
```python
# In main.py, change days parameter:
cleanup_old_records(days=60)
```

## 📈 Scaling Beyond Free Tier

If you exceed free tier limits:

| Emails/Day | Mailboxes | Strategy | Est. Cost |
|------------|-----------|----------|-----------|
| 500 | 5 | 30-min sync | $0.00 |
| 1,000 | 10 | 30-min sync | $0.00 |
| 5,000 | 20 | Split into 2 functions | $0.00 |
| 10,000 | 40 | Split into 4 functions | ~$1-2/mo |
| 50,000+ | 100+ | Use paid tier + optimize | ~$5-10/mo |

**Note:** Even with 100 mailboxes, costs remain minimal (~$5-10/month).

## 🐛 Troubleshooting

### "Failed to connect to IMAP"
- Verify IMAP credentials in `.env.yaml`
- Check if host requires app-specific password
- Ensure port 993 is accessible

### "Failed to connect to Gmail API"
- Re-run `get_gmail_token.py` to refresh OAuth token
- Verify Gmail API is enabled in Cloud Console
- Check GMAIL_CREDENTIALS format in `.env.yaml`

### Messages not deleting from source
- Verify emails are in Gmail trash (not just archived)
- Check Cloud Function logs for deletion errors
- Ensure IMAP account has delete permissions

### Approaching quota limits
- Increase sync interval (15min → 30min)
- Reduce message batch size (50 → 30)
- Split mailboxes into multiple functions

## 📝 License

MIT License - See [LICENSE](LICENSE) file

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 💡 Acknowledgments

- Inspired by [gmail-importer3](https://github.com/kyokuheki/gmail-importer3)
- Built for the Google Cloud free tier community

## 📞 Support

- **Issues**: Open a GitHub issue
- **Discussions**: Use GitHub Discussions
- **Documentation**: See [docs/](docs/) folder

---

**⚡ Built to run forever on Google Cloud's free tier ⚡**