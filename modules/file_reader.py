"""
Link file reader - Extract Udemy links from linkpost.txt
"""
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from rich.console import Console
from config import BASE_DIR, SLOW_MO, UDEMY_BASE_URL

console = Console()

LINK_FILE = BASE_DIR / "linkpost.txt"


def read_course_names_from_file(file_path: Path = LINK_FILE) -> list[str]:
    """
    Read course names from linkpost.txt
    Format: Each course name is on a line before a URL line
    """
    if not file_path.exists():
        console.print(f"[red]File không tồn tại: {file_path}[/red]")
        return []
    
    content = file_path.read_text(encoding='utf-8')
    lines = content.strip().split('\n')
    
    course_names = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Skip empty lines and URL lines
        if not line or line.startswith('http'):
            continue
        
        # Skip header lines
        if 'Udemy Free Courses' in line or '100% Off' in line:
            continue
        
        # Check if next line is a URL (means this line is a course name)
        if i + 1 < len(lines) and lines[i + 1].strip().startswith('http'):
            course_names.append(line)
    
    return course_names


def search_udemy_course(page, course_name: str) -> str:
    """
    Search for a course on Udemy and return its URL if found free with coupon
    """
    try:
        # Clean course name for search
        search_query = course_name.replace(':', '').replace('-', ' ')[:50]
        search_url = f"{UDEMY_BASE_URL}/courses/search/?q={search_query.replace(' ', '+')}"
        
        page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(2000)
        
        # Find first course link
        course_link = page.query_selector('a[data-purpose="course-title-url"]')
        if course_link:
            href = course_link.get_attribute('href')
            if href:
                return f"{UDEMY_BASE_URL}{href}" if href.startswith('/') else href
        
        return None
    except Exception as e:
        return None


def extract_udemy_links_from_file(file_path: Path = LINK_FILE) -> list[str]:
    """
    Read course names from file and search on Udemy
    """
    # First, check for direct Udemy links in the file
    content = file_path.read_text(encoding='utf-8') if file_path.exists() else ""
    
    # Extract any direct Udemy links
    udemy_pattern = r'https?://(?:www\.)?udemy\.com/course/[^\s<>"\')\]]+(?:\?[^\s<>"\')\]]*)?'
    direct_links = re.findall(udemy_pattern, content)
    
    if direct_links:
        console.print(f"[green]Tìm thấy {len(direct_links)} Udemy links trực tiếp[/green]")
        return list(set(direct_links))
    
    # If no direct links, get course names and search
    course_names = read_course_names_from_file(file_path)
    
    if not course_names:
        console.print("[yellow]Không tìm thấy tên khóa học trong file[/yellow]")
        return []
    
    console.print(f"[blue]Tìm thấy {len(course_names)} tên khóa học[/blue]")
    console.print("[yellow]Đang tìm kiếm trên Udemy...[/yellow]")
    
    udemy_links = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel='chrome',
            args=['--disable-blink-features=AutomationControlled'],
            ignore_default_args=['--enable-automation'],
        )
        
        try:
            context = browser.new_context()
            page = context.new_page()
            
            for i, name in enumerate(course_names[:20], 1):  # Limit to 20 courses
                console.print(f"[dim]  Tìm {i}/{min(len(course_names), 20)}: {name[:40]}...[/dim]", end="\r")
                
                url = search_udemy_course(page, name)
                if url:
                    udemy_links.append(url)
            
            console.print(" " * 80, end="\r")
            
        finally:
            browser.close()
    
    console.print(f"[green]Tìm thấy {len(udemy_links)} khóa học trên Udemy[/green]")
    return list(set(udemy_links))
