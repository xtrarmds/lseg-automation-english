# LSEG Automation Program - English Version

## Overview

This is an automated program for LSEG (London Stock Exchange Group) data download and processing. The program automatically logs into the LSEG website, downloads RIC change data, filters AU records, and uploads the processed files to an SFTP server.

## Features

- **Automated Login**: Automatic login to LSEG website using configured credentials
- **Smart Download**: Intelligent download completion detection
- **Data Processing**: Filters AU records from downloaded Excel files
- **SFTP Upload**: Automatic upload of processed files to remote server
- **Email Notifications**: Email reports for successful/failed operations
- **Retry Mechanism**: Automatic retry on failures with configurable intervals
- **Duplicate Prevention**: Prevents duplicate daily executions
- **Comprehensive Logging**: Detailed logging for troubleshooting

## File Structure

```
├── lseg_login_english.py          # Main automation script (English version)
├── lseg_login_simple.py           # Main automation script (Chinese version)
├── start_lseg_automation.bat      # Windows batch startup script (English)
├── start_lseg_automation.ps1      # PowerShell startup script (English)
├── 启动LSEG自动化.bat             # Windows batch startup script (Chinese)
├── 启动LSEG自动化.ps1             # PowerShell startup script (Chinese)
├── config.cnf                     # Configuration file
├── requirements.txt               # Python dependencies
├── README_ENGLISH.md             # This documentation (English)
├── 项目文件说明.md                # Documentation (Chinese)
├── logs/                         # Log files directory
├── downloads/                    # Downloaded files directory
├── target/                       # Processed files directory
└── drivers/                      # Chrome driver directory
```

## Prerequisites

### System Requirements
- Windows 10/11
- Python 3.7 or higher
- Chrome browser
- Internet connection

### Python Dependencies
- selenium
- pandas
- paramiko
- configparser
- smtplib (built-in)

## Installation

### Method 1: Using Batch Script (Recommended)
1. Double-click `start_lseg_automation.bat`
2. The script will automatically:
   - Check Python installation
   - Create virtual environment
   - Install dependencies
   - Create necessary directories
   - Start the automation program

### Method 2: Using PowerShell Script
1. Right-click `start_lseg_automation.ps1`
2. Select "Run with PowerShell"
3. Follow the same automatic setup process

### Method 3: Manual Installation
1. Install Python 3.7+ from https://www.python.org/downloads/
2. Open command prompt in project directory
3. Create virtual environment: `python -m venv .venv`
4. Activate virtual environment: `.venv\Scripts\activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Run program: `python lseg_login_english.py`

## Configuration

### Configuration File (config.cnf)

Create a `config.cnf` file with the following structure:

```ini
[lseg_login]
username = your_lseg_username
password = your_lseg_password

[paths]
downloads_path = downloads
target_dir = target
target_file = your_target_filename.xlsx

[sftp]
host = your_sftp_host
username = your_sftp_username
password = your_sftp_password
remote_dir = /path/to/remote/directory

