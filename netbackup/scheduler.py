"""
Job scheduling for automated backups
"""

import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from netbackup.config import Config
from netbackup.backup_engine import BackupEngine
from netbackup.notifier import Notifier

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Manages scheduled backup jobs"""
    
    def __init__(self, config: Config):
        """
        Initialize scheduler
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.scheduler = BlockingScheduler()
        self.backup_engine = BackupEngine(config)
        self.notifier = Notifier(config.notifications)
    
    def setup(self):
        """Set up scheduled jobs"""
        if not self.config.schedule.enabled:
            logger.warning("Scheduling is disabled in configuration")
            return False
        
        # Initialize backup system
        if not self.backup_engine.initialize():
            logger.error("Failed to initialize backup system")
            return False
        
        # Parse cron expression
        cron_parts = self.config.schedule.cron_expression.split()
        if len(cron_parts) != 5:
            logger.error(f"Invalid cron expression: {self.config.schedule.cron_expression}")
            return False
        
        minute, hour, day, month, day_of_week = cron_parts
        
        # Create cron trigger
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week
        )
        
        # Add job to scheduler
        self.scheduler.add_job(
            self._run_scheduled_backup,
            trigger=trigger,
            id='backup_job',
            name='Network Device Backup',
            replace_existing=True
        )
        
        logger.info(f"Scheduled backup job: {self.config.schedule.cron_expression}")
        return True
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.get_jobs():
            logger.error("No jobs scheduled. Run setup() first.")
            return
        
        logger.info("Starting backup scheduler...")
        logger.info("Press Ctrl+C to exit")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")
    
    def _run_scheduled_backup(self):
        """Execute scheduled backup job"""
        logger.info("Running scheduled backup...")
        
        try:
            # Run backup
            result = self.backup_engine.run_backup()
            
            # Generate report
            report = self.backup_engine.generate_report(result)
            
            # Send notifications
            self.notifier.send_notifications(result, report)
            
            logger.info("Scheduled backup completed")
            
        except Exception as e:
            logger.error(f"Error in scheduled backup: {str(e)}")
    
    def run_once(self):
        """Run backup once immediately (for testing)"""
        logger.info("Running one-time backup...")
        self._run_scheduled_backup()