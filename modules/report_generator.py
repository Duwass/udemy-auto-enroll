"""
Report generator for queue enrollment results
Outputs human-readable TXT report files
"""
from datetime import datetime
from pathlib import Path
from config import REPORTS_DIR


def get_report_path() -> Path:
    """Generate report file path with current timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    return REPORTS_DIR / f"queue_{timestamp}.txt"


def create_report(queue_results: list[dict], start_time: datetime, end_time: datetime) -> Path:
    """
    Create a TXT report file from queue run results

    Args:
        queue_results: List of dicts, each containing:
            - item: queue item dict (id, name, url, status)
            - courses_found: int
            - results: list of enrollment result dicts
            - error: optional error message
        start_time: when the queue run started
        end_time: when the queue run finished

    Returns:
        Path to the generated report file
    """
    report_path = get_report_path()
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("        UDEMY AUTO-ENROLL QUEUE REPORT")
    lines.append(f"        {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")

    total_success = 0
    total_skipped = 0
    total_failed = 0
    total_courses = 0

    # Each link section
    for idx, qr in enumerate(queue_results, 1):
        item = qr["item"]
        results = qr.get("results", [])
        error = qr.get("error")
        courses_found = qr.get("courses_found", 0)

        success = sum(1 for r in results if r.get("status") in ("success", "already_enrolled"))
        skipped = sum(1 for r in results if r.get("status") == "skipped")
        failed = len(results) - success - skipped

        total_success += success
        total_skipped += skipped
        total_failed += failed
        total_courses += courses_found

        status_label = "✅ HOÀN THÀNH" if not error else "❌ LỖI"

        lines.append(f"📋 LINK {idx}: {item['name']}")
        lines.append(f"   URL: {item['url']}")
        lines.append(f"   Trạng thái: {status_label}")

        if error:
            lines.append(f"   Lỗi: {error}")
        else:
            lines.append(
                f"   Tổng khóa: {courses_found} | "
                f"✓ Thành công: {success} | "
                f"⚠ Đã có/Bỏ qua: {skipped} | "
                f"✗ Lỗi: {failed}"
            )

            if results:
                lines.append("   " + "-" * 40)
                for r in results:
                    name = r.get("course_name") or r.get("url", "Unknown")
                    if len(name) > 50:
                        name = name[:47] + "..."
                    st = r.get("status", "unknown")
                    if st in ("success", "already_enrolled"):
                        icon = "✓"
                    elif st == "skipped":
                        icon = "⚠"
                    else:
                        icon = "✗"
                    msg = r.get("message", "")
                    detail = f" ({msg})" if msg and st not in ("success",) else ""
                    lines.append(f"   {icon} {name}{detail}")

        lines.append("")

    # Summary
    duration = end_time - start_time
    minutes = int(duration.total_seconds() // 60)
    seconds = int(duration.total_seconds() % 60)

    lines.append("=" * 60)
    lines.append("📊 TỔNG KẾT:")
    lines.append(f"   Links đã xử lý: {len(queue_results)}")
    lines.append(
        f"   Tổng khóa: {total_courses} | "
        f"✓ {total_success} | "
        f"⚠ {total_skipped} | "
        f"✗ {total_failed}"
    )
    lines.append(f"   Thời gian: {minutes} phút {seconds} giây")
    lines.append("=" * 60)

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def list_reports() -> list[Path]:
    """List all report files, newest first"""
    if not REPORTS_DIR.exists():
        return []
    reports = sorted(REPORTS_DIR.glob("queue_*.txt"), reverse=True)
    return reports


def get_latest_report() -> Path | None:
    """Get the most recent report file"""
    reports = list_reports()
    return reports[0] if reports else None