[email]
smtp_server = smtp.163.com
smtp_port = 465
sender = your_email@163.com
password = your_email_password_or_auth_code
recipient = recipient@example.com
enable_email = true
```

### Configuration Details

#### LSEG Login Section
- `username`: Your LSEG account username
- `password`: Your LSEG account password

#### Paths Section
- `downloads_path`: Directory for downloaded files (relative to project)
- `target_dir`: Directory for processed files (relative to project)
- `target_file`: Expected filename of downloaded file

#### SFTP Section
- `host`: SFTP server hostname or IP
- `username`: SFTP server username
- `password`: SFTP server password
- `remote_dir`: Remote directory path on SFTP server

#### Email Section
- `smtp_server`: SMTP server (163 email recommended)
- `smtp_port`: SMTP port (465 for SSL)
- `sender`: Sender email address
- `password`: Email password or authorization code
- `recipient`: Recipient email address
- `enable_email`: Enable/disable email notifications

## Usage

### Starting the Program

#### Option 1: Batch Script (Easiest)
```cmd
start_lseg_automation.bat
```

#### Option 2: PowerShell Script
```powershell
.\start_lseg_automation.ps1
```

#### Option 3: Direct Python Execution
```cmd
python lseg_login_english.py
```

### Program Workflow

1. **Environment Check**: Verifies Python, virtual environment, and dependencies
2. **Duplicate Check**: Checks if already executed today
3. **Browser Launch**: Starts Chrome browser with optimized settings
4. **Login Process**: 
   - Navigates to LSEG login page
   - Enters credentials
   - Handles cookie popups
   - Accepts terms and conditions
5. **Data Download**: Waits for file download completion
6. **Data Processing**: 
   - Filters AU records from Excel file
   - Creates new file with filtered data
7. **SFTP Upload**: Uploads processed file to remote server
8. **Email Report**: Sends success/failure notification
9. **Cleanup**: Removes temporary files

### Log Files

Log files are created in the `logs/` directory with the format:
- `lseg_automation_YYYYMMDD.log`

Log files contain:
- Program execution status
- Error messages and stack traces
- Performance metrics
- Email notification records

## Troubleshooting

### Common Issues

#### 1. Python Not Found
**Error**: `Python is not installed or not in PATH`
**Solution**: 
- Install Python 3.7+ from https://www.python.org/downloads/
- Ensure "Add Python to PATH" is checked during installation

#### 2. Chrome Driver Issues
**Error**: `Chrome driver not found`
**Solution**:
- Download ChromeDriver from https://chromedriver.chromium.org/
- Place `chromedriver.exe` in the `drivers/` folder
- Or let Selenium download automatically

#### 3. Configuration File Missing
**Error**: `Configuration file config.cnf not found`
**Solution**:
- Create `config.cnf` file with proper settings
- Follow the configuration template above

#### 4. Network Connection Issues
**Error**: `Login timeout` or `SFTP connection failed`
**Solution**:
- Check internet connection
- Verify LSEG website accessibility
- Confirm SFTP server status

#### 5. Email Sending Failed
**Error**: `163 email sending failed`
**Solution**:
- Enable SMTP service in 163 email settings
- Generate authorization code
- Update configuration with correct credentials

### Debug Mode

To run in debug mode with more detailed output:
```cmd
python lseg_login_english.py --debug
```

### Manual Testing

For testing individual components:
```cmd
# Test configuration loading
python -c "from lseg_login_english import LSEGLoginAutomation; LSEGLoginAutomation().load_config()"

# Test SFTP connection
python -c "from lseg_login_english import LSEGLoginAutomation; LSEGLoginAutomation().upload_file_via_sftp('test.txt')"
```

## Automation

### Windows Task Scheduler

To run automatically:

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., daily at 9:00 AM)
4. Set action: Start a program
5. Program: `start_lseg_automation.bat`
6. Start in: Project directory path

### PowerShell Scheduled Job

```powershell
# Create daily job at 9:00 AM
$action = New-ScheduledJobAction -Execute "PowerShell.exe" -Argument "-File `"$PWD\start_lseg_automation.ps1`""
$trigger = New-ScheduledJobTrigger -Daily -At 9:00AM
Register-ScheduledJob -Name "LSEG Automation" -Action $action -Trigger $trigger
```

## Security Considerations

### Credential Management
- Store credentials in `config.cnf` file
- Keep configuration file secure
- Use environment variables for production

### Network Security
- Use SFTP for secure file transfer
- Enable SSL/TLS for email
- Verify server certificates

### Access Control
- Limit file permissions
- Use dedicated service accounts
- Regular credential rotation

## Performance Optimization

### Browser Settings
- Headless mode available
- Optimized Chrome flags
- Disabled unnecessary features

### Memory Management
- Automatic browser cleanup
- Temporary file removal
- Resource cleanup on exit

### Network Optimization
- Connection pooling
- Retry with exponential backoff
- Timeout configuration

## Version History

### v1.0.0 (Current)
- Initial English version
- Complete automation workflow
- Email notifications
- SFTP upload functionality
- Comprehensive logging
- Retry mechanism

## Support

For issues and questions:
1. Check log files in `logs/` directory
2. Review configuration settings
3. Test individual components
4. Check network connectivity

## License

This project is for internal use only. Please ensure compliance with LSEG terms of service and data usage policies. 