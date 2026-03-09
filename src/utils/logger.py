"""
Logger utility for OSINT Sherlock Pro
"""
import logging
import sys
from datetime import datetime

# ANSI color codes
class Colors:
    RESET   = "\033[0m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"


def get_logger(name: str = "osint") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger


logger = get_logger()


def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
 ██████╗ ███████╗██╗███╗   ██╗████████╗    ██████╗ ██████╗  ██████╗ 
██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝    ██╔══██╗██╔══██╗██╔═══██╗
██║   ██║███████╗██║██╔██╗ ██║   ██║       ██████╔╝██████╔╝██║   ██║
██║   ██║╚════██║██║██║╚██╗██║   ██║       ██╔═══╝ ██╔══██╗██║   ██║
╚██████╔╝███████║██║██║ ╚████║   ██║       ██║     ██║  ██║╚██████╔╝
 ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝       ╚═╝     ╚═╝  ╚═╝ ╚═════╝ 
{Colors.RESET}
{Colors.YELLOW}  🔍 OSINT Sherlock Pro — Username & Email Intelligence Scanner{Colors.RESET}
{Colors.DIM}  v2.0 | 100+ Sites | Threaded | HTML Dashboard | Breach Detection{Colors.RESET}
{Colors.DIM}  ⚠️  For ethical/legal use only. Always obtain proper authorization.{Colors.RESET}
    """
    print(banner)


def log_found(platform: str, url: str):
    print(f"  {Colors.GREEN}[+]{Colors.RESET} {Colors.BOLD}{platform:<25}{Colors.RESET} {Colors.GREEN}FOUND{Colors.RESET} → {Colors.CYAN}{url}{Colors.RESET}")


def log_not_found(platform: str):
    print(f"  {Colors.RED}[-]{Colors.RESET} {platform:<25} {Colors.DIM}NOT FOUND{Colors.RESET}")


def log_error(platform: str, err: str = ""):
    print(f"  {Colors.YELLOW}[!]{Colors.RESET} {platform:<25} {Colors.YELLOW}ERROR{Colors.RESET} {Colors.DIM}{err}{Colors.RESET}")


def log_info(msg: str):
    print(f"  {Colors.BLUE}[*]{Colors.RESET} {msg}")


def log_success(msg: str):
    print(f"  {Colors.GREEN}[✓]{Colors.RESET} {Colors.BOLD}{msg}{Colors.RESET}")


def log_warning(msg: str):
    print(f"  {Colors.YELLOW}[⚠]{Colors.RESET} {msg}")


def log_section(title: str):
    width = 60
    print(f"\n{Colors.CYAN}{'─' * width}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}  {title}{Colors.RESET}")
    print(f"{Colors.CYAN}{'─' * width}{Colors.RESET}")
