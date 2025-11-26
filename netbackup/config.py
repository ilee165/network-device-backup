"""
Configuration management for network backup system
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Device:
    """Network device configuration"""
    name: str
    hostname: str
    device_type: str
    groups: List[str] = field(default_factory=list)
    enabled: bool = True
    username: Optional[str] = None
    password: Optional[str] = None
    port: int = 22
    timeout: int = 30


@dataclass
class BackupSettings:
    """Backup configuration settings"""
    repository_path: str = "./backups/repo"
    concurrent_backups: int = 3
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay_seconds: int = 5


@dataclass
class ScheduleSettings:
    """Scheduling configuration"""
    enabled: bool = False
    cron_expression: str = "0 2 * * *"


@dataclass
class EmailSettings:
    """Email notification settings"""
    enabled: bool = False
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_use_tls: bool = True
    from_address: str = ""
    to_addresses: List[str] = field(default_factory=list)
    username: str = ""
    password: str = ""


@dataclass
class SlackSettings:
    """Slack notification settings"""
    enabled: bool = False
    webhook_url: str = ""


@dataclass
class NotificationSettings:
    """Notification configuration"""
    email: EmailSettings = field(default_factory=EmailSettings)
    slack: SlackSettings = field(default_factory=SlackSettings)


@dataclass
class LoggingSettings:
    """Logging configuration"""
    level: str = "INFO"
    file: str = "./logs/netbackup.log"
    console: bool = True
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5


class Config:
    """Main configuration class"""
    
    def __init__(self, config_dir: str = "./config"):
        self.config_dir = Path(config_dir)
        self.devices: List[Device] = []
        self.backup: BackupSettings = BackupSettings()
        self.schedule: ScheduleSettings = ScheduleSettings()
        self.notifications: NotificationSettings = NotificationSettings()
        self.logging: LoggingSettings = LoggingSettings()
        
    def load(self):
        """Load configuration from YAML files"""
        self._load_devices()
        self._load_settings()
        
    def _load_devices(self):
        """Load device inventory"""
        devices_file = self.config_dir / "devices.yaml"
        
        if not devices_file.exists():
            raise FileNotFoundError(
                f"Device configuration not found: {devices_file}\n"
                f"Copy devices.yaml.example to devices.yaml and configure your devices."
            )
        
        with open(devices_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Load credentials
        credentials = data.get('credentials', {})
        default_creds = credentials.get('default', {})
        
        default_username = os.getenv(default_creds.get('username_env', ''))
        default_password = os.getenv(default_creds.get('password_env', ''))
        
        # Load devices
        for device_data in data.get('devices', []):
            # Get device-specific or default credentials
            device_creds = credentials.get(device_data['name'], default_creds)
            username = os.getenv(device_creds.get('username_env', ''), default_username)
            password = os.getenv(device_creds.get('password_env', ''), default_password)
            
            device = Device(
                name=device_data['name'],
                hostname=device_data['hostname'],
                device_type=device_data['device_type'],
                groups=device_data.get('groups', []),
                enabled=device_data.get('enabled', True),
                username=username,
                password=password,
                port=device_data.get('port', 22),
                timeout=device_data.get('timeout', 30)
            )
            self.devices.append(device)
    
    def _load_settings(self):
        """Load application settings"""
        settings_file = self.config_dir / "settings.yaml"
        
        if not settings_file.exists():
            # Use defaults
            return
        
        with open(settings_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Backup settings
        backup_data = data.get('backup', {})
        self.backup = BackupSettings(
            repository_path=backup_data.get('repository_path', './backups/repo'),
            concurrent_backups=backup_data.get('concurrent_backups', 3),
            timeout_seconds=backup_data.get('timeout_seconds', 30),
            retry_attempts=backup_data.get('retry_attempts', 3),
            retry_delay_seconds=backup_data.get('retry_delay_seconds', 5)
        )
        
        # Schedule settings
        schedule_data = data.get('schedule', {})
        self.schedule = ScheduleSettings(
            enabled=schedule_data.get('enabled', False),
            cron_expression=schedule_data.get('cron_expression', '0 2 * * *')
        )
        
        # Notification settings
        notif_data = data.get('notifications', {})
        
        email_data = notif_data.get('email', {})
        email = EmailSettings(
            enabled=email_data.get('enabled', False),
            smtp_server=email_data.get('smtp_server', ''),
            smtp_port=email_data.get('smtp_port', 587),
            smtp_use_tls=email_data.get('smtp_use_tls', True),
            from_address=email_data.get('from_address', ''),
            to_addresses=email_data.get('to_addresses', []),
            username=os.getenv(email_data.get('username_env', ''), ''),
            password=os.getenv(email_data.get('password_env', ''), '')
        )
        
        slack_data = notif_data.get('slack', {})
        slack = SlackSettings(
            enabled=slack_data.get('enabled', False),
            webhook_url=os.getenv(slack_data.get('webhook_url_env', ''), '')
        )
        
        self.notifications = NotificationSettings(email=email, slack=slack)
        
        # Logging settings
        log_data = data.get('logging', {})
        self.logging = LoggingSettings(
            level=log_data.get('level', 'INFO'),
            file=log_data.get('file', './logs/netbackup.log'),
            console=log_data.get('console', True),
            max_bytes=log_data.get('max_bytes', 10485760),
            backup_count=log_data.get('backup_count', 5)
        )
    
    def get_enabled_devices(self) -> List[Device]:
        """Get list of enabled devices"""
        return [d for d in self.devices if d.enabled]
    
    def get_devices_by_group(self, group: str) -> List[Device]:
        """Get devices belonging to a specific group"""
        return [d for d in self.devices if group in d.groups and d.enabled]
    
    def get_device_by_name(self, name: str) -> Optional[Device]:
        """Get a specific device by name"""
        for device in self.devices:
            if device.name == name:
                return device
        return None