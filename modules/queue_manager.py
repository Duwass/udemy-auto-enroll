"""
Queue management module for batch enrollment
Stores queue items in a JSON file
"""
import json
from datetime import datetime
from typing import Optional
from config import QUEUE_FILE


def _load_queue() -> dict:
    """Load queue data from file"""
    if not QUEUE_FILE.exists():
        return {"items": [], "next_id": 1}
    try:
        with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {"items": [], "next_id": 1}


def _save_queue(data: dict) -> bool:
    """Save queue data to file"""
    try:
        with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _normalize_url(url: str) -> str:
    """Normalize URL for comparison (strip trailing slash, query params order)"""
    return url.strip().rstrip('/')


def add_item(url: str, name: str) -> Optional[dict]:
    """Add a new item to the queue. Returns None if URL already exists."""
    data = _load_queue()

    # Check for duplicate URL
    normalized = _normalize_url(url)
    for existing in data["items"]:
        if _normalize_url(existing["url"]) == normalized:
            return None  # Duplicate

    item = {
        "id": data["next_id"],
        "name": name,
        "url": url,
        "status": "pending",
        "added_at": datetime.now().isoformat(),
    }
    data["items"].append(item)
    data["next_id"] += 1
    _save_queue(data)
    return item


def list_items(status_filter: Optional[str] = None) -> list[dict]:
    """List all items in the queue, optionally filtered by status"""
    data = _load_queue()
    items = data["items"]
    if status_filter:
        items = [i for i in items if i["status"] == status_filter]
    return items


def remove_item(item_id: int) -> bool:
    """Remove an item from the queue by ID"""
    data = _load_queue()
    original_len = len(data["items"])
    data["items"] = [i for i in data["items"] if i["id"] != item_id]
    if len(data["items"]) < original_len:
        _save_queue(data)
        return True
    return False


def update_item_status(item_id: int, status: str, extra: Optional[dict] = None) -> bool:
    """Update the status of a queue item"""
    data = _load_queue()
    for item in data["items"]:
        if item["id"] == item_id:
            item["status"] = status
            item["updated_at"] = datetime.now().isoformat()
            if extra:
                item.update(extra)
            _save_queue(data)
            return True
    return False


def get_pending_items() -> list[dict]:
    """Get all pending items in order"""
    return list_items(status_filter="pending")


def clear_queue() -> bool:
    """Clear all items from the queue"""
    return _save_queue({"items": [], "next_id": 1})


def get_item_by_id(item_id: int) -> Optional[dict]:
    """Get a specific item by ID"""
    data = _load_queue()
    for item in data["items"]:
        if item["id"] == item_id:
            return item
    return None


def get_items_by_ids(item_ids: list[int]) -> list[dict]:
    """Get multiple items by their IDs, preserving order"""
    data = _load_queue()
    id_set = set(item_ids)
    items = [i for i in data["items"] if i["id"] in id_set]
    # Sort by requested order
    id_order = {id_: idx for idx, id_ in enumerate(item_ids)}
    items.sort(key=lambda i: id_order.get(i["id"], 0))
    return items


def get_error_items() -> list[dict]:
    """Get all items with error status"""
    return list_items(status_filter="error")


def reset_running_items() -> int:
    """Reset any 'running' items back to 'pending' (interrupted runs).
    Returns the number of items reset."""
    data = _load_queue()
    count = 0
    for item in data["items"]:
        if item["status"] == "running":
            item["status"] = "pending"
            item["updated_at"] = datetime.now().isoformat()
            count += 1
    if count > 0:
        _save_queue(data)
    return count


def update_item_courses(item_id: int, courses: list[dict]) -> bool:
    """Save scraped course list for a queue item"""
    data = _load_queue()
    for item in data["items"]:
        if item["id"] == item_id:
            item["courses"] = courses
            item["scanned_at"] = datetime.now().isoformat()
            _save_queue(data)
            return True
    return False
