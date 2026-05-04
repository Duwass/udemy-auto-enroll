#!/usr/bin/env python3
"""
Udemy Auto-Enroll Tool
Automatically enroll in free Udemy courses from Facebook posts
"""
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group()
def cli():
    """🎓 Udemy Auto-Enroll Tool - Tự động đăng ký khóa học Udemy miễn phí"""
    pass


@cli.command()
def login():
    """Đăng nhập vào tài khoản Udemy (chỉ cần làm 1 lần)"""
    from modules.udemy_enroller import login_udemy, check_login_status
    
    console.print(Panel.fit(
        "[bold blue]🔐 Đăng nhập Udemy[/bold blue]\n"
        "Session sẽ được lưu lại, bạn chỉ cần đăng nhập 1 lần.",
        border_style="blue"
    ))
    
    # Check if already logged in
    console.print("[dim]Đang kiểm tra trạng thái đăng nhập...[/dim]")
    if check_login_status():
        console.print("[green]✓ Bạn đã đăng nhập Udemy rồi![/green]")
        if not click.confirm("Bạn có muốn đăng nhập lại không?", default=False):
            return
    
    login_udemy()


@cli.command('login-fb')
def login_fb():
    """Đăng nhập vào tài khoản Facebook (chỉ cần làm 1 lần)"""
    from modules.facebook_scraper import login_facebook, check_fb_login_status

    console.print(Panel.fit(
        "[bold blue]🔐 Đăng nhập Facebook[/bold blue]\n"
        "Session sẽ được lưu lại, bạn chỉ cần đăng nhập 1 lần.",
        border_style="blue"
    ))

    # Check if already logged in
    console.print("[dim]Đang kiểm tra trạng thái đăng nhập Facebook...[/dim]")
    if check_fb_login_status():
        console.print("[green]✓ Bạn đã đăng nhập Facebook rồi![/green]")
        if not click.confirm("Bạn có muốn đăng nhập lại không?", default=False):
            return

    login_facebook()


@cli.command()
@click.argument('post_url')
def enroll(post_url):
    """Đăng ký các khóa học từ bài viết (Facebook, website...)
    
    POST_URL: Link bài viết chứa các khóa học Udemy
    """
    from modules.facebook_scraper import scrape_facebook_post
    from modules.udemy_enroller import enroll_multiple_courses, check_login_status
    from modules.udemy_parser import parse_udemy_url
    
    console.print(Panel.fit(
        "[bold green]🎓 Udemy Auto-Enroll[/bold green]\n"
        f"Source: {post_url[:60]}...",
        border_style="green"
    ))
    
    # Check login status
    console.print("[dim]Đang kiểm tra trạng thái đăng nhập Udemy...[/dim]")
    if not check_login_status():
        console.print("[red]✗ Bạn chưa đăng nhập Udemy![/red]")
        console.print("Chạy lệnh: [bold]python main.py login[/bold] để đăng nhập")
        return
    
    console.print("[green]✓ Đã đăng nhập Udemy[/green]\n")
    
    # Scrape post for Udemy links
    console.print("[blue]📖 Đang đọc bài viết và tìm Udemy links...[/blue]")
    udemy_links = scrape_facebook_post(post_url)
    
    if not udemy_links:
        console.print("[yellow]Không tìm thấy link Udemy nào.[/yellow]")
        return
    
    # Show found courses
    console.print(f"\n[green]Tìm thấy {len(udemy_links)} khóa học:[/green]")
    for i, link in enumerate(udemy_links[:10], 1):
        course = parse_udemy_url(link)
        if course:
            console.print(f"  {i}. {course.slug[:50]}")
            if course.coupon_code:
                console.print(f"     [dim]Coupon: {course.coupon_code}[/dim]")
    
    if len(udemy_links) > 10:
        console.print(f"  ... và {len(udemy_links) - 10} khóa khác")
    
    # Confirm enrollment
    if not click.confirm(f"\nBạn có muốn đăng ký {len(udemy_links)} khóa học này không?", default=True):
        console.print("[yellow]Đã hủy.[/yellow]")
        return
    
    # Save progress before starting
    from modules.progress import save_progress, update_processed_count, clear_progress
    save_progress(udemy_links, post_url)
    console.print("[dim]💾 Đã lưu tiến trình. Dùng 'python main.py resume' để tiếp tục nếu dừng giữa chừng.[/dim]")
    
    # Enroll
    console.print("\n[blue]🚀 Bắt đầu đăng ký...[/blue]\n")
    results = enroll_multiple_courses(
        udemy_links, 
        source_url=post_url,
        progress_callback=lambda i: update_processed_count(i + 1)
    )
    
    # Summary
    console.print("\n")
    success_count = sum(1 for r in results if r.get('status') in ['success', 'already_enrolled'])
    skipped_count = sum(1 for r in results if r.get('status') == 'skipped')
    failed_count = len(results) - success_count - skipped_count
    
    summary = Table(title="📊 Kết quả")
    summary.add_column("Trạng thái", style="bold")
    summary.add_column("Số lượng", justify="right")
    
    summary.add_row("[green]✓ Thành công[/green]", str(success_count))
    summary.add_row("[yellow]⚠ Đã enrolled trước[/yellow]", str(skipped_count))
    summary.add_row("[red]✗ Thất bại[/red]", str(failed_count))
    
    console.print(summary)
    
    # Clear progress on completion
    clear_progress()
    console.print("[green]✓ Hoàn thành![/green]")


