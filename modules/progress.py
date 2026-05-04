"""
Progress management for Udemy Auto-Enroll Tool
Saves and loads pending courses for resume functionality
"""
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console

console = Console()

# Progress file location
PROGRESS_FILE = Path(__file__).parent.parent / "progress.json"


def save_progress(udemy_links: list, source_url: str, processed_count: int = 0) -> bool:
    """
    Save current progress to file
    
    Args:
        udemy_links: List of Udemy course URLs to enroll
        source_url: Original Facebook post URL
        processed_count: Number of courses already processed
    
    Returns:
        True if saved successfully
    """
    try:
        data = {
            "source_url": source_url,
            "udemy_links": udemy_links,
            "processed_count": processed_count,
            "total_count": len(udemy_links),
            "saved_at": datetime.now().isoformat(),
        }
        
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        console.print(f"[red]Lỗi lưu progress: {e}[/red]")
        return False


def load_progress() -> dict | None:
    """
    Load saved progress from file
    
    Returns:
        Progress data dict or None if not found
    """
    try:
        if not PROGRESS_FILE.exists():
            return None
        
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        console.print(f"[red]Lỗi đọc progress: {e}[/red]")
        return None


def has_pending_progress() -> bool:
    """Check if there's saved progress to resume"""
    progress = load_progress()
    if not progress:
        return False
    
    processed = progress.get("processed_count", 0)
    total = progress.get("total_count", 0)
    
    return processed < total


def get_remaining_links() -> list:
    """Get list of unprocessed links from saved progress"""
    progress = load_progress()
    if not progress:
        return []
    
    all_links = progress.get("udemy_links", [])
    processed = progress.get("processed_count", 0)
    
    return all_links[processed:]


def update_processed_count(count: int) -> bool:
    """Update the number of processed courses"""
    progress = load_progress()
    if not progress:
        return False
    
    progress["processed_count"] = count
    progress["updated_at"] = datetime.now().isoformat()
    
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False


def clear_progress() -> bool:
    """Clear saved progress after completion"""
    try:
        if PROGRESS_FILE.exists():
            PROGRESS_FILE.unlink()
        return True
    except:
        return False


def get_progress_info() -> dict | None:
    """Get progress info for display"""
    progress = load_progress()
    if not progress:
        return None
    
    return {
        "source_url": progress.get("source_url", "Unknown"),
        "processed": progress.get("processed_count", 0),
        "total": progress.get("total_count", 0),
        "remaining": progress.get("total_count", 0) - progress.get("processed_count", 0),
        "saved_at": progress.get("saved_at", "Unknown"),
    }
