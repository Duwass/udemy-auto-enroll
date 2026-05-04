# 🎓 Udemy Auto-Enroll Tool

Automatically enroll in free Udemy courses extracted from Facebook posts. Features a smart queue system, auto-scanning, and auto-resume on network failure.

## ⚡ Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Login to accounts (one-time setup)

You need to log into both Udemy and Facebook for the tool to function properly:

```bash
# Login to Udemy (to enroll in courses)
python main.py login

# Login to Facebook (to scan links from closed groups/posts)
python main.py login-fb
```

The browser will open → Login to the respective account → Press Enter in the terminal. The session will be saved permanently.

### 3. Paste link and enroll (fastest method)

```bash
python main.py watch
```

The terminal will wait for you to paste a Facebook link. Just paste it → it automatically gets added to the queue:

```
📋 Paste link: https://www.facebook.com/share/p/abc123/
✓ Added: FB Coupons #1 (10/03/2026) (ID: 29)

📋 Paste link: run    ← type 'run' to execute queue
📋 Paste link: list   ← type 'list' to view queue
📋 Paste link: exit   ← type 'exit' to quit
```

Alternatively, double-click **`start.bat`** to enter paste mode immediately.

### 4. Queue Management

```bash
# Add link (auto-generates name based on date + sequence)
python main.py queue add "https://facebook.com/post1"

# Or add with a custom name
python main.py queue add "https://facebook.com/post2" --name "Excel Course 05/03"

# View the queue
python main.py queue list

# Run all pending links
python main.py queue run

# Run specific links by ID
python main.py queue run 1
python main.py queue run 1 2 5

# Retry failed links
python main.py queue run --retry

# View courses inside a link (after scanning)
python main.py queue courses 5

# View enrollment report
python main.py queue report --latest
```

When you run `queue run`, the tool automatically executes:
1. **Pre-flight Check**: Verifies that both Udemy and Facebook sessions are active.
2. **Phase 1 (Scan)**: Scans all pending Facebook links to extract Udemy course URLs (using the saved Facebook session).
3. **Phase 2 (Enroll)**: Automatically enrolls each course into your Udemy account.

> **Lost connection?** The tool automatically waits for the internet to restore and resumes from the failed course.

## 📋 Commands

| Command | Description |
|------|-------|
| `python main.py watch` | Interactive mode - paste links |
| `python main.py login` | Login to Udemy |
| `python main.py login-fb` | Login to Facebook |
| `python main.py enroll <URL>` | Enroll from a single post URL |
| `python main.py history` | View enrollment history |
| `python main.py status` | Check login statuses |
| `python main.py queue add <URL>` | Add link (auto-name) |
| `python main.py queue list` | View queue |
| `python main.py queue remove <ID>` | Remove link from queue |
| `python main.py queue run` | Run all pending links |
| `python main.py queue run <ID>` | Run specific links by ID |
| `python main.py queue run --retry` | Retry failed links |
| `python main.py queue courses <ID>` | View courses + statuses |
| `python main.py queue report` | View result report |
| `python main.py queue clear` | Clear the entire queue |

## 📁 Structure

```
├── main.py              # CLI entry point
├── config.py            # Configuration
├── start.bat            # Double-click to enter paste mode
├── requirements.txt     # Dependencies
├── data/
│   ├── history.db       # Enrollment history (SQLite)
│   ├── queue.json       # Queue links + courses
│   ├── reports/         # Enrollment reports (TXT)
│   ├── browser_data/    # Udemy session
│   └── fb_browser_data/ # Facebook session
└── modules/
    ├── facebook_scraper.py   # Scrape Facebook posts
    ├── udemy_parser.py       # Parse Udemy URLs
    ├── udemy_enroller.py     # Enroll in courses
    ├── history.py            # Save history
    ├── queue_manager.py      # Manage queue
    ├── report_generator.py   # Generate TXT reports
    └── network.py            # Handle connection loss/retry
```

## 💡 Tips

- **Permanent sessions**: Only need to log into Udemy and Facebook once (data stored separately).
- **No duplicates**: The tool automatically skips already enrolled courses.
- **Headless mode**: Set `HEADLESS = True` in `config.py` to run the browser in the background.
- **Queue**: Add multiple links, run once, and view the report later.
- **Network resilience**: Auto-pauses if the connection is lost, and resumes when back online.
- **queue courses**: View details of each course along with its status (✓ Free / ⚠ Enrolled / 💰 Paid / ✗ Error).

## ⚠️ Notes

- Coupons may expire; the tool will notify you if enrollment fails.
- If the network drops mid-process, the tool will automatically wait and retry.
