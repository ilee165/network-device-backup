"""
Notification handling for backup results
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import requests

from netbackup.config import NotificationSettings
from netbackup.backup_engine import BackupResult

logger = logging.getLogger(__name__)


class Notifier:
    """Handles sending notifications via email and Slack"""
    
    def __init__(self, settings: NotificationSettings):
        """
        Initialize notifier
        
        Args:
            settings: Notification configuration
        """
        self.settings = settings
    
    def send_notifications(self, result: BackupResult, report: str):
        """
        Send all configured notifications
        
        Args:
            result: Backup result
            report: Formatted report text
        """
        if self.settings.email.enabled:
            self._send_email(result, report)
        
        if self.settings.slack.enabled:
            self._send_slack(result, report)
    
    def _send_email(self, result: BackupResult, report: str):
        """
        Send email notification
        
        Args:
            result: Backup result
            report: Formatted report text
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.settings.email.from_address
            msg['To'] = ', '.join(self.settings.email.to_addresses)
            
            # Determine subject based on results
            if result.failed > 0:
                status = "⚠️  FAILED"
            elif result.changed > 0:
                status = "✓ SUCCESS (Changes Detected)"
            else:
                status = "✓ SUCCESS (No Changes)"
            
            msg['Subject'] = f"Network Backup Report - {status}"
            
            # Create email body
            body = self._format_email_body(result, report)
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.settings.email.smtp_server, self.settings.email.smtp_port) as server:
                if self.settings.email.smtp_use_tls:
                    server.starttls()
                
                if self.settings.email.username and self.settings.email.password:
                    server.login(self.settings.email.username, self.settings.email.password)
                
                server.send_message(msg)
            
            logger.info("Email notification sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
    
    def _send_slack(self, result: BackupResult, report: str):
        """
        Send Slack notification
        
        Args:
            result: Backup result
            report: Formatted report text
        """
        try:
            # Determine emoji and color based on results
            if result.failed > 0:
                emoji = "⚠️"
                color = "#ff9900"  # Orange
            elif result.changed > 0:
                emoji = "✓"
                color = "#36a64f"  # Green
            else:
                emoji = "✓"
                color = "#808080"  # Gray
            
            # Create Slack message
            message = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"{emoji} Network Backup Report",
                        "fields": [
                            {
                                "title": "Total Devices",
                                "value": str(result.total_devices),
                                "short": True
                            },
                            {
                                "title": "Successful",
                                "value": str(result.successful),
                                "short": True
                            },
                            {
                                "title": "Failed",
                                "value": str(result.failed),
                                "short": True
                            },
                            {
                                "title": "Changed",
                                "value": str(result.changed),
                                "short": True
                            },
                            {
                                "title": "Duration",
                                "value": f"{result.duration_seconds:.1f}s",
                                "short": True
                            }
                        ],
                        "footer": "Network Backup System",
                        "ts": int(result.start_time.timestamp())
                    }
                ]
            }
            
            # Add failed devices if any
            if result.failed > 0:
                failed_devices = [
                    dr.device_name for dr in result.device_results if not dr.success
                ]
                message["attachments"].append({
                    "color": "#ff0000",
                    "title": "Failed Devices",
                    "text": ", ".join(failed_devices)
                })
            
            # Send to Slack
            response = requests.post(
                self.settings.slack.webhook_url,
                json=message,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info("Slack notification sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
    
    def _format_email_body(self, result: BackupResult, report: str) -> str:
        """
        Format email body
        
        Args:
            result: Backup result
            report: Formatted report text
            
        Returns:
            Email body as string
        """
        lines = []
        lines.append("Network Device Backup Report")
        lines.append("=" * 70)
        lines.append("")
        
        # Quick summary
        lines.append("QUICK SUMMARY")
        lines.append("-" * 70)
        lines.append(f"Total Devices:    {result.total_devices}")
        lines.append(f"Successful:       {result.successful}")
        lines.append(f"Failed:           {result.failed}")
        lines.append(f"Changed:          {result.changed}")
        lines.append(f"Unchanged:        {result.unchanged}")
        lines.append(f"Duration:         {result.duration_seconds:.1f}s")
        lines.append("")
        
        # Add full report
        lines.append("")
        lines.append("DETAILED REPORT")
        lines.append("-" * 70)
        lines.append(report)
        
        # Footer
        lines.append("")
        lines.append("-" * 70)
        lines.append("This is an automated message from the Network Backup System")
        lines.append("DW Solution - Network Automation Services")
        
        return "\n".join(lines)
    
    def send_test_email(self) -> bool:
        """
        Send a test email to verify configuration
        
        Returns:
            True if successful, False otherwise
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.settings.email.from_address
            msg['To'] = ', '.join(self.settings.email.to_addresses)
            msg['Subject'] = "Network Backup System - Test Email"
            
            body = "This is a test email from the Network Backup System.\n\n"
            body += "If you received this, your email configuration is working correctly.\n\n"
            body += "DW Solution - Network Automation Services"
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.settings.email.smtp_server, self.settings.email.smtp_port) as server:
                if self.settings.email.smtp_use_tls:
                    server.starttls()
                
                if self.settings.email.username and self.settings.email.password:
                    server.login(self.settings.email.username, self.settings.email.password)
                
                server.send_message(msg)
            
            logger.info("Test email sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send test email: {str(e)}")
            return False
    
    def send_test_slack(self) -> bool:
        """
        Send a test message to Slack
        
        Returns:
            True if successful, False otherwise
        """
        try:
            message = {
                "text": "✓ Network Backup System - Test Message",
                "attachments": [
                    {
                        "color": "#36a64f",
                        "text": "If you received this, your Slack configuration is working correctly.",
                        "footer": "DW Solution - Network Automation Services"
                    }
                ]
            }
            
            response = requests.post(
                self.settings.slack.webhook_url,
                json=message,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info("Test Slack message sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send test Slack message: {str(e)}")
            return False