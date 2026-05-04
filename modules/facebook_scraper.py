"""
Facebook post scraper using Playwright
Extracts Udemy links from Facebook group posts
"""
import re
from urllib.parse import unquote, urlparse, parse_qs
from playwright.sync_api import sync_playwright, Page, BrowserContext
from rich.console import Console
from config import FB_BROWSER_DATA_DIR, SLOW_MO
from modules.network import safe_goto, wait_for_internet

console = Console()


def get_fb_persistent_context(playwright) -> BrowserContext:
    """Get browser context with saved Facebook login state using real Chrome"""
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(FB_BROWSER_DATA_DIR),
        headless=False,
        slow_mo=SLOW_MO,
        channel='chrome',
        viewport={'width': 1280, 'height': 900},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
        ],
        ignore_default_args=['--enable-automation'],
    )


def login_facebook():
    """
    Open browser for user to login to Facebook manually.
    Session will be saved in FB_BROWSER_DATA_DIR for future use.
    """
    with sync_playwright() as p:
        context = get_fb_persistent_context(p)
        page = context.new_page()

        console.print("[yellow]Đang mở Facebook...[/yellow]")
        console.print("[yellow]Hãy đăng nhập tài khoản Facebook của bạn[/yellow]")
        console.print("[yellow]Sau khi đăng nhập xong, nhấn Enter trong terminal để tiếp tục...[/yellow]")

        try:
            page.goto('https://www.facebook.com', wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            console.print(f"[yellow]Đang chờ trang load... ({e})[/yellow]")

        input("\n>>> Nhấn Enter sau khi đã đăng nhập Facebook... ")

        try:
            page.wait_for_timeout(2000)
        except:
            pass

        is_logged_in = _check_fb_logged_in(page)

        if is_logged_in:
            console.print("[green]✓ Đăng nhập Facebook thành công! Session đã được lưu.[/green]")
        else:
            console.print("[yellow]⚠ Không thể xác nhận đăng nhập tự động.[/yellow]")
            console.print("[yellow]  Nếu bạn đã đăng nhập, session vẫn được lưu.[/yellow]")

        context.close()
        return is_logged_in


def _check_fb_logged_in(page) -> bool:
    """Check if currently on a logged-in Facebook page"""
    try:
        # Logged-in indicators
        logged_in_selectors = [
            '[aria-label="Your profile"]',
            '[aria-label="Account"]',
            '[aria-label="Tài khoản"]',
            '[aria-label="Trang cá nhân của bạn"]',
            '[data-pagelet="ProfileTilesFeed"]',
            'div[role="banner"] a[href*="/me"]',
            'svg[aria-label="Your profile"]',
        ]
        for selector in logged_in_selectors:
            if page.query_selector(selector):
                return True

        # Check if login form is shown → not logged in
        login_selectors = [
            'input[name="email"]',
            'button[name="login"]',
            '#loginbutton',
        ]
        for selector in login_selectors:
            if page.query_selector(selector):
                return False

        # If no login form found, assume logged in (cookie-based session)
        return True
    except:
        return False


def check_fb_login_status() -> bool:
    """Check if user is logged into Facebook"""
    with sync_playwright() as p:
        context = get_fb_persistent_context(p)
        page = context.new_page()

        try:
            page.goto('https://www.facebook.com', wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(3000)
            return _check_fb_logged_in(page)
        except:
            return False
        finally:
            context.close()


def extract_all_urls(text: str) -> list[str]:
    """Extract all URLs from text"""
    url_pattern = r'https?://[^\s<>"\')\]]+(?:\?[^\s<>"\')\]]*)?'
    urls = re.findall(url_pattern, text)
    
    # Clean URLs
    cleaned = []
    for url in urls:
        url = re.sub(r'[.,;:!?\'"]+$', '', url)
        
        # Filter out truncated URLs (Facebook often shortens display text with ...)
        if '...' in url or '…' in url:
            continue
            
        # Decode Facebook-wrapped URLs
        if 'l.facebook.com/l.php' in url or 'lm.facebook.com/l.php' in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if 'u' in params:
                url = unquote(params['u'][0])
        cleaned.append(url)
    
    return list(set(cleaned))


def is_redirect_url(url: str) -> bool:
    """Check if URL is a redirect/shortener that needs to be followed"""
    redirect_domains = [
        'freewebcart.com', 'bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly',
        'cutt.ly', 'rebrand.ly', 'shorturl.at', 'tiny.cc', 'is.gd', 'v.gd',
        'couponscorpion.com', 'real.discount', 'discudemy.com', 'coursevania.com'
    ]
    return any(domain in url for domain in redirect_domains)


def scrape_facebook_post(post_url: str) -> list[str]:
    """
    Scrape Facebook post and extract Udemy links
    
    Args:
        post_url: Facebook post URL
        
    Returns:
        List of Udemy course URLs found in the post
    """
    udemy_links = []
    all_found_urls = []
    
    with sync_playwright() as p:
        context = get_fb_persistent_context(p)
        
        try:
            page = context.new_page()
            
            console.print(f"[blue]Đang mở Facebook post...[/blue]")
            if not safe_goto(page, post_url, timeout=60000):
                console.print(f"[red]Không thể mở Facebook post (lỗi mạng)[/red]")
                return udemy_links
            page.wait_for_timeout(3000)
            
            # === STEP 1: Close ONLY login/cookie popups (NOT the post modal) ===
            # IMPORTANT: Facebook shows the post content inside a modal/dialog.
            # We must NOT close it. Only close login prompts and cookie banners.
            try:
                login_popup_selectors = [
                    '[data-testid="cookie-policy-manage-dialog-accept-button"]',
                    'button:has-text("Not now")',
                    'button:has-text("Không phải bây giờ")',
                    'button:has-text("Decline optional cookies")',
                    'button:has-text("Allow all cookies")',
                ]
                
                for selector in login_popup_selectors:
                    close_btn = page.query_selector(selector)
                    if close_btn:
                        try:
                            close_btn.click()
                            page.wait_for_timeout(1000)
                            console.print("[dim]Đã đóng popup login/cookie[/dim]")
                            break
                        except:
                            pass
            except:
                pass
            
            page.wait_for_timeout(2000)
            
            # === STEP 2: Find the post modal/dialog and scroll inside it ===
            # Facebook renders the post in a dialog with role="dialog" or
            # a scrollable container. We need to scroll INSIDE it.
            modal_selector = 'div[role="dialog"]'
            modal = page.query_selector(modal_selector)
            
            if modal:
                console.print("[dim]Phát hiện modal bài viết, đang scroll để load toàn bộ...[/dim]")
                # Scroll inside the modal to load all content
                for i in range(15):
                    page.evaluate('''(sel) => {
                        const modal = document.querySelector(sel);
                        if (modal) {
                            // Find the scrollable child inside the modal
                            const scrollable = modal.querySelector('[style*="overflow"]') || modal;
                            scrollable.scrollTop += 800;
                        }
                    }''', modal_selector)
                    page.wait_for_timeout(800)
            else:
                console.print("[dim]Không có modal, scroll trang chính...[/dim]")
                for _ in range(10):
                    page.evaluate('window.scrollBy(0, 600)')
                    page.wait_for_timeout(800)
            
            # === STEP 3: Click "See more" / "Xem thêm" to expand truncated content ===
            try:
                see_more_selectors = [
                    'div[role="button"]:has-text("See more")',
                    'div[role="button"]:has-text("Xem thêm")',
                    'span:has-text("See more")',
                    'span:has-text("Xem thêm")'
                ]
                for selector in see_more_selectors:
                    buttons = page.query_selector_all(selector)
                    for btn in buttons[:5]:
                        try:
                            btn.click()
                            page.wait_for_timeout(500)
                        except:
                            pass
            except:
                pass
            
            page.wait_for_timeout(2000)
            
            # === STEP 4: Extract ALL URLs from the page (including inside modal) ===
            # Get ALL text from the page (includes modal content)
            body_text = page.evaluate('() => document.body.innerText')
            
            # Get ALL links from href attributes (includes modal links)
            href_links = page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                return links.map(a => a.href);
            }''')
            
            # Also specifically extract from dialog/modal if present
            modal_href_links = page.evaluate('''() => {
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return [];
                const links = Array.from(dialog.querySelectorAll('a[href]'));
                return links.map(a => a.href);
            }''')
            
            # Get modal text specifically
            modal_text = page.evaluate('''() => {
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return '';
                return dialog.innerText;
            }''')
            
            # Get page HTML for any embedded links
            page_html = page.content()
            
            # Extract URLs from all sources
            text_urls = extract_all_urls(body_text)
            html_urls = extract_all_urls(page_html)
            modal_text_urls = extract_all_urls(modal_text) if modal_text else []
            
            # Combine all URLs
            all_found_urls = list(set(
                text_urls + html_urls + href_links + modal_href_links + modal_text_urls
            ))
            
            console.print(f"[dim]Tìm thấy {len(all_found_urls)} URLs trong post[/dim]")
            
            # Separate direct Udemy links and redirect links
            redirect_urls = []
            for url in all_found_urls:
                if 'udemy.com/course' in url:
                    udemy_links.append(url)
                elif is_redirect_url(url):
                    redirect_urls.append(url)
            
            console.print(f"[green]  - {len(udemy_links)} Udemy links trực tiếp[/green]")
            console.print(f"[yellow]  - {len(redirect_urls)} redirect links cần follow[/yellow]")
            
            # Follow redirect links to get Udemy URLs
            if redirect_urls:
                console.print("[blue]Đang follow redirect links...[/blue]")
                
                for i, url in enumerate(redirect_urls, 1):
                    console.print(f"[dim]  Following {i}/{len(redirect_urls)}: {url[:60]}...[/dim]")
                    
                    # Check internet before each redirect
                    wait_for_internet()
                    
                    try:
                        if not safe_goto(page, url, timeout=30000):
                            continue
                        
                        page.wait_for_timeout(3000)
                        
                        # Check if already on Udemy
                        if 'udemy.com/course' in page.url:
                            udemy_links.append(page.url)
                            console.print(f"[green]    ✓ → Udemy (direct redirect)[/green]")
                            continue
                        
                        # === FREEWEBCART: Extract Udemy URL from page source ===
                        # Udemy URLs with couponCode are embedded directly in HTML
                        # No need to click buttons or watch ads
                        if 'freewebcart.com' in page.url:
                            fwc_html = page.content()
                            fwc_udemy = re.findall(
                                r'https?://(?:www\.)?udemy\.com/course/[a-zA-Z0-9_-]+/?(?:\?couponCode=[a-zA-Z0-9_-]+)?',
                                fwc_html
                            )
                            fwc_udemy = list(set(fwc_udemy))
                            
                            if fwc_udemy:
                                udemy_links.extend(fwc_udemy)
                                console.print(f"[green]    ✓ → {len(fwc_udemy)} Udemy link(s) từ source[/green]")
                            else:
                                console.print(f"[dim]    ✗ Không tìm thấy Udemy URL trong source[/dim]")
                            
                            continue
                        
                        # === GENERIC REDIRECT HANDLER ===
                        # Search page for Udemy links in href
                        page_udemy_hrefs = page.evaluate('''() => {
                            const links = Array.from(document.querySelectorAll('a[href*="udemy.com/course"]'));
                            return links.map(a => a.href);
                        }''')
                        
                        if page_udemy_hrefs:
                            udemy_links.extend(page_udemy_hrefs)
                            console.print(f"[green]    ✓ → {len(page_udemy_hrefs)} Udemy link(s) từ trang[/green]")
                            continue
                        
                        # Search entire HTML for Udemy URLs
                        page_html = page.content()
                        html_udemy = re.findall(
                            r'https?://(?:www\.)?udemy\.com/course/[a-zA-Z0-9_-]+/?(?:\?[^"\s<>]*)?',
                            page_html
                        )
                        if html_udemy:
                            unique_html = list(set(html_udemy))
                            udemy_links.extend(unique_html)
                            console.print(f"[green]    ✓ → {len(unique_html)} Udemy link(s) từ HTML[/green]")
                            continue
                        
                        console.print(f"[dim]    ✗ Không tìm thấy Udemy link[/dim]")
                            
                    except Exception as e:
                        console.print(f"[dim]    ✗ Lỗi: {str(e)[:50]}[/dim]")
                
                console.print(" " * 50, end="\r")
            
            # Remove duplicates and clean
            udemy_links = list(set(udemy_links))
            
            console.print(f"[green]✓ Tổng cộng: {len(udemy_links)} Udemy courses[/green]")
            
        except Exception as e:
            console.print(f"[red]Lỗi khi đọc Facebook post: {e}[/red]")
        finally:
            context.close()
    
    return udemy_links
