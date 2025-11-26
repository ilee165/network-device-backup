"""
Network device connection and configuration retrieval
"""

import logging
import time
from typing import Optional
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

logger = logging.getLogger(__name__)


class DeviceManager:
    """Manages connection and communication with network devices"""
    
    def __init__(self, device):
        """
        Initialize device manager
        
        Args:
            device: Device configuration object
        """
        self.device = device
        self.connection = None
        self._connected = False
        
    def connect(self, retry_attempts: int = 3, retry_delay: int = 5) -> bool:
        """
        Establish SSH connection to device
        
        Args:
            retry_attempts: Number of connection attempts
            retry_delay: Seconds to wait between retries
            
        Returns:
            True if connection successful, False otherwise
        """
        device_params = {
            'device_type': self.device.device_type,
            'host': self.device.hostname,
            'username': self.device.username,
            'password': self.device.password,
            'port': self.device.port,
            'timeout': self.device.timeout,
            'session_log': None,  # Can enable for debugging
        }
        
        for attempt in range(1, retry_attempts + 1):
            try:
                logger.info(f"Connecting to {self.device.name} ({self.device.hostname}) - Attempt {attempt}/{retry_attempts}")
                self.connection = ConnectHandler(**device_params)
                self._connected = True
                logger.info(f"Successfully connected to {self.device.name}")
                return True
                
            except NetmikoAuthenticationException as e:
                logger.error(f"Authentication failed for {self.device.name}: {str(e)}")
                # Don't retry on auth failures
                return False
                
            except NetmikoTimeoutException as e:
                logger.warning(f"Connection timeout for {self.device.name} (attempt {attempt}/{retry_attempts}): {str(e)}")
                if attempt < retry_attempts:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to connect to {self.device.name} after {retry_attempts} attempts")
                    return False
                    
            except Exception as e:
                logger.error(f"Unexpected error connecting to {self.device.name}: {str(e)}")
                if attempt < retry_attempts:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    return False
        
        return False
    
    def get_config(self) -> Optional[str]:
        """
        Retrieve running configuration from device
        
        Returns:
            Configuration as string, or None if failed
        """
        if not self._connected or not self.connection:
            logger.error(f"Not connected to {self.device.name}")
            return None
        
        try:
            logger.info(f"Retrieving configuration from {self.device.name}")
            
            # Different commands for different device types
            if 'cisco_ios' in self.device.device_type:
                config = self.connection.send_command('show running-config')
            elif 'juniper' in self.device.device_type:
                config = self.connection.send_command('show configuration')
            elif 'arista' in self.device.device_type:
                config = self.connection.send_command('show running-config')
            elif 'hp_comware' in self.device.device_type or 'aruba' in self.device.device_type:
                config = self.connection.send_command('display current-configuration')
            else:
                # Default to show running-config for unknown types
                config = self.connection.send_command('show running-config')
            
            if not config or len(config.strip()) == 0:
                logger.error(f"Retrieved empty configuration from {self.device.name}")
                return None
            
            logger.info(f"Successfully retrieved {len(config)} bytes from {self.device.name}")
            return config
            
        except Exception as e:
            logger.error(f"Error retrieving config from {self.device.name}: {str(e)}")
            return None
    
    def disconnect(self):
        """Close connection to device"""
        if self.connection and self._connected:
            try:
                self.connection.disconnect()
                logger.info(f"Disconnected from {self.device.name}")
            except Exception as e:
                logger.warning(f"Error disconnecting from {self.device.name}: {str(e)}")
            finally:
                self._connected = False
                self.connection = None
    
    def test_connection(self) -> bool:
        """
        Test connection to device without retrieving config
        
        Returns:
            True if connection successful, False otherwise
        """
        success = self.connect(retry_attempts=1)
        if success:
            self.disconnect()
        return success
    
    def __enter__(self):
        """Context manager entry"""
        if self.connect():
            return self
        raise ConnectionError(f"Failed to connect to {self.device.name}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()