@cli.command()
@click.option('--limit', '-n', default=20, help='Số lượng khóa học hiển thị')
def history(limit):
    """Xem lịch sử các khóa học đã đăng ký"""
    from modules.history import get_history
    
    records = get_history(limit)
    
    if not records:
        console.print("[yellow]Chưa có lịch sử đăng ký nào.[/yellow]")
        return
    
    table = Table(title=f"📚 Lịch sử đăng ký (gần nhất: {len(records)} khóa)")
    table.add_column("Tên khóa học", style="cyan", max_width=40)
    table.add_column("Trạng thái", justify="center")
    table.add_column("Ngày đăng ký", style="dim")
    
    status_icons = {
        'success': '[green]✓[/green]',
        'already_enrolled': '[yellow]⚠[/yellow]',
        'skipped': '[dim]○[/dim]',
        'failed': '[red]✗[/red]',
        'coupon_expired': '[red]⏱[/red]',
        'error': '[red]![/red]'
    }
    
    for name, url, status, date in records:
        display_name = name if name else url.split('/')[-2] if url else 'Unknown'
        if len(display_name) > 40:
            display_name = display_name[:37] + '...'
        
        icon = status_icons.get(status, '[dim]?[/dim]')
        date_str = str(date)[:19] if date else ''
        
        table.add_row(display_name, icon, date_str)
    
    console.print(table)


@cli.command('clear-history')
def clear_history():
    """Xóa toàn bộ lịch sử enrollment"""
    from config import DB_PATH
    
    if not DB_PATH.exists():
        console.print("[yellow]Không có lịch sử nào để xóa.[/yellow]")
        return
    
    if not click.confirm("Bạn có chắc chắn muốn xóa TOÀN BỘ lịch sử enrollment?", default=False):
        console.print("[yellow]Đã hủy.[/yellow]")
        return
    
    try:
        DB_PATH.unlink()
        console.print("[green]✓ Đã xóa toàn bộ lịch sử enrollment![/green]")
    except Exception as e:
        console.print(f"[red]Lỗi: {e}[/red]")


@cli.command()
def status():
    """Kiểm tra trạng thái đăng nhập Udemy"""
    from modules.udemy_enroller import check_login_status
    from modules.progress import get_progress_info
    
    console.print("[dim]Đang kiểm tra...[/dim]")
    
    if check_login_status():
        console.print("[green]✓ Đã đăng nhập Udemy[/green]")
    else:
        console.print("[red]✗ Chưa đăng nhập Udemy[/red]")
        console.print("Chạy: [bold]python main.py login[/bold]")

    # Check Facebook login
    from modules.facebook_scraper import check_fb_login_status
    if check_fb_login_status():
        console.print("[green]✓ Đã đăng nhập Facebook[/green]")
    else:
        console.print("[red]✗ Chưa đăng nhập Facebook[/red]")
        console.print("Chạy: [bold]python main.py login-fb[/bold]")
    
    # Check for pending progress
    progress = get_progress_info()
    if progress:
        console.print(f"\n[yellow]📋 Có tiến trình chưa hoàn thành:[/yellow]")
        console.print(f"  - Đã xử lý: {progress['processed']}/{progress['total']} khóa")
        console.print(f"  - Còn lại: {progress['remaining']} khóa")
        console.print(f"  - Lưu lúc: {progress['saved_at'][:19]}")
        console.print("\nChạy: [bold]python main.py resume[/bold] để tiếp tục")


