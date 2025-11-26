# Network Device Backup System

Automated network device configuration backup with Git versioning, change tracking, and notifications.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)

## Features

- 🔄 **Automated Backups** - Schedule backups or run on-demand
- 📝 **Git Versioning** - Full version history of all configuration changes
- 🔍 **Change Detection** - Automatically detect and report configuration changes
- 📧 **Notifications** - Email and Slack notifications with detailed reports
- 🚀 **Multi-vendor Support** - Cisco, Juniper, Arista, HP, and more
- ⚡ **Concurrent Processing** - Backup multiple devices simultaneously
- 🔐 **Secure** - Credential management via environment variables
- 📊 **Detailed Reporting** - Comprehensive backup reports with diffs

## Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/dw-solution/network-device-backup.git
cd network-device-backup

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Initial Setup
```bash
# Initialize the backup system
netbackup init

# Set your credentials
export NET_USERNAME="your-username"
export NET_PASSWORD="your-password"

# Edit configuration files
nano config/devices.yaml
nano config/settings.yaml
```

### First Backup
```bash
# Test device connections
netbackup test

# Run your first backup
netbackup run

# View backup status
netbackup status
```

## Usage

### Basic Commands
```bash
# Run backup for all devices
netbackup run

# Backup specific device
netbackup run --device core-switch-01

# Backup devices in a group
netbackup run --group datacenter

# Test connections
netbackup test
netbackup test --device core-switch-01

# View backup status
netbackup status

# Show backup history
netbackup history core-switch-01

# View configuration changes
netbackup diff core-switch-01

# List all devices
netbackup list-devices

# Start scheduler daemon
netbackup schedule --daemon

# Test notifications
netbackup test-notifications --email
netbackup test-notifications --slack
```

## Configuration

### Device Configuration

Edit `config/devices.yaml`:
```yaml
devices:
  - name: core-switch-01
    hostname: 10.0.1.10
    device_type: cisco_ios
    groups:
      - core
      - datacenter
    enabled: true

credentials:
  default:
    username_env: NET_USERNAME
    password_env: NET_PASSWORD
```

### Application Settings

Edit `config/settings.yaml`:
```yaml
backup:
  repository_path: ./backups/repo
  concurrent_backups: 5
  timeout_seconds: 30

schedule:
  enabled: true
  cron_expression: "0 2 * * *"  # 2 AM daily

notifications:
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    from_address: backup@company.com
    to_addresses:
      - admin@company.com
```

## Supported Devices

- Cisco IOS / IOS-XE / IOS-XR / NX-OS
- Juniper JunOS
- Arista EOS
- HP Comware / ProCurve
- Palo Alto PAN-OS
- Fortinet FortiOS
- MikroTik RouterOS
- And many more via Netmiko

## Architecture
```
┌─────────────────────────────────────┐
│      Backup Orchestrator            │
│   ┌──────────┐  ┌──────────────┐   │
│   │Scheduler │→ │Backup Engine │   │
│   └──────────┘  └──────────────┘   │
└─────────────────────────────────────┘
         ↓                    ↓
┌─────────────────┐  ┌─────────────────┐
│ Device Manager  │  │  Git Repository │
│   (Netmiko)     │  │   (GitPython)   │
└─────────────────┘  └─────────────────┘
         ↓
┌─────────────────┐
│Network Devices  │
└─────────────────┘
```

## Use Cases

1. **Automated Compliance** - Maintain audit trail of all configuration changes
2. **Disaster Recovery** - Quick config restoration from Git history
3. **Change Management** - Track who changed what and when
4. **Multi-site Management** - Centralized backup for distributed networks
5. **Security Auditing** - Monitor unauthorized configuration changes

## Requirements

- Python 3.9 or higher
- SSH access to network devices
- Git installed on the system
- Network connectivity to devices

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/dw-solution/network-device-backup/issues
- Email: contact@dwsolution.com

## About DW Solution

Professional network automation and infrastructure services.

---

**Made with ❤️ by DW Solution**