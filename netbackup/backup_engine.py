"""
Main backup orchestration engine
"""

import logging
import time
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from netbackup.config import Config, Device
from netbackup.device_manager import DeviceManager
from netbackup.git_manager import GitManager

logger = logging.getLogger(__name__)


@dataclass
class DeviceBackupResult:
    """Result of backing up a single device"""
    device_name: str
    hostname: str
    success: bool
    config_changed: bool = False
    config_size: int = 0
    diff: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BackupResult:
    """Overall backup operation result"""
    total_devices: int
    successful: int
    failed: int
    changed: int
    unchanged: int
    device_results: List[DeviceBackupResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    def add_result(self, result: DeviceBackupResult):
        """Add a device result and update counters"""
        self.device_results.append(result)
        
        if result.success:
            self.successful += 1
            if result.config_changed:
                self.changed += 1
            else:
                self.unchanged += 1
        else:
            self.failed += 1
    
    def finalize(self):
        """Finalize the backup result with timing"""
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()


class BackupEngine:
    """Main backup orchestration engine"""
    
    def __init__(self, config: Config):
        """
        Initialize backup engine
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.git_manager = GitManager(config.backup.repository_path)
        
    def initialize(self) -> bool:
        """
        Initialize backup system (Git repo, directories, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Initializing backup system...")
        
        # Initialize Git repository
        if not self.git_manager.initialize_repo():
            logger.error("Failed to initialize Git repository")
            return False
        
        logger.info("Backup system initialized successfully")
        return True
    
    def run_backup(self, 
                   device_filter: Optional[str] = None,
                   group_filter: Optional[str] = None) -> BackupResult:
        """
        Run backup operation for devices
        
        Args:
            device_filter: Optional device name to backup only that device
            group_filter: Optional group name to backup only devices in that group
            
        Returns:
            BackupResult with operation results
        """
        # Determine which devices to backup
        if device_filter:
            device = self.config.get_device_by_name(device_filter)
            devices = [device] if device else []
            if not device:
                logger.error(f"Device not found: {device_filter}")
        elif group_filter:
            devices = self.config.get_devices_by_group(group_filter)
            if not devices:
                logger.warning(f"No devices found in group: {group_filter}")
        else:
            devices = self.config.get_enabled_devices()
        
        if not devices:
            logger.error("No devices to backup")
            return BackupResult(total_devices=0, successful=0, failed=0, changed=0, unchanged=0)
        
        logger.info(f"Starting backup for {len(devices)} device(s)")
        
        # Initialize result
        result = BackupResult(
            total_devices=len(devices),
            successful=0,
            failed=0,
            changed=0,
            unchanged=0
        )
        
        # Backup devices concurrently
        max_workers = min(self.config.backup.concurrent_backups, len(devices))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all backup jobs
            future_to_device = {
                executor.submit(self._backup_device, device): device 
                for device in devices
            }
            
            # Process completed backups
            for future in as_completed(future_to_device):
                device = future_to_device[future]
                try:
                    device_result = future.result()
                    result.add_result(device_result)
                    
                    # Log result
                    if device_result.success:
                        status = "CHANGED" if device_result.config_changed else "UNCHANGED"
                        logger.info(f"✓ {device.name}: {status} ({device_result.duration_seconds:.1f}s)")
                    else:
                        logger.error(f"✗ {device.name}: FAILED - {device_result.error_message}")
                        
                except Exception as e:
                    logger.error(f"Unexpected error backing up {device.name}: {str(e)}")
                    result.add_result(DeviceBackupResult(
                        device_name=device.name,
                        hostname=device.hostname,
                        success=False,
                        error_message=f"Unexpected error: {str(e)}"
                    ))
        
        # Finalize results
        result.finalize()
        
        # Log summary
        logger.info(f"\n{'='*60}")
        logger.info(f"Backup completed in {result.duration_seconds:.1f} seconds")
        logger.info(f"Total: {result.total_devices} | "
                   f"Success: {result.successful} | "
                   f"Failed: {result.failed}")
        logger.info(f"Changed: {result.changed} | "
                   f"Unchanged: {result.unchanged}")
        logger.info(f"{'='*60}\n")
        
        return result
    
    def _backup_device(self, device: Device) -> DeviceBackupResult:
        """
        Backup a single device
        
        Args:
            device: Device to backup
            
        Returns:
            DeviceBackupResult
        """
        start_time = time.time()
        result = DeviceBackupResult(
            device_name=device.name,
            hostname=device.hostname,
            success=False
        )
        
        device_manager = None
        
        try:
            # Connect to device
            device_manager = DeviceManager(device)
            if not device_manager.connect(
                retry_attempts=self.config.backup.retry_attempts,
                retry_delay=self.config.backup.retry_delay_seconds
            ):
                result.error_message = "Failed to connect to device"
                result.duration_seconds = time.time() - start_time
                return result
            
            # Retrieve configuration
            config = device_manager.get_config()
            if not config:
                result.error_message = "Failed to retrieve configuration"
                result.duration_seconds = time.time() - start_time
                return result
            
            result.config_size = len(config)
            
            # Check if config has changed
            has_changes = self.git_manager.has_changes(device.name, config)
            result.config_changed = has_changes
            
            if has_changes:
                # Save configuration
                success, file_path = self.git_manager.save_config(
                    device.name, 
                    config,
                    datetime.now()
                )
                
                if not success:
                    result.error_message = "Failed to save configuration"
                    result.duration_seconds = time.time() - start_time
                    return result
                
                # Commit changes
                commit_message = f"Backup: {device.name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                if not self.git_manager.commit_changes(device.name, commit_message):
                    result.error_message = "Failed to commit changes"
                    result.duration_seconds = time.time() - start_time
                    return result
                
                # Get diff
                diff = self.git_manager.get_diff(device.name)
                result.diff = diff
                
                logger.debug(f"Configuration changed for {device.name}")
            else:
                logger.debug(f"No changes detected for {device.name}")
            
            # Success!
            result.success = True
            result.duration_seconds = time.time() - start_time
            
        except Exception as e:
            logger.error(f"Error backing up {device.name}: {str(e)}")
            result.error_message = str(e)
            result.duration_seconds = time.time() - start_time
            
        finally:
            # Always disconnect
            if device_manager:
                device_manager.disconnect()
        
        return result
    
    def test_device(self, device_name: str) -> bool:
        """
        Test connection to a specific device
        
        Args:
            device_name: Name of device to test
            
        Returns:
            True if connection successful, False otherwise
        """
        device = self.config.get_device_by_name(device_name)
        if not device:
            logger.error(f"Device not found: {device_name}")
            return False
        
        logger.info(f"Testing connection to {device.name} ({device.hostname})...")
        
        device_manager = DeviceManager(device)
        success = device_manager.test_connection()
        
        if success:
            logger.info(f"✓ Successfully connected to {device.name}")
        else:
            logger.error(f"✗ Failed to connect to {device.name}")
        
        return success
    
    def test_all_devices(self) -> dict:
        """
        Test connections to all enabled devices
        
        Returns:
            Dictionary with test results
        """
        devices = self.config.get_enabled_devices()
        results = {
            'total': len(devices),
            'successful': 0,
            'failed': 0,
            'devices': {}
        }
        
        logger.info(f"Testing connections to {len(devices)} device(s)...")
        
        for device in devices:
            success = self.test_device(device.name)
            results['devices'][device.name] = success
            
            if success:
                results['successful'] += 1
            else:
                results['failed'] += 1
        
        logger.info(f"\nTest Summary: {results['successful']}/{results['total']} successful")
        
        return results
    
    def get_device_status(self, device_name: str) -> Optional[dict]:
        """
        Get backup status for a device
        
        Args:
            device_name: Name of device
            
        Returns:
            Dictionary with status information
        """
        device = self.config.get_device_by_name(device_name)
        if not device:
            return None
        
        last_backup = self.git_manager.get_last_backup_time(device_name)
        history = self.git_manager.get_history(device_name, limit=5)
        
        return {
            'device_name': device_name,
            'hostname': device.hostname,
            'enabled': device.enabled,
            'groups': device.groups,
            'last_backup': last_backup,
            'backup_count': len(history),
            'recent_history': history
        }
    
    def generate_report(self, result: BackupResult) -> str:
        """
        Generate a human-readable report from backup results
        
        Args:
            result: BackupResult to generate report from
            
        Returns:
            Formatted report as string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("NETWORK DEVICE BACKUP REPORT")
        lines.append("=" * 70)
        lines.append(f"Start Time: {result.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"End Time: {result.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Duration: {result.duration_seconds:.1f} seconds")
        lines.append("")
        lines.append("SUMMARY")
        lines.append("-" * 70)
        lines.append(f"Total Devices:    {result.total_devices}")
        lines.append(f"Successful:       {result.successful}")
        lines.append(f"Failed:           {result.failed}")
        lines.append(f"Changed:          {result.changed}")
        lines.append(f"Unchanged:        {result.unchanged}")
        lines.append("")
        
        # Changed devices
        if result.changed > 0:
            lines.append("CHANGED CONFIGURATIONS")
            lines.append("-" * 70)
            for device_result in result.device_results:
                if device_result.success and device_result.config_changed:
                    lines.append(f"  • {device_result.device_name} ({device_result.hostname})")
                    lines.append(f"    Size: {device_result.config_size} bytes")
                    lines.append(f"    Duration: {device_result.duration_seconds:.1f}s")
                    
                    if device_result.diff:
                        lines.append(f"    Changes detected (showing first 500 chars):")
                        diff_preview = device_result.diff[:500]
                        for line in diff_preview.split('\n'):
                            lines.append(f"      {line}")
                    lines.append("")
        
        # Unchanged devices
        if result.unchanged > 0:
            lines.append("UNCHANGED CONFIGURATIONS")
            lines.append("-" * 70)
            for device_result in result.device_results:
                if device_result.success and not device_result.config_changed:
                    lines.append(f"  • {device_result.device_name} ({device_result.hostname})")
            lines.append("")
        
        # Failed devices
        if result.failed > 0:
            lines.append("FAILED BACKUPS")
            lines.append("-" * 70)
            for device_result in result.device_results:
                if not device_result.success:
                    lines.append(f"  • {device_result.device_name} ({device_result.hostname})")
                    lines.append(f"    Error: {device_result.error_message}")
                    lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)