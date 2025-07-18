import os
import time
import shutil
import smtplib
import configparser
import logging
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import paramiko
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class LSEGLoginAutomation:
    def __init__(self):
        # Setup logging
        self.setup_logging()
        
        # Load configuration
        self.load_config()
        
        self.headless = False
        self.timeout = 30
        self.driver = None
        self.wait = None
        self.log_file = None
        
    def setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create log file by date
        today = datetime.now().strftime("%Y%m%d")
        self.log_file = log_dir / f"lseg_automation_{today}.log"
        
        # Configure logging format
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()  # Also output to console
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("="*50)
        self.logger.info("LSEG Automation Program Started")
        self.logger.info("="*50)
        
    def check_today_execution(self):
        """Check if the program has been successfully executed today"""
        today = datetime.now().strftime("%Y%m%d")
        
        # 1. Check if log file shows successful execution today
        if self.log_file and self.log_file.exists():
            self.logger.info(f"📋 Checking today's execution log: {self.log_file}")
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    if "🎉 Complete program execution successful!" in log_content:
                        self.logger.info("✅ Found record of successful execution today")
                        return True, "Log shows successful execution today"
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to read log file: {e}")
        
        # 2. Check if today's file already exists on SFTP server
        self.logger.info("🔍 Checking if today's file already exists on SFTP server...")
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=self.sftp_host,
                username=self.sftp_username,
                password=self.sftp_password,
                timeout=30
            )
            
            sftp = ssh.open_sftp()
            
            # Check files in remote directory
            remote_files = sftp.listdir(self.sftp_remote_dir)
            today_pattern = f"AU_RicChangeEvents_{today}"
            
            for file in remote_files:
                if today_pattern in file:
                    self.logger.info(f"✅ Found today's file: {file}")
                    sftp.close()
                    ssh.close()
                    return True, f"Today's file already exists on SFTP server: {file}"
            
            self.logger.info("📁 No today's file found on SFTP server")
            sftp.close()
            ssh.close()
            
        except Exception as e:
            self.logger.warning(f"⚠️ SFTP check failed: {e}")
        
        return False, "No execution record found today"
        
    def load_config(self):
        """Load settings from configuration file"""
        config = configparser.ConfigParser()
        config_file = 'config.cnf'
        
        if not os.path.exists(config_file):
            print(f"❌ Configuration file {config_file} does not exist!")
            print("💡 Please ensure config.cnf file exists and contains necessary configuration information")
            raise FileNotFoundError(f"Configuration file {config_file} not found")
        
        config.read(config_file, encoding='utf-8')
        
        try:
            # LSEG login credentials
            self.username = config.get('lseg_login', 'username')
            self.password = config.get('lseg_login', 'password')
            
            # File path configuration
            self.downloads_path = Path(config.get('paths', 'downloads_path'))
            self.target_dir = Path(config.get('paths', 'target_dir'))
            self.target_file = config.get('paths', 'target_file')
            
            # SFTP configuration
            self.sftp_host = config.get('sftp', 'host')
            self.sftp_username = config.get('sftp', 'username')
            self.sftp_password = config.get('sftp', 'password')
            self.sftp_remote_dir = config.get('sftp', 'remote_dir')
            
            # Email configuration (163 email)
            self.smtp_server = config.get('email', 'smtp_server')
            self.smtp_port = config.getint('email', 'smtp_port')
            self.email_sender = config.get('email', 'sender')
            self.email_password = config.get('email', 'password')
            self.email_recipient = config.get('email', 'recipient')
            self.enable_email = config.getboolean('email', 'enable_email')
            
            print("✅ Configuration file loaded successfully")
            print(f"📧 Email service: {self.smtp_server}:{self.smtp_port} ({self.email_sender})")
            print(f"📤 SFTP service: {self.sftp_host}:{self.sftp_remote_dir}")
            print(f"🔐 LSEG account: {self.username}")
            
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
            print(f"❌ Configuration file format error: {e}")
            print("💡 Please check the format and content of config.cnf file")
            raise
        
    def ensure_target_directory(self):
        """Ensure target directory exists"""
        if not self.target_dir.exists():
            self.target_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {self.target_dir}")
    
    def wait_for_download_completion(self, max_wait_time=60):
        """Intelligent wait for download completion"""
        print(f"⏳ Intelligently waiting for download completion (max {max_wait_time} seconds)...")
        
        start_time = time.time()
        check_interval = 2  # Check every 2 seconds
        
        while time.time() - start_time < max_wait_time:
            # Check all xlsx files in Downloads directory
            xlsx_files = list(self.downloads_path.glob("*.xlsx"))
            
            if xlsx_files:
                # Found xlsx file, check if still downloading (file size still changing)
                largest_file = max(xlsx_files, key=lambda f: f.stat().st_size)
                file_size = largest_file.stat().st_size
                
                print(f"📥 Found file: {largest_file.name} ({file_size} bytes)")
                
                # Wait 3 seconds then check file size again to confirm download completion
                time.sleep(3)
                new_size = largest_file.stat().st_size
                
                if new_size == file_size and file_size > 1024:  # File size unchanged and larger than 1KB
                    print(f"✅ Download completed: {largest_file.name} ({new_size} bytes)")
                    return largest_file
                else:
                    print(f"⏳ File still downloading... {file_size} -> {new_size} bytes")
            
            # Wait for check interval each time
            time.sleep(check_interval)
            elapsed = int(time.time() - start_time)
            print(f"⏰ Waited {elapsed} seconds...")
        
        print(f"⚠️ Wait timeout ({max_wait_time} seconds), checking latest xlsx file...")
        xlsx_files = list(self.downloads_path.glob("*.xlsx"))
        if xlsx_files:
            latest_file = max(xlsx_files, key=lambda f: f.stat().st_mtime)
            print(f"📁 Using latest file: {latest_file.name}")
            return latest_file
        
        return None
    
    def handle_onetrust_cookie_popup(self):
        """Handle OneTrust Cookie popup (called on final page)"""
        if not self.driver or not self.wait:
            print("⚠️ Browser driver not initialized, skipping Cookie popup handling")
            return False
            
        print("🍪 Handling OneTrust Cookie popup...")
        
        # Wait for page to fully load
        time.sleep(3)
        
        # Try multiple strategies to handle OneTrust cookie popup
        cookie_handled = False
        
        # Strategy 1: Directly click Accept button
        try:
            cookie_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            self.driver.execute_script("arguments[0].click();", cookie_button)
            print("✅ Successfully clicked OneTrust Accept button")
            cookie_handled = True
            time.sleep(2)
        except TimeoutException:
            print("⚠️ OneTrust Accept button not found...")
        
        # Strategy 2: If Accept fails, try Reject All
        if not cookie_handled:
            try:
                reject_button = self.driver.find_element(By.ID, "onetrust-reject-all-handler")
                self.driver.execute_script("arguments[0].click();", reject_button)
                print("✅ Successfully clicked OneTrust Reject All button")
                cookie_handled = True
                time.sleep(2)
            except NoSuchElementException:
                print("⚠️ OneTrust Reject button also not found...")
        
        # Strategy 3: Force remove OneTrust related elements
        if not cookie_handled:
            try:
                self.driver.execute_script("""
                     // Remove OneTrust related elements
                     var removeElements = [
                         'onetrust-group-container',
                         'onetrust-banner-content',
                         'onetrust-policy-title',
                         'onetrust-button-group-parent',
                         'onetrust-button-group',
                         'onetrust-policy',
                         'onetrust-pc-btn-handler',
                         'onetrust-accept-btn-handler',
                         'onetrust-reject-all-handler'
                     ];
                     
                     removeElements.forEach(function(id) {
                         var element = document.getElementById(id);
                         if (element) {
                             element.remove();
                             console.log('Removed element: ' + id);
                         }
                     });
                     
                     // Remove all OneTrust related overlays and components
                     var selectors = [
                         '.onetrust-pc-dark-filter',
                         '.ot-fade-in',
                         '.ot-sdk-row',
                         '.ot-sdk-container',
                         '.banner_logo',
                         '[id*="onetrust"]',
                         '[class*="onetrust"]',
                         '[class*="ot-"]'
                     ];
                     
                     selectors.forEach(function(selector) {
                         var elements = document.querySelectorAll(selector);
                         elements.forEach(function(element) {
                             element.remove();
                         });
                     });
                     
                     // Force remove any high z-index blocking elements
                     var allElements = document.querySelectorAll('*');
                     allElements.forEach(function(element) {
                         var style = window.getComputedStyle(element);
                         var zIndex = parseInt(style.zIndex);
                         if (zIndex > 1000000) {
                             element.remove();
                         }
                     });
                     
                     // Reset body overflow style
                     document.body.style.overflow = 'auto';
                     document.documentElement.style.overflow = 'auto';
                     
                     console.log('All OneTrust related elements removed');
                 """)
                print("✅ Force removed OneTrust components")
                cookie_handled = True
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ Force removal failed: {e}")
        
        if cookie_handled:
            print("✅ Cookie popup handling completed")
        else:
            print("⚠️ Cookie popup handling failed, continuing execution...")
        
        time.sleep(2)  # Extra wait to ensure page stability
        return cookie_handled
    
    def check_downloaded_file(self):
        """Check if downloaded file exists"""
        file_path = self.downloads_path / self.target_file
        if file_path.exists():
            print(f"✅ Found downloaded file: {file_path}")
            return file_path
        else:
            print(f"❌ Downloaded file not found: {file_path}")
            return None
    
    def process_excel_file(self, source_file):
        """Process Excel file, filter AU records and generate new file (preserve headers)"""
        try:
            print(f"📊 Starting Excel file processing: {source_file}")
            
            # Read Excel file
            df = pd.read_excel(source_file)
            print(f"📋 File contains {len(df)} rows of data")
            
            # Check if column E exists (Country column)
            if len(df.columns) < 5:
                print("❌ Insufficient columns in file, cannot find column E")
                return None
            
            # Get column E (index 4, this is the Country column)
            country_column = df.iloc[:, 4]  # Column E is the 5th column, index 4
            column_name = df.columns[4]
            print(f"📍 Filtering data containing 'AU' in {column_name} column...")
            
            # Filter rows containing AU (preserve headers)
            au_mask = country_column.astype(str).str.contains('AU', na=False, case=False)
            au_data = df[au_mask].copy()  # Copy data, preserve original DataFrame structure
            
            print(f"✅ Filtered {len(au_data)} records containing AU")
            
            if len(au_data) == 0:
                print("⚠️ No data containing AU found")
                # Even if no data, create a file with only headers
                empty_df = df.iloc[:0].copy()  # Empty DataFrame with only headers
                today = datetime.now().strftime("%Y%m%d")
                new_filename = f"AU_RicChangeEvents_{today}.xlsx"
                new_file_path = self.target_dir / new_filename
                empty_df.to_excel(new_file_path, index=False)
                print(f"✅ Created file with headers only: {new_file_path}")
                return new_file_path
            
            # Generate filename with date
            today = datetime.now().strftime("%Y%m%d")
            new_filename = f"AU_RicChangeEvents_{today}.xlsx"
            new_file_path = self.target_dir / new_filename
            
            # Save filtered data (automatically includes headers)
            au_data.to_excel(new_file_path, index=False)
            print(f"✅ Saved AU data to: {new_file_path}")
            print(f"📊 File contains headers + {len(au_data)} AU records")
            
            return new_file_path
            
        except Exception as e:
            print(f"❌ Error processing Excel file: {e}")
            return None
    
    def cleanup_downloads(self):
        """Clean up all xlsx files in Downloads directory"""
        try:
            xlsx_files = list(self.downloads_path.glob("*.xlsx"))
            if xlsx_files:
                print(f"🧹 Starting cleanup of {len(xlsx_files)} xlsx files...")
                for file in xlsx_files:
                    file.unlink()
                    print(f"🗑️ Deleted: {file.name}")
                print("✅ Downloads directory cleanup completed")
            else:
                print("ℹ️ No xlsx files in Downloads directory need cleanup")
        except Exception as e:
            print(f"❌ Error cleaning Downloads directory: {e}")
    
    def upload_file_via_sftp(self, local_file_path, max_retries=5):
        """Upload file to remote server via SFTP"""
        print(f"\n📤 Starting SFTP upload: {local_file_path}")
        
        for attempt in range(max_retries):
            try:
                print(f"🔄 Upload attempt {attempt + 1}...")
                
                # Create SSH client
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Connect to server
                ssh.connect(
                    hostname=self.sftp_host,
                    username=self.sftp_username,
                    password=self.sftp_password,
                    timeout=30
                )
                
                # Create SFTP client
                sftp = ssh.open_sftp()
                
                # Ensure remote directory exists
                try:
                    sftp.listdir(self.sftp_remote_dir)
                except IOError:
                    print(f"📁 Creating remote directory: {self.sftp_remote_dir}")
                    # Try to create directory
                    ssh.exec_command(f"mkdir -p {self.sftp_remote_dir}")
                
                # Upload file
                remote_file_path = f"{self.sftp_remote_dir}/{local_file_path.name}"
                sftp.put(str(local_file_path), remote_file_path)
                
                # Verify upload success
                remote_files = sftp.listdir(self.sftp_remote_dir)
                if local_file_path.name in remote_files:
                    print(f"✅ File upload successful: {remote_file_path}")
                    
                    # Get remote file size for verification
                    remote_file_stat = sftp.stat(remote_file_path)
                    local_file_size = local_file_path.stat().st_size
                    
                    if remote_file_stat.st_size == local_file_size:
                        print(f"✅ File size verification passed: {local_file_size} bytes")
                        sftp.close()
                        ssh.close()
                        return True, f"File successfully uploaded to {remote_file_path}"
                    else:
                        print(f"❌ File size mismatch: Local {local_file_size} vs Remote {remote_file_stat.st_size}")
                
                sftp.close()
                ssh.close()
                
            except Exception as e:
                print(f"❌ Upload attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    print("⏳ Waiting 10 seconds before retry...")
                    time.sleep(10)
        
        return False, f"SFTP upload failed after {max_retries} attempts"
    
    def send_email_report(self, success, file_path, upload_result, au_record_count=0):
        """Send email report (using 163 email)"""
        try:
            print("📧 Preparing email report...")
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = self.email_recipient
            msg['Subject'] = f"RIC Change Data Processing Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Generate report content
            if success:
                status = "✅ Success"
                report_content = f"""RIC Change Data Processing Report

Processing Status: {status}
Processing Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Processed File: {file_path.name if file_path else 'N/A'}
AU Record Count: {au_record_count}
SFTP Upload Result: {upload_result}

Detailed Information:
- Original File Download: Successful
- AU Data Filtering: Successful (Filtered {au_record_count} records)
- File Save: Successful
- SFTP Upload: {'Successful' if 'successfully' in upload_result else 'Failed'}
- Downloads Cleanup: Completed

File Save Location: {file_path if file_path else 'N/A'}
Remote Server: {self.sftp_host}:{self.sftp_remote_dir}

---
This email was sent by RIC Change Data Automatic Processing Program"""
            else:
                status = "❌ Failed"
                report_content = f"""RIC Change Data Processing Report

Processing Status: {status}
Processing Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Error Information: {upload_result}

Processing Steps:
- File Download: {'Successful' if file_path else 'Failed'}
- AU Data Filtering: {'Successful' if file_path else 'Not Executed'}
- SFTP Upload: Failed

Recommended Actions:
1. Check network connection
2. Verify SFTP server status
3. Confirm downloaded file integrity
4. Program will automatically retry in 5 minutes

---
This email was sent by RIC Change Data Automatic Processing Program"""
            
            msg.attach(MIMEText(report_content, 'plain', 'utf-8'))
            
            # Display email content
            print("📧 Email content preview:")
            print("=" * 50)
            print(report_content)
            print("=" * 50)
            
            # Send email
            if self.enable_email:
                try:
                    print(f"📨 Sending email via 163 email...")
                    print(f"   Sender: {self.email_sender}")
                    print(f"   Recipient: {self.email_recipient}")
                    
                    # Connect to 163 SMTP server (using SSL)
                    if self.smtp_port == 465:
                        server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
                    else:
                        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                        server.starttls()  # Enable secure transmission
                    server.login(self.email_sender, self.email_password)
                    
                    # Send email
                    text = msg.as_string()
                    server.sendmail(self.email_sender, self.email_recipient, text)
                    server.quit()
                    
                    print("✅ 163 email sent successfully!")
                    
                except Exception as email_error:
                    print(f"❌ 163 email sending failed: {email_error}")
                    print("💡 Please check 163 email configuration:")
                    print("   1. Confirm email address and password are correct")
                    print("   2. Confirm SMTP service is enabled")
                    print("   3. Check network connection")
                    print("   4. Confirm firewall is not blocking SMTP connection")
                    print("💡 163 email may require authorization code:")
                    print("   - Login to 163 email -> Settings -> Client Authorization Password")
                    print("   - Enable SMTP service and get authorization code")
            else:
                print("⚠️ Email sending is disabled, enable it in config file by setting enable_email=true")
            
        except Exception as e:
            print(f"❌ Error processing email: {e}")
    
    def process_downloaded_file(self):
        """Process downloaded file, including SFTP upload"""
        print("\n" + "="*50)
        print("📁 Starting file processing workflow...")
        print("="*50)
        
        au_record_count = 0
        processed_file = None
        upload_success = False
        upload_message = ""
        
        try:
            # Ensure target directory exists
            self.ensure_target_directory()
            
            # Wait and check downloaded file (intelligent detection)
            source_file = self.wait_for_download_completion(max_wait_time=90)  # Wait 90 seconds
            if not source_file:
                upload_message = "Downloaded file not found or download timeout"
                self.send_email_report(False, None, upload_message, 0)
                return False
            
            # Process Excel file
            processed_file = self.process_excel_file(source_file)
            if not processed_file:
                upload_message = "Excel file processing failed"
                self.send_email_report(False, source_file, upload_message, 0)
                return False
            
            # Read processed file to get record count
            try:
                df = pd.read_excel(processed_file)
                au_record_count = len(df)
                print(f"📊 Processing completed, {au_record_count} AU records total")
            except:
                au_record_count = 0
            
            # SFTP upload file
            upload_success, upload_message = self.upload_file_via_sftp(processed_file)
            
            # Clean up Downloads directory
            self.cleanup_downloads()
            
            # Send email report
            self.send_email_report(upload_success, processed_file, upload_message, au_record_count)
            
            if upload_success:
                print(f"🎉 Complete workflow execution successful!")
                print(f"   - AU Records: {au_record_count}")
                print(f"   - Local File: {processed_file}")
                print(f"   - SFTP Status: Successful")
                return True
            else:
                print(f"❌ SFTP upload failed: {upload_message}")
                return False
                
        except Exception as e:
            error_message = f"Error occurred during file processing: {e}"
            print(f"❌ {error_message}")
            self.send_email_report(False, processed_file, error_message, au_record_count)
            return False
        
    def setup_driver(self):
        """Configure browser driver"""
        chrome_options = Options()
        
        # Disable password saving and autofill
        chrome_options.add_argument("--disable-password-manager-reauthentication")
        chrome_options.add_argument("--disable-save-password-bubble")
        chrome_options.add_argument("--disable-password-generation")
        chrome_options.add_argument("--disable-autofill")
        chrome_options.add_argument("--disable-autofill-keyboard-accessory-view")
        chrome_options.add_argument("--disable-full-form-autofill-ios")
        
        # Disable Cookie popup and privacy notifications
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-cookie-encryption")
        chrome_options.add_argument("--disable-privacy-sandbox-prompt")
        chrome_options.add_argument("--disable-component-extensions-with-background-pages")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_argument("--disable-hang-monitor")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-prompt-on-repost")
        chrome_options.add_argument("--disable-domain-reliability")
        chrome_options.add_argument("--disable-consent-auditing")
        chrome_options.add_argument("--disable-privacy-sandbox")
        
        # Aggressively disable all popups and overlays
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-features=Translate")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-service-autorun")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-component-update")
        chrome_options.add_argument("--block-new-web-contents")
        
        # Block OneTrust and other Cookie management tools
        chrome_options.add_argument("--disable-permissions-api")
        chrome_options.add_argument("--disable-site-isolation-trials")
        chrome_options.add_argument("--disable-features=VizServiceDisplayCompositor,VizDisplayCompositor")
        chrome_options.add_argument("--aggressive-cache-discard")
        chrome_options.add_argument("--disable-partial-raster")
        chrome_options.add_argument("--disable-skia-runtime-opts")
        chrome_options.add_argument("--disable-checking-optimization-guide-user-permissions")
        chrome_options.add_argument("--disable-back-forward-cache")
        
        # Add user preferences to disable password saving and Cookie popups
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.default_content_setting_values.cookies": 1,  # Allow cookies but don't show popups
            "profile.cookie_controls_mode": 0,  # Disable cookie control
            "profile.managed_default_cookie_setting": 1,
            "profile.block_third_party_cookies": False,
            "profile.cookie_session_only": False,
            "privacy_sandbox.apis_enabled": False,
            "privacy_sandbox.personalization_enabled": False,
            "privacy_sandbox.topics_enabled": False,
            "privacy_sandbox.fledge_enabled": False,
            "privacy_sandbox.ad_measurement_enabled": False,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Other settings
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Window size settings
        chrome_options.add_argument("--window-size=1051,805")
        
        # Disable GPU acceleration (sometimes can solve some issues)
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        print("🚀 Starting Chrome browser...")
        
        try:
            # Try to use manually downloaded chromedriver
            driver_path = os.path.join(os.getcwd(), "drivers", "chromedriver.exe")
            if os.path.exists(driver_path):
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                print("✅ Chrome browser started successfully (using manually downloaded driver)")
            else:
                # Use Selenium 4's automatic driver management
                self.driver = webdriver.Chrome(options=chrome_options)
                print("✅ Chrome browser started successfully (using automatic driver management)")
            
            # Execute script to further disable auto-save
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, self.timeout)
            
        except Exception as e:
            print(f"❌ Unable to start Chrome browser: {e}")
            print("💡 Please ensure Chrome browser is installed")
            print("💡 If problem persists, try updating Chrome to latest version")
            raise
        
    def login(self):
        """Execute login workflow"""
        try:
            print("🚀 Starting login workflow...")
            
            # 0. Setup browser driver
            self.setup_driver()
            
            # 1. Visit target website
            target_url = "https://myaccount.lseg.com/en/symbolchanges"
            print(f"📍 Visiting target website: {target_url}")
            self.driver.get(target_url)
            
            # Wait for page redirect to login page
            print("⏳ Waiting for redirect to login page...")
            time.sleep(5)
            
            # 2. Enter username
            print("👤 Entering username...")
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "AAA-AS-SI1-SE003"))
            )
            username_field.clear()
            username_field.send_keys(self.username)
            
            # 3. Enter password
            print("🔒 Entering password...")
            password_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "AAA-AS-SI1-SE006"))
            )
            password_field.clear()
            password_field.send_keys(self.password)
            
            # 4. Press Enter key to login (according to new recording)
            print("⏎ Pressing Enter key to login...")
            password_field.send_keys(Keys.RETURN)
            
            # 5. Wait for page redirect
            print("⏳ Waiting for login page redirect...")
            time.sleep(3)
            
            # 6. Click checkbox
            print("☑️ Clicking checkbox...")
            try:
                checkbox = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".ui-checkbox__bg"))
                )
                checkbox.click()
                print("✅ Checkbox clicked")
                time.sleep(1)
            except TimeoutException:
                print("⚠️ Checkbox not found, continuing to next step...")
            
            # 7. Wait for terms-of-use page to load and handle Cookie popup
            print("⏳ Waiting for terms-of-use page to load...")
            time.sleep(3)
            
            # Check if reached terms-of-use page
            current_url = self.driver.current_url if self.driver else ""
            if "terms-of-use" in current_url.lower():
                print("📄 Reached terms-of-use page, handling Cookie popup...")
                self.handle_onetrust_cookie_popup()
            else:
                print(f"⚠️ Current page: {current_url}, trying to handle Cookie popup...")
                self.handle_onetrust_cookie_popup()
            
            # 8. Click Accept and Continue button
            print("✅ Clicking Accept and Continue...")
            try:
                accept_button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#instrumentchange > span"))
                )
                accept_button.click()
                print("✅ Accept and Continue button clicked")
                time.sleep(2)
            except TimeoutException:
                print("⚠️ Accept and Continue button not found...")
            
            # 9. 【Key new step】Click SVG icon for navigation
            print("🧭 Clicking SVG icon for navigation...")
            try:
                # Wait for page to fully load
                time.sleep(2)
                
                # Try multiple ways to click SVG icon
                svg_selectors = [
                    ".sc-hqyNC:nth-child(1) svg",  # Original selector
                    ".sc-hqyNC:nth-child(1)",      # Parent container
                    ".sc-hqyNC svg",               # More generic selector
                    ".sc-hqyNC",                   # Container itself
                ]
                
                clicked = False
                for selector in svg_selectors:
                    try:
                        svg_icon = self.wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        # Try regular click
                        svg_icon.click()
                        print(f"✅ SVG icon clicked (selector: {selector})")
                        clicked = True
                        break
                    except Exception as e:
                        print(f"⚠️ Selector {selector} failed: {e}")
                        continue
                
                if not clicked:
                    print("⚠️ All SVG selectors failed")
                else:
                    time.sleep(3)  # Wait for navigation to complete
                    
            except Exception as e:
                print(f"⚠️ SVG icon click failed: {e}")
            
            # 10. Click Apply button
            print("📋 Clicking Apply button...")
            try:
                apply_button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".sc-VJcYb"))
                )
                apply_button.click()
                print("✅ Apply button clicked")
            except TimeoutException:
                print("⚠️ Apply button not found...")
            
            # 11. Wait for final page to load
            print("⏳ Waiting for final page to load...")
            time.sleep(5)
            
            # Check login status
            current_url = self.driver.current_url
            print(f"🌐 Current page URL: {current_url}")
            
            if "symbolchanges" in current_url.lower() or "myaccount.lseg.com" in current_url.lower():
                print("🎉 Login successful!")
                return True
            else:
                print("❓ Login status uncertain, please check page")
                return False
                
        except TimeoutException as e:
            print(f"❌ Login timeout: {e}")
            return False
        except Exception as e:
            print(f"❌ Error occurred during login: {e}")
            return False
    
    def get_page_info(self):
        """Get current page information"""
        try:
            title = self.driver.title
            url = self.driver.current_url
            print(f"📄 Page title: {title}")
            print(f"🌐 Page URL: {url}")
            
            # Find possible download buttons and links
            download_selectors = [
                "//button[contains(text(), 'Download')]",
                "//button[contains(text(), 'Export')]", 
                "//button[contains(text(), 'CSV')]",
                "//button[contains(text(), 'Excel')]",
                "//a[contains(text(), 'Download')]",
                "//a[contains(text(), 'Export')]",
                "//a[contains(text(), 'CSV')]",
                "//a[contains(text(), 'Excel')]",
                "//button[contains(@class, 'download')]",
                "//a[contains(@class, 'download')]",
                "//button[contains(@aria-label, 'Download')]",
                "//a[contains(@aria-label, 'Download')]",
                "//input[@type='submit'][contains(@value, 'Download')]",
                "//span[contains(text(), 'Download')]",
                "//div[contains(text(), 'Download')]",
            ]
            
            found_downloads = []
            for selector in download_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        try:
                            text = element.text.strip()
                            if text:
                                found_downloads.append({
                                    'element': element,
                                    'text': text,
                                    'tag': element.tag_name,
                                    'href': element.get_attribute('href') if element.tag_name == 'a' else None
                                })
                        except:
                            pass
                except:
                    pass
                    
            if found_downloads:
                print(f"📥 Found {len(found_downloads)} possible download elements")
                for i, item in enumerate(found_downloads[:10]):  # Only show first 10
                    href_info = f" -> {item['href']}" if item['href'] else ""
                    print(f"  {i+1}. [{item['tag']}] '{item['text']}'{href_info}")
            else:
                print("🔍 No obvious download buttons found")
                
            # Find all elements that might contain download functionality
            all_elements = self.driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'symbol') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'change') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'instrument')]")
            
            if all_elements:
                print(f"🔍 Found {len(all_elements)} elements containing keywords")
                for i, element in enumerate(all_elements[:10]):  # Only show first 10
                    try:
                        text = element.text.strip()
                        if text and len(text) < 100:  # Only show short text
                            print(f"  {i+1}. [{element.tag_name}] '{text}'")
                    except:
                        pass
                
        except Exception as e:
            print(f"❌ Error getting page information: {e}")
    
    def close(self):
        """Close browser"""
        if self.driver:
            print("🔚 Closing browser...")
            self.driver.quit()

    def run_with_retry(self, max_retries=3, retry_delay=300):
        """
        Run program with retry mechanism
        max_retries: Maximum retry attempts
        retry_delay: Retry interval (seconds), default 5 minutes
        """
        self.logger.info("🚀 Starting LSEG automatic download and file processing program...")
        self.logger.info(f"📋 Configuration information:")
        self.logger.info(f"   - Download directory: {self.downloads_path}")
        self.logger.info(f"   - Target directory: {self.target_dir}")
        self.logger.info(f"   - SFTP server: {self.sftp_host}:{self.sftp_remote_dir}")
        self.logger.info(f"   - Email recipient: {self.email_recipient}")
        
        # Check if program has been successfully executed today
        self.logger.info("🔍 Checking if executed today...")
        already_executed, reason = self.check_today_execution()
        
        if already_executed:
            self.logger.info(f"⏹️ Program already successfully executed today, skipping run")
            self.logger.info(f"   Reason: {reason}")
            print(f"⏹️ Program already successfully executed today, skipping run")
            print(f"   Reason: {reason}")
            print(f"   To force re-execution, please delete today's log file or remote file")
            return True
        
        self.logger.info("▶️ Not executed today, starting program...")
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"\n📍 Attempt {attempt + 1} (Total {max_retries})")
                print(f"\n📍 Attempt {attempt + 1} (Total {max_retries})")
                
                # Execute login and download
                if self.login():
                    self.logger.info("✅ Login and page navigation successful")
                    print("✅ Login and page navigation successful")
                    
                    # Process downloaded file (includes intelligent download wait, SFTP upload and email sending)
                    if self.process_downloaded_file():
                        self.logger.info("🎉 Complete program execution successful!")
                        print("🎉 Complete program execution successful!")
                        return True
                    else:
                        self.logger.error("❌ File download, processing or upload failed")
                        print("❌ File download, processing or upload failed")
                else:
                    self.logger.error("❌ Login or page navigation failed")
                    print("❌ Login or page navigation failed")
                    
            except Exception as e:
                self.logger.error(f"❌ Program execution error: {e}")
                print(f"❌ Program execution error: {e}")
            
            finally:
                # Close browser
                if self.driver:
                    try:
                        self.driver.quit()
                        self.logger.info("🔚 Closing browser...")
                        print("🔚 Closing browser...")
                    except:
                        pass
                    self.driver = None
                    self.wait = None
            
            # If not the last attempt, wait then retry
            if attempt < max_retries - 1:
                self.logger.warning(f"⏳ Retrying in {retry_delay//60} minutes...")
                print(f"⏳ Retrying in {retry_delay//60} minutes...")
                # Don't send email during retries, only log
                time.sleep(retry_delay)
        
        self.logger.error("❌ All attempts failed, program exiting")
        print("❌ All attempts failed, program exiting")
        # Send final failure email
        self.send_email_report(False, None, f"Program execution failed after {max_retries} attempts", 0)
        return False

def main():
    """Main function"""
    automation = LSEGLoginAutomation()
    try:
        success = automation.run_with_retry(max_retries=3, retry_delay=300)  # 5 minute retry interval
        
        if success:
            print("\n🎉 Program execution completed successfully, exiting...")
        else:
            print("\n❌ Program execution failed, exiting...")
    
    except KeyboardInterrupt:
        print("\n⚠️ User interrupted program...")
    
    except Exception as e:
        print(f"\n❌ Program encountered unhandled error: {e}")
    
    finally:
        # Force cleanup all resources
        try:
            if hasattr(automation, 'driver') and automation.driver:
                automation.driver.quit()
                print("🔧 Force closing browser driver...")
        except:
            pass
        
        print("🏁 Program completely exited")
        
        # Force exit program
        import sys
        sys.exit(0)

if __name__ == "__main__":
    main() 