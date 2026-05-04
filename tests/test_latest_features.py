"""
Test script for latest features:
- Auto-detect Facebook URL (sys.argv pre-check)
- Auto-naming (date + sequential number)
- queue add --name optional
- queue courses status columns
- Watch mode (import test only)
- start.bat existence
"""
import sys
import os
import json
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = 0
failed = 0
total = 0


def test(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  \u2705 #{total} {name}")
    else:
        failed += 1
        print(f"  \u274c #{total} {name}")
        if detail:
            print(f"     \u2192 {detail}")


CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(*args):
    """Run main.py with args and return output"""
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    result = subprocess.run(
        [sys.executable, 'main.py'] + list(args),
        capture_output=True, cwd=CWD, timeout=10,
        env=env
    )
    stdout = result.stdout.decode('utf-8', errors='replace')
    stderr = result.stderr.decode('utf-8', errors='replace')
    return stdout + stderr, result.returncode


# ============================================================
# GROUP A: Auto-detect Facebook URL
# ============================================================
print("\n\U0001f9ea Group A: Auto-detect Facebook URL")
print("=" * 50)

# Test 1: Facebook URL auto-adds to queue
out, code = run_cli("https://www.facebook.com/share/p/autotest1/")
test("Facebook URL auto-detected and added",
     "Auto-added" in out or "\u0110\u00e3 th\u00eam" in out or "queue" in out.lower(),
     f"Output: {out[:100]}")

# Test 2: Another Facebook URL with fb.com
out2, code2 = run_cli("https://fb.com/post/autotest2")
test("fb.com URL also auto-detected",
     "Auto-added" in out2 or "\u0110\u00e3 th\u00eam" in out2,
     f"Output: {out2[:100]}")

# Test 3: Non-Facebook URL falls through to CLI help
out3, code3 = run_cli("https://google.com/something")
test("Non-Facebook URL shows help (not auto-add)",
     "Auto-added" not in out3 and "\u0110\u00e3 th\u00eam" not in out3,
     f"Output: {out3[:100]}")

# Test 4: No args shows help
out4, code4 = run_cli()
test("No args shows help menu",
     "Usage" in out4 or "queue" in out4.lower(),
     f"Output: {out4[:100]}")


# ============================================================
# GROUP B: Auto-naming with date + sequential number
# ============================================================
print("\n\U0001f9ea Group B: Auto-naming logic")
print("=" * 50)

from modules.queue_manager import list_items, get_item_by_id

today_prefix = datetime.now().strftime('%Y-%m-%d')
today_display = datetime.now().strftime('%d/%m/%Y')

# Find items added today by the auto-detect tests
all_items = list_items()
today_items = [i for i in all_items if i.get('added_at', '').startswith(today_prefix)]

test("Auto-detect created items for today",
     len(today_items) >= 2,
     f"Found {len(today_items)} items for today")

# Check naming format
fb_coupons_items = [i for i in today_items if 'FB Coupons' in i.get('name', '')]
test("Items named 'FB Coupons #N (date)'",
     len(fb_coupons_items) >= 2,
     f"Found {len(fb_coupons_items)} FB Coupons items")

# Check sequential numbering
if len(fb_coupons_items) >= 2:
    names = [i['name'] for i in fb_coupons_items]
    test("Names contain today's date",
         any(today_display in n for n in names),
         f"Names: {names[:3]}")

    # Check numbers are sequential
    import re
    numbers = []
    for n in names:
        match = re.search(r'#(\d+)', n)
        if match:
            numbers.append(int(match.group(1)))
    test("Sequential numbering works",
         len(numbers) >= 2 and numbers == sorted(numbers),
         f"Numbers found: {numbers}")
else:
    test("Names contain today's date", False, "Not enough items")
    test("Sequential numbering works", False, "Not enough items")


# ============================================================
# GROUP C: queue add --name optional
# ============================================================
print("\n\U0001f9ea Group C: queue add --name optional")
print("=" * 50)

# Test without --name
out5, code5 = run_cli("queue", "add", "https://facebook.com/test-no-name")
test("queue add without --name succeeds",
     code5 == 0 and ("\u0110\u00e3 th\u00eam" in out5 or "queue" in out5.lower()),
     f"Output: {out5[:100]}")

# Test with --name
out6, code6 = run_cli("queue", "add", "https://facebook.com/test-with-name", "-n", "Custom Name")
test("queue add with --name 'Custom Name' succeeds",
     code6 == 0 and "Custom Name" in out6,
     f"Output: {out6[:100]}")


# ============================================================
# GROUP D: queue courses status display
# ============================================================
print("\n\U0001f9ea Group D: queue courses status columns")
print("=" * 50)

from modules.queue_manager import update_item_courses

# Find a test item and add mock courses with statuses
test_items = list_items()
if test_items:
    test_id = test_items[0]['id']

    mock_courses = [
        {"url": "https://udemy.com/course/free-ok/", "slug": "free-ok",
         "status": "success", "message": "Enrolled successfully"},
        {"url": "https://udemy.com/course/already/", "slug": "already",
         "status": "already_enrolled", "message": "\u0110\u00e3 \u0111\u0103ng k\u00fd tr\u01b0\u1edbc \u0111\u00f3"},
        {"url": "https://udemy.com/course/paid/", "slug": "paid",
         "status": "skipped", "message": "Kh\u00f3a m\u1ea5t ph\u00ed"},
        {"url": "https://udemy.com/course/broken/", "slug": "broken",
         "status": "error", "message": "Coupon h\u1ebft h\u1ea1n"},
        {"url": "https://udemy.com/course/pending/", "slug": "pending-course",
         "status": "pending", "message": ""},
    ]
    update_item_courses(test_id, mock_courses)

    # Run queue courses command
    out7, _ = run_cli("queue", "courses", str(test_id))

    test("queue courses shows Status column",
         "Status" in out7,
         f"Output snippet: {out7[:200]}")

    test("queue courses shows free (success) status",
         "Mi\u1ec5n ph\u00ed" in out7 or "success" in out7.lower(),
         f"Looking for 'Mi\u1ec5n ph\u00ed' in output")

    test("queue courses shows paid (skipped) status",
         "M\u1ea5t ph\u00ed" in out7 or "skipped" in out7.lower(),
         f"Looking for 'M\u1ea5t ph\u00ed' in output")

    test("queue courses shows already enrolled status",
         "\u0110\u00e3 \u0111\u0103ng k\u00fd" in out7 or "already" in out7.lower(),
         f"Looking for '\u0110\u00e3 \u0111\u0103ng k\u00fd' in output")

    test("queue courses shows error status",
         "L\u1ed7i" in out7 or "error" in out7.lower(),
         f"Looking for 'L\u1ed7i' in output")

    test("queue courses shows Message column",
         "Message" in out7,
         f"Output snippet: {out7[:200]}")

    # Cleanup mock courses
    update_item_courses(test_id, [])
else:
    for _ in range(6):
        test("queue courses test", False, "No items in queue")


# ============================================================
# GROUP E: Watch mode & start.bat
# ============================================================
print("\n\U0001f9ea Group E: Watch mode & start.bat")
print("=" * 50)

# Test watch command exists in help
out8, _ = run_cli("--help")
test("watch command listed in --help",
     "watch" in out8.lower(),
     f"Output: {out8[:200]}")

# Test watch --help
out9, code9 = run_cli("watch", "--help")
test("watch --help works",
     code9 == 0 and ("t\u01b0\u01a1ng t\u00e1c" in out9.lower() or "paste" in out9.lower()),
     f"Output: {out9[:100]}")

# Test start.bat exists
start_bat = os.path.join(CWD, 'start.bat')
test("start.bat file exists",
     os.path.isfile(start_bat))

# Test start.bat content
if os.path.isfile(start_bat):
    content = open(start_bat, 'r').read()
    test("start.bat contains 'python main.py watch'",
         "python main.py watch" in content)
else:
    test("start.bat contains correct command", False, "File not found")


# ============================================================
# GROUP F: CLI subcommands still work
# ============================================================
print("\n\U0001f9ea Group F: Existing CLI commands not broken")
print("=" * 50)

out_login, code_login = run_cli("login", "--help")
test("login --help works", code_login == 0 and ("Options" in out_login or "help" in out_login.lower()))

out_enroll, code_enroll = run_cli("enroll", "--help")
test("enroll --help works", code_enroll == 0 and ("Options" in out_enroll or "POST_URL" in out_enroll))

out_queue, code_queue = run_cli("queue", "--help")
test("queue --help works", code_queue == 0 and ("Options" in out_queue or "Commands" in out_queue))

out_list, code_list = run_cli("queue", "list")
test("queue list works", code_list == 0)

out_run_help, code_run = run_cli("queue", "run", "--help")
test("queue run --help works", code_run == 0 and "retry" in out_run_help.lower())


# ============================================================
# CLEANUP: Remove test items
# ============================================================
print("\n\U0001f527 Cleanup: Removing test items")
print("=" * 50)

all_items = list_items()
test_urls = [
    "https://www.facebook.com/share/p/autotest1/",
    "https://fb.com/post/autotest2",
    "https://facebook.com/test-no-name",
    "https://facebook.com/test-with-name",
    "https://www.facebook.com/share/p/test999/",
]
removed = 0
for item in all_items:
    if item['url'] in test_urls:
        from modules.queue_manager import remove_item
        remove_item(item['id'])
        removed += 1

print(f"  \U0001f9f9 Removed {removed} test items")


# ============================================================
# SUMMARY
# ============================================================
print(f"\n{'=' * 50}")
print(f"\U0001f4ca Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("\U0001f389 All tests passed!")
else:
    print(f"\u26a0\ufe0f  {failed} test(s) failed")
    sys.exit(1)
