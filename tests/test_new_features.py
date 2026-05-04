"""
Test script for new features:
- Feature 1: Auto Scan + Queue Courses
- Feature 2: Network Resilience
"""
import sys
import json
import os

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

passed = 0
failed = 0
total = 0


def test(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  ✅ #{total} {name}")
    else:
        failed += 1
        print(f"  ❌ #{total} {name}")
        if detail:
            print(f"     → {detail}")


# ============================================================
# GROUP A: queue_manager tests
# ============================================================
print("\n🧪 Group A: queue_manager functions")
print("=" * 50)

from modules.queue_manager import (
    get_item_by_id, get_items_by_ids, get_error_items,
    update_item_courses, list_items
)

# Test #1: get_item_by_id - existing
item = get_item_by_id(1)
test("get_item_by_id(1) returns item", item is not None and item['id'] == 1)

# Test #2: get_item_by_id - non-existing
item_999 = get_item_by_id(999)
test("get_item_by_id(999) returns None", item_999 is None)

# Test #3: get_items_by_ids - multiple
items = get_items_by_ids([1, 2, 3])
test("get_items_by_ids([1,2,3]) returns 3 items",
     len(items) == 3 and items[0]['id'] == 1)

# Test #4: get_items_by_ids - preserves order
items_rev = get_items_by_ids([3, 1, 2])
test("get_items_by_ids preserves order",
     items_rev[0]['id'] == 3 and items_rev[1]['id'] == 1)

# Test #5: get_error_items
error_items = get_error_items()
test("get_error_items returns error status items",
     all(i['status'] == 'error' for i in error_items))

# Test #6: Item without courses
item1 = get_item_by_id(1)
has_courses = 'courses' in item1 and item1['courses']
test("Old items don't have courses (pre-scan)",
     not has_courses,
     f"courses={item1.get('courses', 'NONE')}")

# ============================================================
# GROUP D: Network module tests
# ============================================================
print("\n🧪 Group D: Network module functions")
print("=" * 50)

from modules.network import check_internet, is_network_error, NETWORK_ERRORS

# Test #13: check_internet (should be True right now)
has_internet = check_internet()
test("check_internet() returns True (online)", has_internet)

# Test: is_network_error with network errors
test("is_network_error detects ERR_INTERNET_DISCONNECTED",
     is_network_error(Exception("net::ERR_INTERNET_DISCONNECTED at https://...")))

test("is_network_error detects ERR_CONNECTION_RESET",
     is_network_error(Exception("net::ERR_CONNECTION_RESET")))

test("is_network_error detects ERR_TIMED_OUT",
     is_network_error(Exception("net::ERR_TIMED_OUT")))

test("is_network_error detects ERR_NAME_NOT_RESOLVED",
     is_network_error(Exception("ERR_NAME_NOT_RESOLVED")))

# Test: is_network_error with non-network errors
test("is_network_error returns False for normal errors",
     not is_network_error(Exception("Button not found")))

test("is_network_error returns False for timeout",
     not is_network_error(Exception("Timeout 30000ms exceeded")))

test("is_network_error returns False for empty error",
     not is_network_error(Exception("")))

# Test: NETWORK_ERRORS list
test("NETWORK_ERRORS has correct entries",
     'ERR_INTERNET_DISCONNECTED' in NETWORK_ERRORS and
     'ERR_CONNECTION_RESET' in NETWORK_ERRORS)

# ============================================================
# GROUP E: safe_goto import test
# ============================================================
print("\n🧪 Group E: safe_goto import validation")
print("=" * 50)

from modules.network import safe_goto, wait_for_internet
import inspect

# Test function signatures
sig_safe = inspect.signature(safe_goto)
test("safe_goto has correct params (page, url, timeout, max_retries)",
     list(sig_safe.parameters.keys()) == ['page', 'url', 'timeout', 'max_retries'])

sig_wait = inspect.signature(wait_for_internet)
test("wait_for_internet has correct params",
     'check_interval' in sig_wait.parameters and 'max_wait' in sig_wait.parameters)

# ============================================================
# GROUP F: Enroller integration check
# ============================================================
print("\n🧪 Group F: Enroller network integration")
print("=" * 50)

import modules.udemy_enroller as enroller
import modules.facebook_scraper as scraper

# Verify imports exist
test("udemy_enroller imports wait_for_internet",
     hasattr(enroller, 'wait_for_internet'))

test("udemy_enroller imports safe_goto",
     hasattr(enroller, 'safe_goto'))

test("udemy_enroller imports is_network_error",
     hasattr(enroller, 'is_network_error'))

test("facebook_scraper imports safe_goto",
     hasattr(scraper, 'safe_goto'))

test("facebook_scraper imports wait_for_internet",
     hasattr(scraper, 'wait_for_internet'))

# ============================================================
# GROUP G: update_item_courses function
# ============================================================
print("\n🧪 Group G: update_item_courses")
print("=" * 50)

# Test update_item_courses (on a test basis, read-only check)
from config import QUEUE_FILE

# Read current queue
with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
    queue_data = json.load(f)

# Find an item to test
test_item = queue_data['items'][0] if queue_data['items'] else None
test("Queue has items to test", test_item is not None)

if test_item:
    # Test saving courses
    test_courses = [
        {"url": "https://udemy.com/course/test-1/?couponCode=TEST", "slug": "test-1"},
        {"url": "https://udemy.com/course/test-2/?couponCode=TEST", "slug": "test-2"},
    ]
    item_id = test_item['id']
    result = update_item_courses(item_id, test_courses)
    test(f"update_item_courses(#{item_id}) returns True", result)

    # Verify saved
    updated = get_item_by_id(item_id)
    test(f"Courses saved correctly (2 courses)",
         len(updated.get('courses', [])) == 2)
    test(f"Course data has correct structure",
         updated['courses'][0]['slug'] == 'test-1' and
         updated['courses'][0]['url'].startswith('https://'))
    test(f"scanned_at timestamp saved",
         'scanned_at' in updated)

    # Clean up: remove test courses
    update_item_courses(item_id, [])
    cleaned = get_item_by_id(item_id)
    test(f"Cleanup: courses cleared", len(cleaned.get('courses', [])) == 0)


# ============================================================
# SUMMARY
# ============================================================
print(f"\n{'=' * 50}")
print(f"📊 Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("🎉 All tests passed!")
else:
    print(f"⚠️  {failed} test(s) failed")
    sys.exit(1)
