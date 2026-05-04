"""
Udemy URL parser - Extract course info from URLs
"""
import re
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass
from typing import Optional


@dataclass
class UdemyCourse:
    """Parsed Udemy course info"""
    url: str
    slug: str
    coupon_code: Optional[str] = None
    
    @property
    def enroll_url(self) -> str:
        """Get URL with coupon for enrollment"""
        if self.coupon_code:
            return f"https://www.udemy.com/course/{self.slug}/?couponCode={self.coupon_code}"
        return f"https://www.udemy.com/course/{self.slug}/"


def parse_udemy_url(url: str) -> Optional[UdemyCourse]:
    """
    Parse Udemy URL to extract course slug and coupon code
    
    Supports formats:
    - https://www.udemy.com/course/course-name/
    - https://www.udemy.com/course/course-name/?couponCode=ABC123
    - https://udemy.com/course/course-name?couponCode=ABC123
    """
    try:
        parsed = urlparse(url)
        
        # Check if it's a Udemy URL
        if 'udemy.com' not in parsed.netloc:
            return None
        
        # Extract course slug from path
        path_match = re.search(r'/course/([^/?]+)', parsed.path)
        if not path_match:
            return None
        
        slug = path_match.group(1)
        
        # Extract coupon code from query params
        query_params = parse_qs(parsed.query)
        coupon_code = query_params.get('couponCode', [None])[0]
        
        return UdemyCourse(
            url=url,
            slug=slug,
            coupon_code=coupon_code
        )
    except Exception:
        return None


def extract_udemy_links(text: str) -> list[str]:
    """
    Extract all Udemy course URLs from text
    """
    # Pattern to match Udemy URLs
    pattern = r'https?://(?:www\.)?udemy\.com/course/[^\s<>"\')\]]+(?:\?[^\s<>"\')\]]*)?'
    
    matches = re.findall(pattern, text)
    
    # Clean up URLs (remove trailing punctuation)
    cleaned = []
    for url in matches:
        # Remove trailing punctuation that might be captured
        url = re.sub(r'[.,;:!?\'"]+$', '', url)
        cleaned.append(url)
    
    return list(set(cleaned))  # Remove duplicates


def is_udemy_link(url: str) -> bool:
    """Check if URL is a valid Udemy course link"""
    return parse_udemy_url(url) is not None
