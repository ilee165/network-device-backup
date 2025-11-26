"""
Utility functions and helpers
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from netbackup.config import LoggingSettings


def setup_logging(settings: LoggingSettings) -> logging.Logger:
    """
    Configure logging for the application
    
    Args:
        settings: Logging configuration settings
        
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger('netbackup')
    logger.setLevel(getattr(logging, settings.level.upper(), logging.INFO))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # Console handler
    if settings.console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if settings.file:
        # Create log directory if needed
        log_path = Path(settings.file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            settings.file,
            maxBytes=settings.max_bytes,
            backupCount=settings.backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    return logger


def format_bytes(bytes_size: int) -> str:
    """
    Format bytes into human-readable string
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 KB", "2.3 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds into human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "1m 30s", "45s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.0f}s"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    return f"{hours}h {remaining_minutes}m"


def validate_device_type(device_type: str) -> bool:
    """
    Validate that device type is supported by Netmiko
    
    Args:
        device_type: Device type string
        
    Returns:
        True if valid, False otherwise
    """
    # Common supported device types
    supported_types = [
        'cisco_ios',
        'cisco_xe',
        'cisco_xr',
        'cisco_nxos',
        'cisco_asa',
        'arista_eos',
        'juniper_junos',
        'hp_comware',
        'hp_procurve',
        'paloalto_panos',
        'fortinet',
        'checkpoint_gaia',
        'dell_force10',
        'avaya_ers',
        'avaya_vsp',
        'mikrotik_routeros',
    ]
    
    return device_type.lower() in supported_types


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to maximum length
    
    Args:
        text: String to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def create_summary_table(headers: list, rows: list) -> str:
    """
    Create a simple ASCII table
    
    Args:
        headers: List of header strings
        rows: List of row lists
        
    Returns:
        Formatted table as string
    """
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Create separator
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    
    # Format header
    header_row = "|" + "|".join(
        f" {h.ljust(col_widths[i])} " for i, h in enumerate(headers)
    ) + "|"
    
    # Format rows
    table_rows = []
    for row in rows:
        table_row = "|" + "|".join(
            f" {str(cell).ljust(col_widths[i])} " for i, cell in enumerate(row)
        ) + "|"
        table_rows.append(table_row)
    
    # Combine
    lines = [separator, header_row, separator]
    lines.extend(table_rows)
    lines.append(separator)
    
    return "\n".join(lines)


def check_credentials(username: Optional[str], password: Optional[str]) -> tuple:
    """
    Check if credentials are provided
    
    Args:
        username: Username (can be None)
        password: Password (can be None)
        
    Returns:
        Tuple of (valid: bool, error_message: str or None)
    """
    if not username:
        return False, "Username not provided. Set NET_USERNAME environment variable."
    
    if not password:
        return False, "Password not provided. Set NET_PASSWORD environment variable."
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    return filename