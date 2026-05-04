"""
Network resilience utilities
Handles internet disconnection, retry logic, and browser recovery
"""
import time
import socket
from rich.console import Console

console = Console()

NETWORK_ERRORS = [
    'ERR_INTERNET_DISCONNECTED',
    'ERR_NETWORK_CHANGED',
    'ERR_CONNECTION_RESET',
    'ERR_CONNECTION_REFUSED',
    'ERR_CONNECTION_TIMED_OUT',
    'ERR_NAME_NOT_RESOLVED',
    'ERR_TIMED_OUT',
    'net::ERR_',
    'NS_ERROR_',
]


def is_network_error(error: Exception) -> bool:
    """Check if an exception is a network-related error"""
    error_str = str(error)
    return any(err in error_str for err in NETWORK_ERRORS)


def check_internet(timeout: int = 3) -> bool:
    """Quick internet connectivity check via DNS"""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        return False


def wait_for_internet(check_interval: int = 10, max_wait: int = 3600) -> bool:
    """
    Wait until internet connection is available

    Args:
        check_interval: Seconds between checks
        max_wait: Maximum total wait time in seconds (default 1 hour)

    Returns:
        True if internet restored, False if max_wait exceeded
    """
    if check_internet():
        return True

    console.print(f"[yellow]⏸ Mất kết nối internet. Đang chờ khôi phục...[/yellow]")
    waited = 0

    while waited < max_wait:
        time.sleep(check_interval)
        waited += check_interval

        if check_internet():
            console.print(f"[green]✓ Internet đã khôi phục! (sau {waited}s) Tiếp tục...[/green]")
            # Extra wait for connection to stabilize
            time.sleep(3)
            return True

        minutes = waited // 60
        seconds = waited % 60
        console.print(f"[dim]  ⏸ Chờ internet... ({minutes}p{seconds}s đã trôi qua)[/dim]")

    console.print(f"[red]✗ Đã chờ {max_wait}s nhưng không có internet.[/red]")
    return False


def safe_goto(page, url: str, timeout: int = 30000, max_retries: int = 5) -> bool:
    """
    Navigate to URL with network error retry

    Args:
        page: Playwright page object
        url: URL to navigate to
        timeout: Navigation timeout in ms
        max_retries: Maximum retry attempts

    Returns:
        True if navigation successful, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            return True
        except Exception as e:
            if is_network_error(e):
                console.print(f"[yellow]⏸ Lỗi mạng (lần {attempt}/{max_retries}): {str(e)[:60]}[/yellow]")
                if wait_for_internet():
                    # Wait a bit more for browser to recover
                    try:
                        page.wait_for_timeout(2000)
                    except:
                        pass
                    continue
                else:
                    return False
            else:
                # Non-network error, re-raise
                raise

    console.print(f"[red]✗ Không thể mở URL sau {max_retries} lần thử[/red]")
    return False