@cli.command()
def resume():
    """Tiếp tục đăng ký từ chỗ đã dừng"""
    from modules.udemy_enroller import enroll_multiple_courses, check_login_status
    from modules.udemy_parser import parse_udemy_url
    from modules.progress import (
        has_pending_progress, get_remaining_links, get_progress_info,
        update_processed_count, load_progress, clear_progress
    )
    
    # Check for saved progress
    if not has_pending_progress():
        console.print("[yellow]Không có tiến trình nào để tiếp tục.[/yellow]")
        console.print("Chạy: [bold]python main.py enroll <URL>[/bold] để bắt đầu mới")
        return
    
    # Show progress info
    progress = get_progress_info()
    console.print(Panel.fit(
        "[bold blue]🔄 Tiếp tục đăng ký[/bold blue]\n"
        f"Source: {progress['source_url'][:60]}...\n"
        f"Đã xử lý: {progress['processed']}/{progress['total']} | Còn lại: {progress['remaining']}",
        border_style="blue"
    ))
    
    # Check login status
    console.print("[dim]Đang kiểm tra trạng thái đăng nhập Udemy...[/dim]")
    if not check_login_status():
        console.print("[red]✗ Bạn chưa đăng nhập Udemy![/red]")
        console.print("Chạy lệnh: [bold]python main.py login[/bold] để đăng nhập")
        return
    
    console.print("[green]✓ Đã đăng nhập Udemy[/green]\n")
    
    # Get remaining links
    remaining_links = get_remaining_links()
    
    # Show remaining courses
    console.print(f"[green]Còn {len(remaining_links)} khóa học cần xử lý:[/green]")
    for i, link in enumerate(remaining_links[:5], 1):
        course = parse_udemy_url(link)
        if course:
            console.print(f"  {i}. {course.slug[:50]}")
    
    if len(remaining_links) > 5:
        console.print(f"  ... và {len(remaining_links) - 5} khóa khác")
    
    # Confirm resume
    if not click.confirm(f"\nTiếp tục đăng ký {len(remaining_links)} khóa còn lại?", default=True):
        console.print("[yellow]Đã hủy.[/yellow]")
        return
    
    # Enroll remaining courses
    console.print("\n[blue]🚀 Tiếp tục đăng ký...[/blue]\n")
    
    saved_progress = load_progress()
    source_url = saved_progress.get("source_url", "")
    start_index = saved_progress.get("processed_count", 0)
    
    results = enroll_multiple_courses(
        remaining_links, 
        source_url=source_url,
        progress_callback=lambda i: update_processed_count(start_index + i + 1)
    )
    
    # Summary
    console.print("\n")
    success_count = sum(1 for r in results if r.get('status') in ['success', 'already_enrolled'])
    skipped_count = sum(1 for r in results if r.get('status') == 'skipped')
    failed_count = len(results) - success_count - skipped_count
    
    summary = Table(title="📊 Kết quả")
    summary.add_column("Trạng thái", style="bold")
    summary.add_column("Số lượng", justify="right")
    
    summary.add_row("[green]✓ Thành công[/green]", str(success_count))
    summary.add_row("[yellow]⚠ Đã enrolled trước[/yellow]", str(skipped_count))
    summary.add_row("[red]✗ Thất bại[/red]", str(failed_count))
    
    console.print(summary)
    
    # Clear progress on completion
    clear_progress()
    console.print("[green]✓ Đã hoàn thành tất cả![/green]")


@cli.group()
def queue():
    """📋 Quản lý hàng đợi links để đăng ký hàng loạt"""
    pass


