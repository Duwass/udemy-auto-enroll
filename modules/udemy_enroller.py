"""
Udemy auto-enrollment module using Playwright
"""
from playwright.sync_api import sync_playwright, Browser, BrowserContext
from rich.console import Console
from config import BROWSER_DATA_DIR, UDEMY_BASE_URL, HEADLESS, SLOW_MO, ENROLL_TIMEOUT
from modules.udemy_parser import parse_udemy_url, UdemyCourse
from modules.network import wait_for_internet, safe_goto, is_network_error

console = Console()


def get_persistent_context(playwright) -> BrowserContext:
    """Get browser context with saved login state using real Chrome"""
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(BROWSER_DATA_DIR),
        headless=False,  # Must be False to bypass Cloudflare
        slow_mo=SLOW_MO,
        viewport={'width': 1280, 'height': 800},
        # Use real Chrome browser instead of Playwright Chromium
        channel='chrome',
        # Anti-detection settings
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
        ],
        ignore_default_args=['--enable-automation'],
    )


def login_udemy():
    """
    Open browser for user to login to Udemy manually
    Session will be saved for future use
    """
    with sync_playwright() as p:
        context = get_persistent_context(p)
        page = context.new_page()
        
        console.print("[yellow]Đang mở Udemy...[/yellow]")
        console.print("[yellow]Hãy đăng nhập tài khoản Udemy của bạn[/yellow]")
        console.print("[yellow]Sau khi đăng nhập xong, nhấn Enter trong terminal để tiếp tục...[/yellow]")
        
        try:
            # Navigate to Udemy homepage first (more stable than login popup)
            page.goto(UDEMY_BASE_URL, wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            console.print(f"[yellow]Đang chờ trang load... ({e})[/yellow]")
        
        # Wait for user to login
        input("\n>>> Nhấn Enter sau khi đã đăng nhập Udemy... ")
        
        # Give page some time to update after login
        try:
            page.wait_for_timeout(2000)
        except:
            pass
        
        # Check if logged in by looking for user menu on current page
        is_logged_in = False
        try:
            # Try to find user dropdown on current page
            is_logged_in = page.query_selector('[data-purpose="user-dropdown"]') is not None
            
            # If not found, try navigating to homepage
            if not is_logged_in:
                page.goto(UDEMY_BASE_URL, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(2000)
                is_logged_in = page.query_selector('[data-purpose="user-dropdown"]') is not None
        except Exception as e:
            console.print(f"[dim]Check login: {e}[/dim]")
        
        if is_logged_in:
            console.print("[green]✓ Đăng nhập thành công! Session đã được lưu.[/green]")
        else:
            console.print("[yellow]⚠ Không thể xác nhận đăng nhập tự động.[/yellow]")
            console.print("[yellow]  Nếu bạn đã đăng nhập, session vẫn được lưu.[/yellow]")
            console.print("[yellow]  Hãy thử chạy: python main.py status[/yellow]")
        
        context.close()
        return is_logged_in


def check_login_status() -> bool:
    """Check if user is logged into Udemy"""
    with sync_playwright() as p:
        context = get_persistent_context(p)
        page = context.new_page()
        
        try:
            page.goto(UDEMY_BASE_URL, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(3000)  # Wait for dynamic content
            is_logged_in = page.query_selector('[data-purpose="user-dropdown"]') is not None
            return is_logged_in
        except:
            return False
        finally:
            context.close()


def detect_course_type(page) -> str:
    """
    Detect button type on Udemy course page.

    Returns:
        'enrolled'               - Already enrolled (Go to course button present)
        'free'                   - Free course (Enroll now button)
        'paid'                   - Paid course (Buy now button)
        'subscription'           - Subscription-only course (Start subscription button)
        'subscription_with_free' - New mechanism: subscription + buy individual (Free option available)
        'unknown'                - No recognizable button found
    """
    # Already enrolled
    already_enrolled_selectors = [
        '[data-purpose="go-to-course-button"]',
        'button:has-text("Go to course")',
        'text=You purchased this course',
        'text=Bạn đã mua khóa học này',
    ]
    for selector in already_enrolled_selectors:
        try:
            if page.query_selector(selector):
                return 'enrolled'
        except:
            continue

    # ====================================================================
    # NEW UI DETECTION (collapsible purchase sections with radio buttons)
    # The new Udemy UI has collapsible panels:
    #   Panel 1: "Subscribe and save" (radio, expanded by default)
    #   Panel 2: "Buy individual course" (radio, collapsed by default)
    # The "Start subscription" / "Enroll now" / "Buy now" / "Add to cart"
    # buttons are INSIDE these panels, not standalone.
    # We detect the new UI by looking for the collapsible panel structure.
    # ====================================================================

    # Detect new collapsible purchase UI
    has_collapsible_purchase = page.query_selector('[class*="collapsible-purchase-section"]')
    has_subscribe_text = page.query_selector('text=Subscribe and save')
    has_buy_individual = page.query_selector('text=Buy individual course')

    if has_collapsible_purchase or (has_subscribe_text and has_buy_individual):
        # New UI detected — has both subscription and individual purchase options
        return 'subscription_with_free'

    # Legacy: subscription-only (no "Buy individual" option)
    if has_subscribe_text and not has_buy_individual:
        return 'subscription'

    # Also check for Start subscription button (legacy selector)
    start_sub_btn = page.query_selector('button:has-text("Start subscription")')
    if start_sub_btn:
        if has_buy_individual:
            return 'subscription_with_free'
        return 'subscription'

    # Free course — "Enroll now" button must be VISIBLE
    enroll_btn = page.query_selector('button:has-text("Enroll now")') or \
                 page.query_selector('button:has-text("Enroll Now")')
    if enroll_btn:
        try:
            is_visible = enroll_btn.is_visible()
        except:
            is_visible = True
        if is_visible:
            return 'free'

    # Paid course — check data-purpose first (most reliable), then text
    if page.query_selector('[data-purpose="buy-now-button"]') or \
       page.query_selector('button:has-text("Buy now")') or \
       page.query_selector('button:has-text("Buy Now")'):
        return 'paid'

    return 'unknown'


def enroll_course(course: UdemyCourse) -> dict:
    """
    Enroll in a single Udemy course (FREE courses only)
    
    Returns:
        dict with keys: success, message, course_name, status
    """
    result = {
        'success': False,
        'message': '',
        'course_name': None,
        'status': 'failed'
    }
    
    with sync_playwright() as p:
        context = get_persistent_context(p)
        page = context.new_page()
        
        try:
            console.print(f"[blue]Đang mở khóa học: {course.slug}[/blue]")
            
            # Navigate to course page with coupon
            page.goto(course.enroll_url, wait_until='domcontentloaded', timeout=ENROLL_TIMEOUT)
            
            # Wait 10s for page to fully load
            console.print(f"[dim]  → Đợi trang tải đầy đủ (10s)...[/dim]")
            page.wait_for_timeout(10000/2)
            
            # Get course name
            title_element = page.query_selector('h1[data-purpose="lead-title"]')
            if title_element:
                result['course_name'] = title_element.inner_text()
            else:
                title_element = page.query_selector('h1')
                if title_element:
                    result['course_name'] = title_element.inner_text()
            
            # === DETECT COURSE TYPE ===
            course_type = detect_course_type(page)

            if course_type == 'enrolled':
                result['success'] = True
                result['message'] = 'Đã đăng ký trước đó'
                result['status'] = 'already_enrolled'
                console.print(f"[yellow]⚠ Đã enrolled: {result['course_name']}[/yellow]")
                context.close()
                return result

            if course_type == 'paid':
                result['message'] = 'Khóa học có phí (mua lẻ) - đã skip'
                result['status'] = 'paid_course'
                console.print(f"[yellow]💰 SKIP khóa có phí: {course.slug}[/yellow]")
                context.close()
                return result

            if course_type == 'subscription':
                result['message'] = 'Khóa học chỉ dành cho subscription - đã skip'
                result['status'] = 'subscription_course'
                console.print(f"[yellow]🔒 SKIP khóa subscription: {course.slug}[/yellow]")
                context.close()
                return result

            if course_type == 'unknown':
                result['message'] = 'Không tìm thấy nút đăng ký'
                result['status'] = 'no_button'
                console.print(f"[red]✗ Không tìm thấy nút: {course.slug}[/red]")
                context.close()
                return result

            # course_type == 'free' → proceed
            enroll_now_btn = page.query_selector('button:has-text("Enroll now")') or \
                             page.query_selector('button:has-text("Enroll Now")')
            
            # === ENROLL FREE COURSE ===
            console.print(f"[green]  → Tìm thấy 'Enroll Now' → Khóa miễn phí ✓[/green]")
            enroll_now_btn.click()
            page.wait_for_timeout(3000)
            
            # Handle checkout page for free courses
            if 'checkout' in page.url.lower():
                checkout_selectors = [
                    'button:has-text("Complete Checkout")',
                    'button:has-text("Hoàn tất thanh toán")',
                    'button:has-text("Enroll Now")',
                    'button:has-text("Đăng ký ngay")',
                    'button[type="submit"]'
                ]
                
                for selector in checkout_selectors:
                    checkout_btn = page.query_selector(selector)
                    if checkout_btn:
                        checkout_btn.click()
                        page.wait_for_timeout(5000)
                        break
            
            # Verify enrollment success
            page.goto(course.enroll_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(2000)
            
            if page.query_selector('[data-purpose="go-to-course-button"]'):
                result['success'] = True
                result['message'] = 'Đăng ký thành công!'
                result['status'] = 'success'
                console.print(f"[green]✓ Enrolled: {result['course_name']}[/green]")
            else:
                result['message'] = 'Chưa xác nhận được đăng ký'
                result['status'] = 'unconfirmed'
                console.print(f"[yellow]? Chưa xác nhận: {course.slug}[/yellow]")
                
        except Exception as e:
            result['message'] = f'Lỗi: {str(e)}'
            result['status'] = 'error'
            console.print(f"[red]✗ Lỗi: {e}[/red]")
        finally:
            context.close()
    
    return result


def enroll_multiple_courses(urls: list[str], source_url: str = None, progress_callback = None) -> list[dict]:
    """
    Enroll in multiple courses using a single browser session
    
    Args:
        urls: List of Udemy course URLs
        source_url: Optional source URL (e.g., Facebook post)
        progress_callback: Optional callback function called after each course with index
        
    Returns:
        List of enrollment results
    """
    from modules.history import is_already_enrolled, add_enrollment
    
    results = []
    
    with sync_playwright() as p:
        context = get_persistent_context(p)
        page = context.new_page()
        
        try:
            for i, url in enumerate(urls):
                course = parse_udemy_url(url)
                if not course:
                    console.print(f"[yellow]Bỏ qua URL không hợp lệ: {url}[/yellow]")
                    if progress_callback:
                        progress_callback(i)
                    continue
                
                # Check history
                if is_already_enrolled(url):
                    console.print(f"[yellow]⚠ Đã enrolled trước đó: {course.slug}[/yellow]")
                    results.append({
                        'url': url,
                        'success': True,
                        'status': 'skipped',
                        'message': 'Đã enrolled trước đó (trong history)'
                    })
                    if progress_callback:
                        progress_callback(i)
                    continue
                
                # Check internet before each course
                wait_for_internet()
                
                # Enroll with network error recovery
                max_retries = 3
                result = None
                for attempt in range(1, max_retries + 1):
                    try:
                        result = _enroll_single_course(page, course)
                        break  # Success, exit retry loop
                    except Exception as e:
                        if is_network_error(e) and attempt < max_retries:
                            console.print(f"[yellow]⏸ Lỗi mạng khi xử lý {course.slug}, đang chờ...[/yellow]")
                            if wait_for_internet():
                                # Recover: create new page
                                try:
                                    page.close()
                                except:
                                    pass
                                page = context.new_page()
                                console.print(f"[blue]🔄 Retry {course.slug} (lần {attempt + 1})...[/blue]")
                                continue
                            else:
                                result = {
                                    'success': False,
                                    'message': f'Mất internet: {str(e)[:80]}',
                                    'course_name': course.slug,
                                    'status': 'error'
                                }
                                break
                        else:
                            result = {
                                'success': False,
                                'message': f'Lỗi: {str(e)[:80]}',
                                'course_name': course.slug,
                                'status': 'error'
                            }
                            console.print(f"[red]✗ Lỗi: {e}[/red]")
                            break
                
                result['url'] = url
                
                # Save to history
                add_enrollment(
                    course_url=url,
                    course_name=result.get('course_name'),
                    status=result['status'],
                    source_url=source_url
                )
                
                results.append(result)
                
                # Call progress callback
                if progress_callback:
                    progress_callback(i)
                
                # Small delay between courses
                try:
                    page.wait_for_timeout(2000)
                except:
                    pass
                
        finally:
            context.close()
    
    return results


def _handle_new_pricing(page) -> bool:
    """
    Handle Udemy's new collapsible pricing mechanism.
    
    DOM structure:
    - Panel 1 (expanded by default): "Subscribe and save" → "Start subscription" button
    - Panel 2 (collapsed): "Buy individual course" → "Enroll now" / "Buy now" / "Add to cart"
    
    We need to click the Panel 2 toggler to expand it and collapse Panel 1.
    The toggler is a <button> with class containing 'panel-toggler' and text 'Buy individual course'.
    """
    clicked = False
    
    # Priority 1: Click the panel-toggler button that contains "Buy individual course"
    # This is the most reliable selector based on actual DOM inspection
    selectors = [
        # The actual collapsible panel toggler button
        'button[class*="panel-toggler"]:has-text("Buy individual")',
        # The panel div itself (clicking it also works)
        '[class*="collapsible-purchase-section"] :text("Buy individual course")',
        # Label for the radio
        'label:has-text("Buy individual course")',
        # Direct text match
        'text=Buy individual course',
        # Span inside the panel
        'span:has-text("Buy individual course")',
    ]

    for selector in selectors:
        try:
            element = page.query_selector(selector)
            if element:
                element.click()
                clicked = True
                console.print(f"[dim]  → Click thành công: {selector[:50]}[/dim]")
                break
        except:
            continue

    # Fallback: find the second radio input and click its label
    if not clicked:
        try:
            radios = page.query_selector_all('input[type="radio"].ud-real-toggle-input')
            if len(radios) >= 2:
                # Click the label of the second radio (Buy individual)
                radio_id = radios[1].get_attribute('id')
                if radio_id:
                    label = page.query_selector(f'label[for="{radio_id}"]')
                    if label:
                        label.click()
                        clicked = True
                        console.print(f"[dim]  → Click radio label: {radio_id}[/dim]")
        except:
            pass

    if not clicked:
        return False

    # Wait for the "Buy individual" panel to expand
    console.print(f"[dim]  → Chờ panel 'Buy individual' mở rộng...[/dim]")
    page.wait_for_timeout(2000)
    
    # Verify: check if the panel expanded (aria-expanded changed)
    try:
        page.wait_for_selector(
            '[data-purpose="buy-now-button"], '
            'button:has-text("Enroll now"), '
            'button:has-text("Add to cart"), '
            'button[class*="panel-toggler"][aria-expanded="true"]:has-text("Buy individual")',
            timeout=10000
        )
        page.wait_for_timeout(1000)  # Extra stability wait
    except:
        console.print(f"[dim]  → Timeout chờ panel, thử tiếp...[/dim]")
        page.wait_for_timeout(2000)

    return True


def _enroll_single_course(page, course: UdemyCourse) -> dict:
    """
    Enroll in a single course using existing page
    
    Optimized flow:
    1. Course page: Wait up to 60s for "Enroll now" button
    2. Checkout page: Wait up to 60s for "Enroll now" button
    3. Success page: Auto-proceed to next course
    4. Skip paid courses with notification
    """
    BUTTON_TIMEOUT = 60000  # 60 seconds
    
    result = {
        'success': False,
        'message': '',
        'course_name': None,
        'status': 'failed'
    }
    
    try:
        console.print(f"[blue]📖 Đang mở: {course.slug}[/blue]")
        
        # Navigate to course page with coupon (with network retry)
        if not safe_goto(page, course.enroll_url, timeout=ENROLL_TIMEOUT):
            result['message'] = 'Không thể mở trang khóa học (lỗi mạng)'
            result['status'] = 'error'
            return result
        
        # === WAIT 10s FOR PAGE TO FULLY LOAD ===
        console.print(f"[dim]  → Đợi trang tải đầy đủ (10s)...[/dim]")
        page.wait_for_timeout(10000/2)
        
        # Get course name
        try:
            title_element = page.query_selector('h1[data-purpose="lead-title"]') or page.query_selector('h1')
            if title_element:
                result['course_name'] = title_element.inner_text().strip()
        except:
            result['course_name'] = course.slug
        
        # === DETECT COURSE TYPE ===
        course_type = detect_course_type(page)

        if course_type == 'enrolled':
            result['success'] = True
            result['message'] = 'Đã đăng ký trước đó'
            result['status'] = 'already_enrolled'
            console.print(f"[yellow]⚠ Đã enrolled: {result['course_name']}[/yellow]")
            return result

        if course_type == 'paid':
            result['message'] = 'Khóa học có phí (mua lẻ) - skip'
            result['status'] = 'paid_course'
            console.print(f"[yellow]💰 SKIP khóa có phí: {result['course_name'] or course.slug}[/yellow]")
            return result

        if course_type == 'subscription':
            result['message'] = 'Khóa học chỉ dành cho subscription - skip'
            result['status'] = 'subscription_course'
            console.print(f"[yellow]🔒 SKIP khóa subscription: {result['course_name'] or course.slug}[/yellow]")
            return result

        if course_type == 'subscription_with_free':
            console.print(f"[cyan]  → Phát hiện cơ chế mới (Subscription + Buy Individual)[/cyan]")
            if _handle_new_pricing(page):
                console.print(f"[green]  → Đã chọn 'Buy individual course' ✓[/green]")
                
                # Chờ 10s theo yêu cầu user để đảm bảo TẤT CẢ button (Enroll now / Buy now) hiển thị đầy đủ
                console.print(f"[dim]  → Đợi 10s để load đầy đủ button trong giao diện mới...[/dim]")
                page.wait_for_timeout(10000)

                # Check if already enrolled
                if page.query_selector('[data-purpose="go-to-course-button"]'):
                    result['success'] = True
                    result['message'] = 'Đã đăng ký trước đó'
                    result['status'] = 'already_enrolled'
                    console.print(f"[yellow]⚠ Đã enrolled: {result['course_name']}[/yellow]")
                    return result

                # First priority: Look for Enroll now button (it's a free course!)
                enroll_btn = page.query_selector('button:has-text("Enroll now")') or \
                             page.query_selector('button:has-text("Enroll Now")')
                
                if enroll_btn:
                    # Override course_type to 'free' so the enroll flow below picks it up
                    course_type = 'free'
                else:
                    # Check if paid (Buy now / Add to cart appeared because it's not free)
                    buy_now_btn = page.query_selector('[data-purpose="buy-now-button"]') or \
                                  page.query_selector('button:has-text("Buy now")') or \
                                  page.query_selector('button:has-text("Add to cart")')
                    
                    if buy_now_btn:
                        result['message'] = 'Khóa học có phí sau khi chọn Buy individual - skip'
                        result['status'] = 'paid_course'
                        console.print(f"[yellow]💰 SKIP khóa có phí: {result['course_name'] or course.slug}[/yellow]")
                        return result
                    
                    # If neither found
                    result['message'] = 'Không tìm thấy nút Enroll sau khi chọn Buy individual'
                    result['status'] = 'no_button'
                    console.print(f"[red]✗ Không tìm thấy nút Enroll: {course.slug}[/red]")
                    return result
            else:
                console.print(f"[yellow]  → Không thể chọn 'Buy individual', skip subscription...[/yellow]")
                result['message'] = 'Không thể chọn Buy individual course'
                result['status'] = 'subscription_course'
                return result

        if course_type == 'unknown':
            # Re-check enrolled one more time before giving up
            course_type_retry = detect_course_type(page)
            if course_type_retry == 'enrolled':
                result['success'] = True
                result['message'] = 'Đã đăng ký trước đó'
                result['status'] = 'already_enrolled'
                console.print(f"[yellow]⚠ Đã enrolled: {result['course_name']}[/yellow]")
                return result
            console.print(f"[red]✗ Không tìm thấy nút nào: {course.slug}[/red]")
            result['message'] = 'Không tìm thấy nút đăng ký'
            result['status'] = 'no_button'
            return result

        # course_type == 'free' → proceed to enroll
        console.print(f"[green]  → Tìm thấy 'Enroll Now' → Khóa miễn phí ✓[/green]")
        enroll_now_btn = page.query_selector('button:has-text("Enroll now")') or \
                         page.query_selector('button:has-text("Enroll Now")')
        
        # ============================================================
        # STEP 4: CLICK ENROLL BUTTON WITH RETRY (until checkout)
        # ============================================================
        if not enroll_now_btn:
            console.print(f"[red]✗ Không tìm thấy nút Enroll: {course.slug}[/red]")
            result['message'] = 'Không tìm thấy nút đăng ký'
            result['status'] = 'no_button'
            return result
        
        original_url = page.url
        max_clicks = 5
        
        console.print(f"[dim]  → Click Enroll now...[/dim]")
        
        for click_count in range(1, max_clicks + 1):
            try:
                # Re-find button each time (DOM may have changed)
                btn = page.query_selector('button:has-text("Enroll now")') or \
                      page.query_selector('button[data-purpose="buy-this-course-button"]') or \
                      page.query_selector('button:has-text("Add to cart")')
                
                if btn:
                    btn.click()
                else:
                    page.evaluate('document.querySelector("button[data-purpose=\\"buy-this-course-button\\"]")?.click()')
            except Exception as e:
                console.print(f"[dim]  → Click {click_count} failed: {e}[/dim]")
            
            # Wait for navigation
            page.wait_for_timeout(3000)
            
            current_url = page.url.lower()
            
            # Check if URL changed to checkout/learn/success
            if current_url != original_url.lower():
                if any(p in current_url for p in ['checkout', 'payment', '/learn/', 'success']):
                    console.print(f"[dim]  → Đã chuyển trang sau {click_count} lần click[/dim]")
                    break
            
            # Check if enrolled immediately (Go to course appeared)
            if page.query_selector('[data-purpose="go-to-course-button"]'):
                result['success'] = True
                result['message'] = 'Đăng ký thành công!'
                result['status'] = 'success'
                console.print(f"[green]✓ Enrolled: {result['course_name']}[/green]")
                return result
            
            if click_count < max_clicks:
                console.print(f"[dim]  → Retry click ({click_count}/{max_clicks})...[/dim]")
        
        # === STEP 5: HANDLE CHECKOUT PAGE ===
        current_url = page.url.lower()
        
        # Check for checkout or payment page patterns
        if 'checkout' in current_url or 'payment' in current_url or '/subscribe/' in current_url:
            console.print(f"[dim]  → Đang ở trang Checkout, đợi nút Enroll now (tối đa 60s)...[/dim]")
            
            try:
                # Wait for checkout button with multiple selectors
                page.wait_for_selector(
                    'button:has-text("Enroll"), button:has-text("Complete"), button[data-purpose="checkout-submit-button"]',
                    timeout=BUTTON_TIMEOUT
                )
            except:
                console.print(f"[red]✗ Timeout 60s - không thấy nút checkout: {course.slug}[/red]")
                result['message'] = 'Timeout - checkout button không xuất hiện'
                result['status'] = 'checkout_timeout'
                return result
            
            # Click checkout button
            checkout_selectors = [
                'button:has-text("Enroll now")',
                'button:has-text("Enroll Now")',
                'button:has-text("Complete Checkout")',
                'button[data-purpose="checkout-submit-button"]',
                'button.ud-btn-primary:has-text("Enroll")',
            ]
            
            checkout_btn = None
            for selector in checkout_selectors:
                try:
                    checkout_btn = page.query_selector(selector)
                    if checkout_btn:
                        break
                except:
                    continue
            
            if checkout_btn:
                console.print(f"[dim]  → Click Enroll now trên Checkout...[/dim]")
                checkout_btn.click()

                # Wait for actual page navigation instead of blind sleep
                try:
                    page.wait_for_load_state('domcontentloaded', timeout=15000)
                except:
                    page.wait_for_timeout(5000)

        # === STEP 6: VERIFY SUCCESS ===
        enrollment_confirmed = False

        # --- Check 1: URL-based immediate detection (most reliable) ---
        current_url = page.url
        url_success_patterns = ['/learn/', 'success', 'order-confirm', 'checkout/complete']
        if any(p in current_url.lower() for p in url_success_patterns):
            enrollment_confirmed = True
            console.print(f"[dim]  → Phát hiện URL thành công: {current_url[:60]}[/dim]")

        # --- Check 2: DOM indicators on current page ---
        if not enrollment_confirmed:
            page.wait_for_timeout(3000)  # Allow dynamic content to render
            dom_success_selectors = [
                '[data-purpose="go-to-course-button"]',
                'a[href*="/learn/"]',
                'button:has-text("Go to course")',
            ]
            for selector in dom_success_selectors:
                try:
                    if page.query_selector(selector):
                        enrollment_confirmed = True
                        console.print(f"[dim]  → Phát hiện DOM: {selector}[/dim]")
                        break
                except:
                    continue

        # --- Check 3: Navigate back to course page and use detect_course_type ---
        if not enrollment_confirmed:
            console.print(f"[dim]  → Quay lại trang khóa học để xác nhận...[/dim]")
            try:
                page.goto(course.enroll_url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(4000)  # Wait longer for DOM to settle
                if detect_course_type(page) == 'enrolled':
                    enrollment_confirmed = True
            except Exception as e:
                console.print(f"[dim]  → Lỗi khi quay lại: {e}[/dim]")

        if enrollment_confirmed:
            result['success'] = True
            result['message'] = 'Đăng ký thành công!'
            result['status'] = 'success'
            console.print(f"[green]✓ Enrolled: {result['course_name']}[/green]")
        else:
            result['message'] = 'Chưa xác nhận - kiểm tra thủ công'
            result['status'] = 'unconfirmed'
            console.print(f"[yellow]? Chưa xác nhận: {course.slug}[/yellow]")
            
    except Exception as e:
        result['message'] = f'Lỗi: {str(e)}'
        result['status'] = 'error'
        console.print(f"[red]✗ Lỗi: {e}[/red]")
    
    return result
