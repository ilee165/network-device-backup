"""
Command-line interface for network backup system
"""

import sys
import click
from pathlib import Path

from netbackup.config import Config
from netbackup.backup_engine import BackupEngine
from netbackup.notifier import Notifier
from netbackup.scheduler import BackupScheduler
from netbackup.utils import setup_logging, create_summary_table


@click.group()
@click.option('--config-dir', default='./config', help='Configuration directory path')
@click.pass_context
def cli(ctx, config_dir):
    """Network Device Backup System - Automated configuration backup with Git versioning"""
    ctx.ensure_object(dict)
    ctx.obj['config_dir'] = config_dir


@cli.command()
@click.option('--device', help='Backup specific device by name')
@click.option('--group', help='Backup devices in specific group')
@click.pass_context
def run(ctx, device, group):
    """Run backup operation"""
    config_dir = ctx.obj['config_dir']
    
    try:
        # Load configuration
        config = Config(config_dir)
        config.load()
        
        # Setup logging
        setup_logging(config.logging)
        
        # Initialize backup engine
        engine = BackupEngine(config)
        
        # Initialize system
        if not engine.initialize():
            click.echo("Failed to initialize backup system", err=True)
            sys.exit(1)
        
        # Run backup
        click.echo("Starting backup operation...")
        result = engine.run_backup(device_filter=device, group_filter=group)
        
        # Generate and display report
        report = engine.generate_report(result)
        click.echo("\n" + report)
        
        # Send notifications if configured
        notifier = Notifier(config.notifications)
        notifier.send_notifications(result, report)
        
        # Exit with appropriate code
        if result.failed > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except FileNotFoundError as e:
        click.echo(f"Configuration error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--device', help='Test specific device')
@click.pass_context
def test(ctx, device):
    """Test device connections"""
    config_dir = ctx.obj['config_dir']
    
    try:
        # Load configuration
        config = Config(config_dir)
        config.load()
        
        # Setup logging
        setup_logging(config.logging)
        
        # Initialize backup engine
        engine = BackupEngine(config)
        
        if device:
            # Test specific device
            click.echo(f"Testing connection to {device}...")
            success = engine.test_device(device)
            sys.exit(0 if success else 1)
        else:
            # Test all devices
            click.echo("Testing connections to all enabled devices...")
            results = engine.test_all_devices()
            
            # Display results
            click.echo(f"\nResults: {results['successful']}/{results['total']} successful\n")
            
            # Show details
            for device_name, success in results['devices'].items():
                status = "✓" if success else "✗"
                click.echo(f"  {status} {device_name}")
            
            sys.exit(0 if results['failed'] == 0 else 1)
            
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show backup status for all devices"""
    config_dir = ctx.obj['config_dir']
    
    try:
        # Load configuration
        config = Config(config_dir)
        config.load()
        
        # Setup logging
        setup_logging(config.logging)
        
        # Initialize backup engine
        engine = BackupEngine(config)
        engine.initialize()
        
        # Get status for all devices
        devices = config.get_enabled_devices()
        
        click.echo(f"\nBackup Status for {len(devices)} device(s):\n")
        
        # Prepare table data
        headers = ["Device", "Hostname", "Groups", "Last Backup", "Status"]
        rows = []
        
        for device in devices:
            status_info = engine.get_device_status(device.name)
            
            if status_info:
                last_backup = status_info['last_backup']
                if last_backup:
                    last_backup_str = last_backup.strftime('%Y-%m-%d %H:%M')
                    status_str = "✓"
                else:
                    last_backup_str = "Never"
                    status_str = "○"
                
                groups_str = ", ".join(status_info['groups'][:2])
                if len(status_info['groups']) > 2:
                    groups_str += "..."
                
                rows.append([
                    device.name,
                    device.hostname,
                    groups_str,
                    last_backup_str,
                    status_str
                ])
        
        # Display table
        table = create_summary_table(headers, rows)
        click.echo(table)
        click.echo()
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('device')
@click.option('--limit', default=10, help='Number of history entries to show')
@click.pass_context
def history(ctx, device, limit):
    """Show backup history for a device"""
    config_dir = ctx.obj['config_dir']
    
    try:
        # Load configuration
        config = Config(config_dir)
        config.load()
        
        # Setup logging
        setup_logging(config.logging)
        
        # Initialize backup engine
        engine = BackupEngine(config)
        engine.initialize()
        
        # Get device status
        status_info = engine.get_device_status(device)
        
        if not status_info:
            click.echo(f"Device not found: {device}", err=True)
            sys.exit(1)
        
        click.echo(f"\nBackup History for {device}:\n")
        
        history_entries = status_info['recent_history']
        
        if not history_entries:
            click.echo("No backup history found")
            return
        
        # Display history
        for entry in history_entries[:limit]:
            click.echo(f"  {entry['date'].strftime('%Y-%m-%d %H:%M:%S')} - {entry['hash']}")
            click.echo(f"    {entry['message']}")
            click.echo()
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('device')
@click.pass_context
def diff(ctx, device):
    """Show latest config changes for a device"""
    config_dir = ctx.obj['config_dir']
    
    try:
        # Load configuration
        config = Config(config_dir)
        config.load()
        
        # Setup logging
        setup_logging(config.logging)
        
        # Initialize backup engine
        engine = BackupEngine(config)
        engine.initialize()
        
        # Get diff
        diff_text = engine.git_manager.get_diff(device)
        
        if not diff_text:
            click.echo(f"No recent changes found for {device}")
            return
        
        click.echo(f"\nLatest Changes for {device}:\n")
        click.echo(diff_text)
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def list_devices(ctx):
    """List all configured devices"""
    config_dir = ctx.obj['config_dir']
    
    try:
        # Load configuration
        config = Config(config_dir)
        config.load()
        
        click.echo(f"\nConfigured Devices ({len(config.devices)}):\n")
        
        # Prepare table
        headers = ["Name", "Hostname", "Type", "Groups", "Enabled"]
        rows = []
        
        for device in config.devices:
            groups_str = ", ".join(device.groups[:2])
            if len(device.groups) > 2:
                groups_str += "..."
            
            enabled_str = "Yes" if device.enabled else "No"
            
            rows.append([
                device.name,
                device.hostname,
                device.device_type,
                groups_str,
                enabled_str
            ])
        
        table = create_summary_table(headers, rows)
        click.echo(table)
        click.echo()
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--daemon', is_flag=True, help='Run as daemon')
@click.pass_context
def schedule(ctx, daemon):
    """Start scheduled backup jobs"""
    config_dir = ctx.obj['config_dir']
    
    try:
        # Load configuration
        config = Config(config_dir)
        config.load()
        
        # Setup logging
        setup_logging(config.logging)
        
        # Initialize scheduler
        scheduler = BackupScheduler(config)
        
        if not scheduler.setup():
            click.echo("Failed to setup scheduler", err=True)
            sys.exit(1)
        
        if daemon:
            # Run as daemon (blocking)
            click.echo("Starting scheduler daemon...")
            scheduler.start()
        else:
            # Run once for testing
            click.echo("Running one-time scheduled backup...")
            scheduler.run_once()
        
    except KeyboardInterrupt:
        click.echo("\nScheduler stopped")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--repo-path', default='./backups/repo', help='Repository path')
@click.pass_context
def init(ctx, repo_path):
    """Initialize new backup repository"""
    config_dir = ctx.obj['config_dir']
    
    try:
        click.echo(f"Initializing backup system...")
        
        # Create config directory if needed
        config_path = Path(config_dir)
        config_path.mkdir(parents=True, exist_ok=True)
        
        # Copy example configs if they don't exist
        devices_file = config_path / "devices.yaml"
        settings_file = config_path / "settings.yaml"
        
        if not devices_file.exists():
            example_devices = config_path.parent / "config" / "devices.yaml.example"
            if example_devices.exists():
                import shutil
                shutil.copy(example_devices, devices_file)
                click.echo(f"Created {devices_file}")
            else:
                click.echo(f"Warning: Could not find devices.yaml.example", err=True)
        
        if not settings_file.exists():
            example_settings = config_path.parent / "config" / "settings.yaml.example"
            if example_settings.exists():
                import shutil
                shutil.copy(example_settings, settings_file)
                click.echo(f"Created {settings_file}")
            else:
                click.echo(f"Warning: Could not find settings.yaml.example", err=True)
        
        # Load minimal config for initialization
        from netbackup.config import BackupSettings
        from netbackup.git_manager import GitManager
        
        backup_settings = BackupSettings(repository_path=repo_path)
        git_manager = GitManager(backup_settings.repository_path)
        
        if git_manager.initialize_repo():
            click.echo(f"✓ Initialized Git repository at {repo_path}")
        else:
            click.echo("✗ Failed to initialize Git repository", err=True)
            sys.exit(1)
        
        # Create logs directory
        logs_dir = Path("./logs")
        logs_dir.mkdir(exist_ok=True)
        click.echo(f"✓ Created logs directory at {logs_dir}")
        
        click.echo("\nSetup complete!")
        click.echo("\nNext steps:")
        click.echo(f"  1. Edit {devices_file} to add your devices")
        click.echo(f"  2. Edit {settings_file} to configure settings")
        click.echo("  3. Set environment variables: NET_USERNAME, NET_PASSWORD")
        click.echo("  4. Test connections: netbackup test")
        click.echo("  5. Run your first backup: netbackup run")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--email', is_flag=True, help='Test email notifications')
@click.option('--slack', is_flag=True, help='Test Slack notifications')
@click.pass_context
def test_notifications(ctx, email, slack):
    """Test notification configuration"""
    config_dir = ctx.obj['config_dir']
    
    try:
        # Load configuration
        config = Config(config_dir)
        config.load()
        
        # Setup logging
        setup_logging(config.logging)
        
        notifier = Notifier(config.notifications)
        
        if email:
            click.echo("Sending test email...")
            if notifier.send_test_email():
                click.echo("✓ Test email sent successfully")
            else:
                click.echo("✗ Failed to send test email", err=True)
                sys.exit(1)
        
        if slack:
            click.echo("Sending test Slack message...")
            if notifier.send_test_slack():
                click.echo("✓ Test Slack message sent successfully")
            else:
                click.echo("✗ Failed to send test Slack message", err=True)
                sys.exit(1)
        
        if not email and not slack:
            click.echo("Please specify --email or --slack", err=True)
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


def main():
    """Main entry point"""
    cli(obj={})


if __name__ == '__main__':
    main()