@queue.command('add')
@click.argument('url')
@click.option('--name', '-n', default=None, help='Tên để nhận biết link (tự động nếu bỏ trống)')
def queue_add(url, name):
    """Thêm link vào hàng đợi

    URL: Link bài viết chứa các khóa học Udemy
    """
    from datetime import datetime
    from modules.queue_manager import add_item, list_items

    # Auto-generate name if not provided
    if not name:
        today_str = datetime.now().strftime('%d/%m/%Y')
        all_items = list_items()
        today_count = sum(
            1 for i in all_items
            if i.get('added_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))
        )
        name = f"FB Coupons #{today_count + 1} ({today_str})"

    item = add_item(url, name)
    if item is None:
        console.print(f"[yellow]⚠ Link này đã có trong queue rồi![/yellow]")
        console.print(f"  URL: {url[:60]}...")
        return
    console.print(f"[green]✓ Đã thêm vào queue:[/green]")
    console.print(f"  ID: {item['id']}")
    console.print(f"  Tên: {item['name']}")
    console.print(f"  URL: {item['url'][:60]}...")


@queue.command('list')
def queue_list():
    """Xem danh sách links trong hàng đợi"""
    from modules.queue_manager import list_items

    items = list_items()
    if not items:
        console.print("[yellow]Hàng đợi trống. Dùng 'python main.py queue add' để thêm link.[/yellow]")
        return

    table = Table(title="📋 Hàng đợi")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Tên", style="cyan", max_width=30)
    table.add_column("URL", max_width=40)
    table.add_column("Trạng thái", justify="center")
    table.add_column("Thêm lúc", style="dim")

    status_icons = {
        'pending': '[yellow]⏳ Chờ[/yellow]',
        'running': '[blue]🔄 Đang chạy[/blue]',
        'done': '[green]✅ Xong[/green]',
        'error': '[red]❌ Lỗi[/red]',
    }

    for item in items:
        table.add_row(
            str(item['id']),
            item['name'],
            item['url'][:40] + ('...' if len(item['url']) > 40 else ''),
            status_icons.get(item['status'], item['status']),
            item.get('added_at', '')[:16],
        )

    console.print(table)
    pending = sum(1 for i in items if i['status'] == 'pending')
    console.print(f"\n[dim]Tổng: {len(items)} | Chờ xử lý: {pending}[/dim]")


@queue.command('remove')
@click.argument('item_id', type=int)
def queue_remove(item_id):
    """Xóa 1 link khỏi hàng đợi theo ID"""
    from modules.queue_manager import remove_item

    if remove_item(item_id):
        console.print(f"[green]✓ Đã xóa item #{item_id}[/green]")
    else:
        console.print(f"[red]✗ Không tìm thấy item #{item_id}[/red]")


@queue.command('run')
@click.argument('ids', nargs=-1, type=int)
@click.option('--retry', is_flag=True, help='Chạy lại các link bị lỗi')
def queue_run(ids, retry):
    """Chạy links trong hàng đợi

    Không có tham số: chạy tất cả pending.
    Có IDs: chạy riêng các link theo ID.
    --retry: chạy lại các link bị lỗi.

    \b
    Ví dụ:
      python main.py queue run          # Chạy tất cả pending
      python main.py queue run 12       # Chạy riêng link #12
      python main.py queue run 12 14 17 # Chạy 3 links cụ thể
      python main.py queue run --retry  # Chạy lại các link lỗi
    """
    from datetime import datetime
    from modules.queue_manager import (
        get_pending_items, get_items_by_ids, get_error_items,
        update_item_status, update_item_courses, reset_running_items
    )
    from modules.facebook_scraper import scrape_facebook_post
    from modules.udemy_enroller import enroll_multiple_courses, check_login_status
    from modules.udemy_parser import parse_udemy_url
    from modules.report_generator import create_report
    from modules.network import wait_for_internet

    # Reset any stale 'running' items from interrupted runs
    reset_count = reset_running_items()
    if reset_count > 0:
        console.print(f"[yellow]>> Da reset {reset_count} link bi ket 'dang chay' ve 'cho xu ly'[/yellow]")

    # Determine which items to run
    if ids:
        items_to_run = get_items_by_ids(list(ids))
        not_found = set(ids) - {i['id'] for i in items_to_run}
        if not_found:
            console.print(f"[red]✗ Không tìm thấy ID: {', '.join(str(i) for i in not_found)}[/red]")
        if not items_to_run:
            return
        mode_label = f"Chạy {len(items_to_run)} link được chọn"
    elif retry:
        items_to_run = get_error_items()
        if not items_to_run:
            console.print("[yellow]Không có link nào bị lỗi cần retry.[/yellow]")
            return
        mode_label = f"Retry {len(items_to_run)} link bị lỗi"
    else:
        items_to_run = get_pending_items()
        if not items_to_run:
            console.print("[yellow]Không có link nào trong hàng đợi cần xử lý.[/yellow]")
            console.print("Dùng: [bold]python main.py queue add <URL> --name 'Tên'[/bold]")
            return
        mode_label = f"Chạy {len(items_to_run)} link pending"

    console.print(Panel.fit(
        "[bold green]📋 Chạy hàng đợi[/bold green]\n"
        f"{mode_label}",
        border_style="green"
    ))

    # Show items to run
    for item in items_to_run:
        console.print(f"  {item['id']}. {item['name']}")

    # === PRE-FLIGHT: Check login status ===
    console.print("\n[bold blue]🔐 Pre-flight: Kiểm tra đăng nhập...[/bold blue]")

    # Check Facebook login first (needed for scanning)
    from modules.facebook_scraper import check_fb_login_status
    console.print("[dim]  Kiểm tra Facebook...[/dim]")
    fb_logged_in = check_fb_login_status()
    if fb_logged_in:
        console.print("[green]  ✓ Facebook: Đã đăng nhập[/green]")
    else:
        console.print("[red]  ✗ Facebook: Chưa đăng nhập![/red]")
        console.print("  Chạy lệnh: [bold]python main.py login-fb[/bold] để đăng nhập Facebook")
        console.print("[yellow]  ⚠ Không thể quét link Udemy từ Facebook nếu chưa đăng nhập![/yellow]")
        return

    # Check Udemy login (needed for enrolling)
    console.print("[dim]  Kiểm tra Udemy...[/dim]")
    if not check_login_status():
        console.print("[red]  ✗ Udemy: Chưa đăng nhập![/red]")
        console.print("  Chạy lệnh: [bold]python main.py login[/bold] để đăng nhập Udemy")
        return
    console.print("[green]  ✓ Udemy: Đã đăng nhập[/green]")
    console.print("[green]  ✓ Pre-flight OK![/green]")

    # === PHASE 1: SCAN ===
    console.print("\n[bold blue]🔍 Phase 1: Scan links...[/bold blue]")
    
    scan_results = {}  # item_id -> list of udemy URLs
    total_courses = 0
    
    for idx, item in enumerate(items_to_run, 1):
        # Check if already scanned (has courses saved)
        if item.get('courses'):
            udemy_links = [c['url'] for c in item['courses']]
            console.print(f"  {item['id']}. {item['name']} → {len(udemy_links)} khóa (đã scan trước)")
        else:
            console.print(f"  [dim]Scanning [{idx}/{len(items_to_run)}] {item['name']}...[/dim]")
            wait_for_internet()
            
            try:
                udemy_links = scrape_facebook_post(item['url'])
            except Exception as e:
                console.print(f"  [red]✗ Lỗi scan {item['name']}: {e}[/red]")
                udemy_links = []
            
            # Save courses to queue
            courses_data = []
            for link in udemy_links:
                course = parse_udemy_url(link)
                courses_data.append({
                    "url": link,
                    "slug": course.slug if course else link.split('/')[-1],
                })
            update_item_courses(item['id'], courses_data)
            console.print(f"  {item['id']}. {item['name']} → [green]{len(udemy_links)} khóa học[/green]")
        
        scan_results[item['id']] = udemy_links
        total_courses += len(udemy_links)
    
    # Show scan summary
    console.print(f"\n[bold]Tổng: {total_courses} khóa học từ {len(items_to_run)} links[/bold]")
    console.print("[dim]Dùng 'python main.py queue courses <ID>' để xem chi tiết từng link[/dim]")
    
    if total_courses == 0:
        console.print("[yellow]Không tìm thấy khóa học nào. Dừng.[/yellow]")
        return
    
    

    # Auto-confirm countdown: 5 minutes, Ctrl+C to cancel, Enter to skip
    import time, sys
    try:
        import msvcrt
        has_msvcrt = True
    except ImportError:
        has_msvcrt = False

    WAIT_SECONDS = 300
    console.print(f"\n[bold yellow]⏳ Tự động bắt đầu đăng ký {total_courses} khóa học sau [white]{WAIT_SECONDS // 60} phút[/white]...[/bold yellow]")
    if has_msvcrt:
        console.print("[dim]   Nhấn [bold]Enter[/bold] để bắt đầu ngay, hoặc [bold]Ctrl+C[/bold] để hủy và giữ lại dữ liệu.[/dim]\n")
    else:
        console.print("[dim]   Nhấn [bold]Ctrl+C[/bold] để hủy và giữ lại dữ liệu scan.[/dim]\n")
        
    try:
        for remaining in range(WAIT_SECONDS, 0, -1):
            mins, secs = divmod(remaining, 60)
            msg = f"\r   ⏱  Còn lại: {mins:02d}:{secs:02d}  "
            if has_msvcrt:
                msg += "[dim](Nhấn Enter để skip)[/dim] "
            sys.stdout.write(msg)
            sys.stdout.flush()
            
            skipped = False
            if has_msvcrt:
                for _ in range(10):  # Check multiple times per second for responsiveness
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        if key in (b'\r', b'\n'):
                            skipped = True
                            break
                    time.sleep(0.1)
                
                if skipped:
                    sys.stdout.write("\n[green]▶ Đã bỏ qua đếm ngược. Bắt đầu ngay![/green]\n")
                    break
            else:
                time.sleep(1)
                
        sys.stdout.write("\r" + " " * 60 + "\r")  # clear countdown line
        sys.stdout.flush()
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        console.print("[yellow]⚠ Đã hủy. Dữ liệu scan đã lưu, bạn có thể chạy lại sau.[/yellow]")
        return
    
    # === PHASE 2: ENROLL ===
    console.print("\n[bold blue]🚀 Phase 2: Đăng ký khóa học...[/bold blue]")
    
    start_time = datetime.now()
    queue_results = []
    
    for idx, item in enumerate(items_to_run, 1):
        udemy_links = scan_results.get(item['id'], [])
        
        console.print(f"\n{'='*50}")
        console.print(f"[bold blue]📋 [{idx}/{len(items_to_run)}] {item['name']} ({len(udemy_links)} khóa)[/bold blue]")
        console.print(f"[dim]{item['url']}[/dim]\n")
        
        update_item_status(item['id'], 'running')
        
        if not udemy_links:
            console.print("[yellow]Không có khóa học nào.[/yellow]")
            update_item_status(item['id'], 'done', {"courses_found": 0})
            queue_results.append({
                "item": item,
                "courses_found": 0,
                "results": [],
            })
            continue
        
        try:
            console.print("[blue]🚀 Bắt đầu đăng ký...[/blue]\n")
            results = enroll_multiple_courses(udemy_links, source_url=item['url'])
            
            success_count = sum(1 for r in results if r.get('status') in ('success', 'already_enrolled'))
            skipped_count = sum(1 for r in results if r.get('status') == 'skipped')
            failed_count = len(results) - success_count - skipped_count
            
            console.print(f"\n[green]✓ {item['name']}: {success_count} thành công, {skipped_count} bỏ qua, {failed_count} lỗi[/green]")
            
            # Map results to save back to queue
            from modules.udemy_parser import parse_udemy_url
            updated_courses = []
            for r in results:
                slug = r.get('course_name')
                if not slug:
                    parsed = parse_udemy_url(r['url'])
                    slug = parsed.slug if parsed else r['url'].split('/')[-1]
                
                updated_courses.append({
                    "url": r['url'],
                    "slug": str(slug)[:80],
                    "status": r.get('status', 'unknown'),
                    "message": r.get('message', '')
                })
            
            update_item_courses(item['id'], updated_courses)
            update_item_status(item['id'], 'done', {"courses_found": len(udemy_links)})
            queue_results.append({
                "item": item,
                "courses_found": len(udemy_links),
                "results": results,
            })
        
        except Exception as e:
            console.print(f"[red]✗ Lỗi xử lý {item['name']}: {e}[/red]")
            update_item_status(item['id'], 'error')
            queue_results.append({
                "item": item,
                "courses_found": len(udemy_links),
                "results": [],
                "error": str(e),
            })

    end_time = datetime.now()

    # Generate report
    console.print(f"\n{'='*50}")
    report_path = create_report(queue_results, start_time, end_time)
    console.print(f"\n[green]✓ Hoàn thành tất cả![/green]")
    console.print(f"[blue]📄 Report đã lưu: {report_path}[/blue]")
    console.print(f"[dim]Xem lại: python main.py queue report --latest[/dim]")

    # Summary table
    total_courses = sum(qr['courses_found'] for qr in queue_results)
    total_success = sum(
        sum(1 for r in qr.get('results', []) if r.get('status') in ('success', 'already_enrolled'))
        for qr in queue_results
    )

    summary = Table(title="📊 Tổng kết Queue")
    summary.add_column("Chỉ số", style="bold")
    summary.add_column("Giá trị", justify="right")
    summary.add_row("Links đã xử lý", str(len(queue_results)))
    summary.add_row("Tổng khóa học", str(total_courses))
    summary.add_row("[green]Thành công[/green]", str(total_success))

    duration = end_time - start_time
    minutes = int(duration.total_seconds() // 60)
    seconds = int(duration.total_seconds() % 60)
    summary.add_row("Thời gian", f"{minutes}p {seconds}s")
    console.print(summary)


@queue.command('report')
@click.option('--latest', is_flag=True, help='Xem report mới nhất')
@click.option('--list', 'list_all', is_flag=True, help='Liệt kê tất cả reports')
def queue_report(latest, list_all):
    """Xem report kết quả enrollment"""
    from modules.report_generator import list_reports, get_latest_report

    if list_all:
        reports = list_reports()
        if not reports:
            console.print("[yellow]Chưa có report nào.[/yellow]")
            return
        console.print("[bold]📄 Danh sách reports:[/bold]")
        for r in reports:
            size_kb = r.stat().st_size / 1024
            console.print(f"  - {r.name} ({size_kb:.1f} KB)")
        return

    if latest:
        report = get_latest_report()
        if not report:
            console.print("[yellow]Chưa có report nào.[/yellow]")
            return
        console.print(f"[bold blue]📄 {report.name}[/bold blue]\n")
        console.print(report.read_text(encoding='utf-8'))
        return

    # Default: show latest
    report = get_latest_report()
    if report:
        console.print(f"[bold blue]📄 {report.name}[/bold blue]\n")
        console.print(report.read_text(encoding='utf-8'))
    else:
        console.print("[yellow]Chưa có report nào. Chạy 'python main.py queue run' trước.[/yellow]")


@queue.command('clear')
def queue_clear():
    """Xóa toàn bộ hàng đợi"""
    from modules.queue_manager import clear_queue, list_items

    items = list_items()
    if not items:
        console.print("[yellow]Hàng đợi đã trống.[/yellow]")
        return

    if not click.confirm(f"Xóa toàn bộ {len(items)} item trong hàng đợi?", default=False):
        console.print("[yellow]Đã hủy.[/yellow]")
        return

    clear_queue()
    console.print("[green]✓ Đã xóa toàn bộ hàng đợi.[/green]")


@queue.command('courses')
@click.argument('item_id', type=int)
def queue_courses(item_id):
    """Xem danh sách khóa học trong 1 link

    ITEM_ID: ID của link trong queue
    """
    from modules.queue_manager import get_item_by_id

    item = get_item_by_id(item_id)
    if not item:
        console.print(f"[red]✗ Không tìm thấy item #{item_id}[/red]")
        return

    courses = item.get('courses', [])
    if not courses:
        console.print(f"[yellow]Link #{item_id} ({item['name']}) chưa được scan.[/yellow]")
        console.print("Chạy: [bold]python main.py queue run[/bold] để scan và đăng ký")
        return

    console.print(Panel.fit(
        f"[bold cyan]📋 {item['name']}[/bold cyan]\n"
        f"URL: {item['url'][:60]}...\n"
        f"Tổng: {len(courses)} khóa học",
        border_style="cyan"
    ))

    table = Table(title=f"Khóa học trong link #{item_id}")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Slug", style="cyan", max_width=40)
    table.add_column("URL", max_width=40)
    table.add_column("Status", justify="center")
    table.add_column("Message", style="dim", max_width=40)

    for i, course in enumerate(courses, 1):
        slug = course.get('slug', 'unknown')
        url = course.get('url', '')
        status_raw = course.get('status', 'pending')
        msg = course.get('message', '')
        
        # Format status
        if status_raw == 'success':
            status_text = "[green]✓ Miễn phí[/green]"
        elif status_raw == 'already_enrolled':
            status_text = "[yellow]⚠ Đã đăng ký[/yellow]"
        elif status_raw in ('skipped'):
            status_text = "[magenta]💰 Mất phí[/magenta]"
        elif status_raw in ('failed', 'error'):
            status_text = "[red]✗ Lỗi[/red]"
        else:
            status_text = "[bright_black]Chờ đăng ký[/bright_black]"

        if len(url) > 40:
            url = url[:37] + '...'
        if len(slug) > 40:
            slug = slug[:37] + '...'
            
        table.add_row(str(i), slug, url, status_text, msg)

    console.print(table)


@cli.command()
def watch():
    """🔄 Chế độ tương tác - paste link Facebook để tự động thêm vào queue"""
    from datetime import datetime
    from modules.queue_manager import add_item, list_items

    console.print(Panel.fit(
        "[bold green]🔄 Chế độ tương tác[/bold green]\n"
        "Paste link Facebook vào đây → tự động thêm vào queue\n"
        "[dim]Gõ 'run' để chạy queue | 'list' để xem | 'exit' để thoát[/dim]",
        border_style="green"
    ))

    while True:
        try:
            console.print()
            user_input = input("📋 Paste link: ").strip()

            if not user_input:
                continue

            # Commands
            if user_input.lower() in ('exit', 'quit', 'q'):
                console.print("[yellow]👋 Thoát.[/yellow]")
                break

            if user_input.lower() == 'run':
                import subprocess, sys
                console.print("[blue]🚀 Đang chạy queue...[/blue]\n")
                subprocess.run([sys.executable, 'main.py', 'queue', 'run'])
                continue

            if user_input.lower() == 'list':
                import subprocess, sys
                subprocess.run([sys.executable, 'main.py', 'queue', 'list'])
                continue

            # Check if it's a Facebook URL
            if 'facebook' in user_input.lower() or 'fb.com' in user_input.lower():
                today_str = datetime.now().strftime('%d/%m/%Y')
                all_items = list_items()
                today_count = sum(
                    1 for i in all_items
                    if i.get('added_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))
                )
                name = f"FB Coupons #{today_count + 1} ({today_str})"
                item = add_item(user_input, name)

                if item is None:
                    console.print(f"[yellow]⚠ Link này đã có trong queue rồi![/yellow]")
                else:
                    console.print(f"[green]✓ Đã thêm:[/green] [cyan]{item['name']}[/cyan] (ID: {item['id']})")
            else:
                console.print("[yellow]⚠ Không phải Facebook link. Chỉ hỗ trợ link Facebook.[/yellow]")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]👋 Thoát.[/yellow]")
            break


if __name__ == '__main__':
    import sys

    # Auto-detect: if first arg is a Facebook URL, add to queue automatically
    if len(sys.argv) == 2 and ('facebook' in sys.argv[1].lower() or 'fb.com' in sys.argv[1].lower()):
        from datetime import datetime
        from modules.queue_manager import add_item, list_items

        url = sys.argv[1]
        today_str = datetime.now().strftime('%d/%m/%Y')
        all_items = list_items()
        today_count = sum(
            1 for i in all_items
            if i.get('added_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))
        )
        name = f"FB Coupons #{today_count + 1} ({today_str})"
        item = add_item(url, name)

        if item is None:
            console.print(f"[yellow]⚠ Link này đã có trong queue rồi![/yellow]")
            console.print(f"  URL: {url[:70]}")
        else:
            console.print(f"[green]✓ Auto-added vào queue:[/green]")
            console.print(f"  ID: [bold]{item['id']}[/bold]")
            console.print(f"  Tên: [cyan]{item['name']}[/cyan]")
            console.print(f"  URL: [dim]{item['url'][:70]}{'...' if len(item['url']) > 70 else ''}[/dim]")
            console.print(f"\n[dim]Dùng 'python main.py queue run' để bắt đầu đăng ký[/dim]")
    else:
        cli()
