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
        # 设置日志
        self.setup_logging()
        
        # 读取配置文件
        self.load_config()
        
        self.headless = False
        self.timeout = 30
        self.driver = None
        self.wait = None
        self.log_file = None
        
    def setup_logging(self):
        """设置日志记录"""
        # 创建logs目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 按日期创建日志文件
        today = datetime.now().strftime("%Y%m%d")
        self.log_file = log_dir / f"lseg_automation_{today}.log"
        
        # 配置日志格式
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()  # 同时输出到控制台
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("="*50)
        self.logger.info("LSEG自动化程序启动")
        self.logger.info("="*50)
        
    def check_today_execution(self):
        """检查今天是否已经成功执行过"""
        today = datetime.now().strftime("%Y%m%d")
        
        # 1. 检查日志文件是否显示今天已成功
        if self.log_file and self.log_file.exists():
            self.logger.info(f"📋 检查今日执行日志: {self.log_file}")
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    if "🎉 完整程序执行成功！" in log_content:
                        self.logger.info("✅ 发现今日已成功执行的记录")
                        return True, "日志显示今日已成功执行"
            except Exception as e:
                self.logger.warning(f"⚠️ 读取日志文件失败: {e}")
        
        # 2. 检查SFTP服务器上是否已有今天的文件
        self.logger.info("🔍 检查SFTP服务器上是否已有今日文件...")
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
            
            # 检查远程目录中的文件
            remote_files = sftp.listdir(self.sftp_remote_dir)
            today_pattern = f"AU_RicChangeEvents_{today}"
            
            for file in remote_files:
                if today_pattern in file:
                    self.logger.info(f"✅ 发现今日文件: {file}")
                    sftp.close()
                    ssh.close()
                    return True, f"SFTP服务器上已存在今日文件: {file}"
            
            self.logger.info("📁 SFTP服务器上没有今日文件")
            sftp.close()
            ssh.close()
            
        except Exception as e:
            self.logger.warning(f"⚠️ SFTP检查失败: {e}")
        
        return False, "未发现今日执行记录"
        
    def load_config(self):
        """从配置文件加载设置"""
        config = configparser.ConfigParser()
        config_file = 'config.cnf'
        
        if not os.path.exists(config_file):
            print(f"❌ 配置文件 {config_file} 不存在！")
            print("💡 请确保config.cnf文件存在并包含必要的配置信息")
            raise FileNotFoundError(f"配置文件 {config_file} 未找到")
        
        config.read(config_file, encoding='utf-8')
        
        try:
            # LSEG登录凭证
            self.username = config.get('lseg_login', 'username')
            self.password = config.get('lseg_login', 'password')
            
            # 文件路径配置
            self.downloads_path = Path(config.get('paths', 'downloads_path'))
            self.target_dir = Path(config.get('paths', 'target_dir'))
            self.target_file = config.get('paths', 'target_file')
            
            # SFTP配置
            self.sftp_host = config.get('sftp', 'host')
            self.sftp_username = config.get('sftp', 'username')
            self.sftp_password = config.get('sftp', 'password')
            self.sftp_remote_dir = config.get('sftp', 'remote_dir')
            
            # 邮件配置 (163邮箱)
            self.smtp_server = config.get('email', 'smtp_server')
            self.smtp_port = config.getint('email', 'smtp_port')
            self.email_sender = config.get('email', 'sender')
            self.email_password = config.get('email', 'password')
            self.email_recipient = config.get('email', 'recipient')
            self.enable_email = config.getboolean('email', 'enable_email')
            
            print("✅ 配置文件加载成功")
            print(f"📧 邮件服务: {self.smtp_server}:{self.smtp_port} ({self.email_sender})")
            print(f"📤 SFTP服务: {self.sftp_host}:{self.sftp_remote_dir}")
            print(f"🔐 LSEG账户: {self.username}")
            
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
            print(f"❌ 配置文件格式错误: {e}")
            print("💡 请检查config.cnf文件的格式和内容")
            raise
        
    def ensure_target_directory(self):
        """确保目标目录存在"""
        if not self.target_dir.exists():
            self.target_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ 创建目录: {self.target_dir}")
    
    def wait_for_download_completion(self, max_wait_time=60):
        """智能等待下载完成"""
        print(f"⏳ 智能等待下载完成（最多等待{max_wait_time}秒）...")
        
        start_time = time.time()
        check_interval = 2  # 每2秒检查一次
        
        while time.time() - start_time < max_wait_time:
            # 检查Downloads目录中的所有xlsx文件
            xlsx_files = list(self.downloads_path.glob("*.xlsx"))
            
            if xlsx_files:
                # 找到xlsx文件，检查是否还在下载中（文件大小是否还在变化）
                largest_file = max(xlsx_files, key=lambda f: f.stat().st_size)
                file_size = largest_file.stat().st_size
                
                print(f"📥 发现文件: {largest_file.name} ({file_size} 字节)")
                
                # 等待3秒后再次检查文件大小，确认下载是否完成
                time.sleep(3)
                new_size = largest_file.stat().st_size
                
                if new_size == file_size and file_size > 1024:  # 文件大小不变且大于1KB
                    print(f"✅ 下载完成: {largest_file.name} ({new_size} 字节)")
                    return largest_file
                else:
                    print(f"⏳ 文件还在下载中... {file_size} -> {new_size} 字节")
            
            # 每次等待检查间隔
            time.sleep(check_interval)
            elapsed = int(time.time() - start_time)
            print(f"⏰ 已等待 {elapsed} 秒...")
        
        print(f"⚠️ 等待超时（{max_wait_time}秒），检查最新的xlsx文件...")
        xlsx_files = list(self.downloads_path.glob("*.xlsx"))
        if xlsx_files:
            latest_file = max(xlsx_files, key=lambda f: f.stat().st_mtime)
            print(f"📁 使用最新文件: {latest_file.name}")
            return latest_file
        
        return None
    
    def handle_onetrust_cookie_popup(self):
        """处理OneTrust Cookie弹窗（在最终页面调用）"""
        if not self.driver or not self.wait:
            print("⚠️ 浏览器驱动未初始化，跳过Cookie弹窗处理")
            return False
            
        print("🍪 处理OneTrust Cookie弹窗...")
        
        # 等待页面完全加载
        time.sleep(3)
        
        # 尝试多种策略处理OneTrust cookie弹窗
        cookie_handled = False
        
        # 策略1: 直接点击Accept按钮
        try:
            cookie_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            self.driver.execute_script("arguments[0].click();", cookie_button)
            print("✅ 成功点击OneTrust Accept按钮")
            cookie_handled = True
            time.sleep(2)
        except TimeoutException:
            print("⚠️ OneTrust Accept按钮未找到...")
        
        # 策略2: 如果Accept失败，尝试Reject All
        if not cookie_handled:
            try:
                reject_button = self.driver.find_element(By.ID, "onetrust-reject-all-handler")
                self.driver.execute_script("arguments[0].click();", reject_button)
                print("✅ 成功点击OneTrust Reject All按钮")
                cookie_handled = True
                time.sleep(2)
            except NoSuchElementException:
                print("⚠️ OneTrust Reject按钮也未找到...")
        
        # 策略3: 强制移除OneTrust相关元素
        if not cookie_handled:
            try:
                self.driver.execute_script("""
                     // 移除OneTrust相关元素
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
                             console.log('移除元素: ' + id);
                         }
                     });
                     
                     // 移除所有OneTrust相关的覆盖层和组件
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
                     
                     // 强制移除任何高z-index的阻挡元素
                     var allElements = document.querySelectorAll('*');
                     allElements.forEach(function(element) {
                         var style = window.getComputedStyle(element);
                         var zIndex = parseInt(style.zIndex);
                         if (zIndex > 1000000) {
                             element.remove();
                         }
                     });
                     
                     // 重置body的overflow样式
                     document.body.style.overflow = 'auto';
                     document.documentElement.style.overflow = 'auto';
                     
                     console.log('OneTrust相关元素已全部移除');
                 """)
                print("✅ 强制移除OneTrust组件")
                cookie_handled = True
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ 强制移除失败: {e}")
        
        if cookie_handled:
            print("✅ Cookie弹窗处理完成")
        else:
            print("⚠️ Cookie弹窗处理失败，继续执行...")
        
        time.sleep(2)  # 额外等待确保页面稳定
        return cookie_handled
    
    def check_downloaded_file(self):
        """检查下载的文件是否存在"""
        file_path = self.downloads_path / self.target_file
        if file_path.exists():
            print(f"✅ 找到下载文件: {file_path}")
            return file_path
        else:
            print(f"❌ 未找到下载文件: {file_path}")
            return None
    
    def process_excel_file(self, source_file):
        """处理Excel文件，筛选AU项目并生成新文件（保留表头）"""
        try:
            print(f"📊 开始处理Excel文件: {source_file}")
            
            # 读取Excel文件
            df = pd.read_excel(source_file)
            print(f"📋 文件包含 {len(df)} 行数据")
            
            # 检查E列是否存在（Country列）
            if len(df.columns) < 5:
                print("❌ 文件列数不足，无法找到E列")
                return None
            
            # 获取E列（索引为4，这是Country列）
            country_column = df.iloc[:, 4]  # E列是第5列，索引为4
            column_name = df.columns[4]
            print(f"📍 正在筛选 {column_name} 列中包含 'AU' 的数据...")
            
            # 筛选包含AU的行（保留表头）
            au_mask = country_column.astype(str).str.contains('AU', na=False, case=False)
            au_data = df[au_mask].copy()  # 复制数据，保留原始DataFrame结构
            
            print(f"✅ 筛选出 {len(au_data)} 条包含AU的记录")
            
            if len(au_data) == 0:
                print("⚠️ 没有找到包含AU的数据")
                # 即使没有数据，也创建一个只有表头的文件
                empty_df = df.iloc[:0].copy()  # 只有表头的空DataFrame
                today = datetime.now().strftime("%Y%m%d")
                new_filename = f"AU_RicChangeEvents_{today}.xlsx"
                new_file_path = self.target_dir / new_filename
                empty_df.to_excel(new_file_path, index=False)
                print(f"✅ 已创建只有表头的文件: {new_file_path}")
                return new_file_path
            
            # 生成带日期的文件名
            today = datetime.now().strftime("%Y%m%d")
            new_filename = f"AU_RicChangeEvents_{today}.xlsx"
            new_file_path = self.target_dir / new_filename
            
            # 保存筛选后的数据（自动包含表头）
            au_data.to_excel(new_file_path, index=False)
            print(f"✅ 已保存AU数据到: {new_file_path}")
            print(f"📊 文件包含表头 + {len(au_data)} 条AU记录")
            
            return new_file_path
            
        except Exception as e:
            print(f"❌ 处理Excel文件时出错: {e}")
            return None
    
    def cleanup_downloads(self):
        """清理Downloads目录中的所有xlsx文件"""
        try:
            xlsx_files = list(self.downloads_path.glob("*.xlsx"))
            if xlsx_files:
                print(f"🧹 开始清理 {len(xlsx_files)} 个xlsx文件...")
                for file in xlsx_files:
                    file.unlink()
                    print(f"🗑️ 已删除: {file.name}")
                print("✅ Downloads目录清理完成")
            else:
                print("ℹ️ Downloads目录中没有xlsx文件需要清理")
        except Exception as e:
            print(f"❌ 清理Downloads目录时出错: {e}")
    
    def upload_file_via_sftp(self, local_file_path, max_retries=5):
        """通过SFTP上传文件到远程服务器"""
        print(f"\n📤 开始SFTP上传: {local_file_path}")
        
        for attempt in range(max_retries):
            try:
                print(f"🔄 第 {attempt + 1} 次上传尝试...")
                
                # 创建SSH客户端
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # 连接到服务器
                ssh.connect(
                    hostname=self.sftp_host,
                    username=self.sftp_username,
                    password=self.sftp_password,
                    timeout=30
                )
                
                # 创建SFTP客户端
                sftp = ssh.open_sftp()
                
                # 确保远程目录存在
                try:
                    sftp.listdir(self.sftp_remote_dir)
                except IOError:
                    print(f"📁 创建远程目录: {self.sftp_remote_dir}")
                    # 尝试创建目录
                    ssh.exec_command(f"mkdir -p {self.sftp_remote_dir}")
                
                # 上传文件
                remote_file_path = f"{self.sftp_remote_dir}/{local_file_path.name}"
                sftp.put(str(local_file_path), remote_file_path)
                
                # 验证上传是否成功
                remote_files = sftp.listdir(self.sftp_remote_dir)
                if local_file_path.name in remote_files:
                    print(f"✅ 文件上传成功: {remote_file_path}")
                    
                    # 获取远程文件大小进行验证
                    remote_file_stat = sftp.stat(remote_file_path)
                    local_file_size = local_file_path.stat().st_size
                    
                    if remote_file_stat.st_size == local_file_size:
                        print(f"✅ 文件大小验证通过: {local_file_size} 字节")
                        sftp.close()
                        ssh.close()
                        return True, f"文件成功上传到 {remote_file_path}"
                    else:
                        print(f"❌ 文件大小不匹配: 本地 {local_file_size} vs 远程 {remote_file_stat.st_size}")
                
                sftp.close()
                ssh.close()
                
            except Exception as e:
                print(f"❌ 第 {attempt + 1} 次上传失败: {e}")
                if attempt < max_retries - 1:
                    print("⏳ 等待 10 秒后重试...")
                    time.sleep(10)
        
        return False, f"SFTP上传失败，已尝试 {max_retries} 次"
    
    def send_email_report(self, success, file_path, upload_result, au_record_count=0):
        """发送邮件报告（使用163邮箱）"""
        try:
            print("📧 正在准备邮件报告...")
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = self.email_recipient
            msg['Subject'] = f"RIC变更数据处理报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 生成报告内容
            if success:
                status = "✅ 成功"
                report_content = f"""RIC变更数据处理报告

处理状态: {status}
处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
处理文件: {file_path.name if file_path else 'N/A'}
AU记录数量: {au_record_count}
SFTP上传结果: {upload_result}

详细信息:
- 原始文件下载: 成功
- AU数据筛选: 成功 (筛选出 {au_record_count} 条记录)
- 文件保存: 成功
- SFTP上传: {'成功' if '成功' in upload_result else '失败'}
- Downloads清理: 已完成

文件保存位置: {file_path if file_path else 'N/A'}
远程服务器: {self.sftp_host}:{self.sftp_remote_dir}

---
此邮件由RIC变更数据自动处理程序发送"""
            else:
                status = "❌ 失败"
                report_content = f"""RIC变更数据处理报告

处理状态: {status}
处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
错误信息: {upload_result}

处理步骤:
- 文件下载: {'成功' if file_path else '失败'}
- AU数据筛选: {'成功' if file_path else '未执行'}
- SFTP上传: 失败

建议操作:
1. 检查网络连接
2. 验证SFTP服务器状态
3. 确认下载文件完整性
4. 程序将在5分钟后自动重试

---
此邮件由RIC变更数据自动处理程序发送"""
            
            msg.attach(MIMEText(report_content, 'plain', 'utf-8'))
            
            # 显示邮件内容
            print("📧 邮件内容预览:")
            print("=" * 50)
            print(report_content)
            print("=" * 50)
            
            # 发送邮件
            if self.enable_email:
                try:
                    print(f"📨 正在通过163邮箱发送邮件...")
                    print(f"   发件人: {self.email_sender}")
                    print(f"   收件人: {self.email_recipient}")
                    
                    # 连接163 SMTP服务器 (使用SSL)
                    if self.smtp_port == 465:
                        server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
                    else:
                        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                        server.starttls()  # 启用安全传输
                    server.login(self.email_sender, self.email_password)
                    
                    # 发送邮件
                    text = msg.as_string()
                    server.sendmail(self.email_sender, self.email_recipient, text)
                    server.quit()
                    
                    print("✅ 163邮件发送成功！")
                    
                except Exception as email_error:
                    print(f"❌ 163邮件发送失败: {email_error}")
                    print("💡 请检查163邮箱配置：")
                    print("   1. 确认邮箱地址和密码正确")
                    print("   2. 确认已开启SMTP服务")
                    print("   3. 检查网络连接")
                    print("   4. 确认防火墙没有阻止SMTP连接")
                    print("💡 163邮箱可能需要开启授权码：")
                    print("   - 登录163邮箱 -> 设置 -> 客户端授权密码")
                    print("   - 开启SMTP服务并获取授权码")
            else:
                print("⚠️ 邮件发送已禁用，如需启用请在配置文件中设置 enable_email=true")
            
        except Exception as e:
            print(f"❌ 邮件处理时出错: {e}")
    
    def process_downloaded_file(self):
        """处理下载的文件，包含SFTP上传"""
        print("\n" + "="*50)
        print("📁 开始文件处理流程...")
        print("="*50)
        
        au_record_count = 0
        processed_file = None
        upload_success = False
        upload_message = ""
        
        try:
            # 确保目标目录存在
            self.ensure_target_directory()
            
            # 等待并检查下载的文件（智能检测）
            source_file = self.wait_for_download_completion(max_wait_time=90)  # 等待90秒
            if not source_file:
                upload_message = "下载文件未找到或下载超时"
                self.send_email_report(False, None, upload_message, 0)
                return False
            
            # 处理Excel文件
            processed_file = self.process_excel_file(source_file)
            if not processed_file:
                upload_message = "Excel文件处理失败"
                self.send_email_report(False, source_file, upload_message, 0)
                return False
            
            # 读取处理后的文件以获取记录数
            try:
                df = pd.read_excel(processed_file)
                au_record_count = len(df)
                print(f"📊 处理完成，共 {au_record_count} 条AU记录")
            except:
                au_record_count = 0
            
            # SFTP上传文件
            upload_success, upload_message = self.upload_file_via_sftp(processed_file)
            
            # 清理Downloads目录
            self.cleanup_downloads()
            
            # 发送邮件报告
            self.send_email_report(upload_success, processed_file, upload_message, au_record_count)
            
            if upload_success:
                print(f"🎉 完整流程执行成功!")
                print(f"   - AU记录: {au_record_count} 条")
                print(f"   - 本地文件: {processed_file}")
                print(f"   - SFTP状态: 成功")
                return True
            else:
                print(f"❌ SFTP上传失败: {upload_message}")
                return False
                
        except Exception as e:
            error_message = f"文件处理过程中发生错误: {e}"
            print(f"❌ {error_message}")
            self.send_email_report(False, processed_file, error_message, au_record_count)
            return False
        
    def setup_driver(self):
        """配置浏览器驱动"""
        chrome_options = Options()
        
        # 禁用密码保存和自动填充
        chrome_options.add_argument("--disable-password-manager-reauthentication")
        chrome_options.add_argument("--disable-save-password-bubble")
        chrome_options.add_argument("--disable-password-generation")
        chrome_options.add_argument("--disable-autofill")
        chrome_options.add_argument("--disable-autofill-keyboard-accessory-view")
        chrome_options.add_argument("--disable-full-form-autofill-ios")
        
        # 禁用 Cookie 弹窗和隐私通知
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
        
        # 强力禁用所有弹窗和覆盖层
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
        
        # 阻止 OneTrust 和其他 Cookie 管理工具
        chrome_options.add_argument("--disable-permissions-api")
        chrome_options.add_argument("--disable-site-isolation-trials")
        chrome_options.add_argument("--disable-features=VizServiceDisplayCompositor,VizDisplayCompositor")
        chrome_options.add_argument("--aggressive-cache-discard")
        chrome_options.add_argument("--disable-partial-raster")
        chrome_options.add_argument("--disable-skia-runtime-opts")
        chrome_options.add_argument("--disable-checking-optimization-guide-user-permissions")
        chrome_options.add_argument("--disable-back-forward-cache")
        
        # 添加用户首选项禁用密码保存和 Cookie 弹窗
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.default_content_setting_values.cookies": 1,  # 允许 cookies 但不显示弹窗
            "profile.cookie_controls_mode": 0,  # 禁用 cookie 控制
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
        
        # 其他设置
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 窗口大小设置
        chrome_options.add_argument("--window-size=1051,805")
        
        # 禁用GPU加速（有时候可以解决一些问题）
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        print("🚀 正在启动Chrome浏览器...")
        
        try:
            # 尝试使用手动下载的chromedriver
            driver_path = os.path.join(os.getcwd(), "drivers", "chromedriver.exe")
            if os.path.exists(driver_path):
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                print("✅ Chrome浏览器启动成功（使用手动下载的驱动）")
            else:
                # 使用Selenium 4的自动驱动管理
                self.driver = webdriver.Chrome(options=chrome_options)
                print("✅ Chrome浏览器启动成功（使用自动驱动管理）")
            
            # 执行脚本来进一步禁用自动保存
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, self.timeout)
            
        except Exception as e:
            print(f"❌ 无法启动Chrome浏览器: {e}")
            print("💡 请确保已安装Chrome浏览器")
            print("💡 如果问题持续，请尝试更新Chrome到最新版本")
            raise
        
    def login(self):
        """执行登录流程"""
        try:
            print("🚀 开始登录流程...")
            
            # 0. 设置浏览器驱动
            self.setup_driver()
            
            # 1. 访问目标网站
            target_url = "https://myaccount.lseg.com/en/symbolchanges"
            print(f"📍 访问目标网站: {target_url}")
            self.driver.get(target_url)
            
            # 等待页面跳转到登录页面
            print("⏳ 等待跳转到登录页面...")
            time.sleep(5)
            
            # 2. 输入用户名
            print("👤 输入用户名...")
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "AAA-AS-SI1-SE003"))
            )
            username_field.clear()
            username_field.send_keys(self.username)
            
            # 3. 输入密码
            print("🔒 输入密码...")
            password_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "AAA-AS-SI1-SE006"))
            )
            password_field.clear()
            password_field.send_keys(self.password)
            
            # 4. 按Enter键登录（根据新录制）
            print("⏎ 按Enter键登录...")
            password_field.send_keys(Keys.RETURN)
            
            # 5. 等待页面跳转
            print("⏳ 等待登录页面跳转...")
            time.sleep(3)
            
            # 6. 点击复选框
            print("☑️ 点击复选框...")
            try:
                checkbox = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".ui-checkbox__bg"))
                )
                checkbox.click()
                print("✅ 复选框已点击")
                time.sleep(1)
            except TimeoutException:
                print("⚠️ 复选框未找到，继续下一步...")
            
            # 7. 等待terms-of-use页面加载并处理Cookie弹窗
            print("⏳ 等待terms-of-use页面加载...")
            time.sleep(3)
            
            # 检查是否到达terms-of-use页面
            current_url = self.driver.current_url if self.driver else ""
            if "terms-of-use" in current_url.lower():
                print("📄 已到达terms-of-use页面，处理Cookie弹窗...")
                self.handle_onetrust_cookie_popup()
            else:
                print(f"⚠️ 当前页面: {current_url}，尝试处理Cookie弹窗...")
                self.handle_onetrust_cookie_popup()
            
            # 8. 点击Accept and Continue按钮
            print("✅ 点击Accept and Continue...")
            try:
                accept_button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#instrumentchange > span"))
                )
                accept_button.click()
                print("✅ Accept and Continue按钮已点击")
                time.sleep(2)
            except TimeoutException:
                print("⚠️ Accept and Continue按钮未找到...")
            
            # 9. 【关键新步骤】点击SVG图标进行导航
            print("🧭 点击SVG图标进行导航...")
            try:
                # 等待页面完全加载
                time.sleep(2)
                
                # 尝试多种方式点击SVG图标
                svg_selectors = [
                    ".sc-hqyNC:nth-child(1) svg",  # 原始选择器
                    ".sc-hqyNC:nth-child(1)",      # 父容器
                    ".sc-hqyNC svg",               # 更通用的选择器
                    ".sc-hqyNC",                   # 容器本身
                ]
                
                clicked = False
                for selector in svg_selectors:
                    try:
                        svg_icon = self.wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        # 尝试常规点击
                        svg_icon.click()
                        print(f"✅ SVG图标已点击 (选择器: {selector})")
                        clicked = True
                        break
                    except Exception as e:
                        print(f"⚠️ 选择器 {selector} 失败: {e}")
                        continue
                
                if not clicked:
                    print("⚠️ 所有SVG选择器都失败")
                else:
                    time.sleep(3)  # 等待导航完成
                    
            except Exception as e:
                print(f"⚠️ SVG图标点击失败: {e}")
            
            # 10. 点击Apply按钮
            print("📋 点击Apply按钮...")
            try:
                apply_button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".sc-VJcYb"))
                )
                apply_button.click()
                print("✅ Apply按钮已点击")
            except TimeoutException:
                print("⚠️ Apply按钮未找到...")
            
            # 11. 等待最终页面加载
            print("⏳ 等待最终页面加载...")
            time.sleep(5)
            
            # 检查登录状态
            current_url = self.driver.current_url
            print(f"🌐 当前页面URL: {current_url}")
            
            if "symbolchanges" in current_url.lower() or "myaccount.lseg.com" in current_url.lower():
                print("🎉 登录成功！")
                return True
            else:
                print("❓ 登录状态未确定，请检查页面")
                return False
                
        except TimeoutException as e:
            print(f"❌ 登录超时: {e}")
            return False
        except Exception as e:
            print(f"❌ 登录过程中发生错误: {e}")
            return False
    
    def get_page_info(self):
        """获取当前页面信息"""
        try:
            title = self.driver.title
            url = self.driver.current_url
            print(f"📄 页面标题: {title}")
            print(f"🌐 页面URL: {url}")
            
            # 查找可能的下载按钮和链接
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
                print(f"📥 找到 {len(found_downloads)} 个可能的下载元素")
                for i, item in enumerate(found_downloads[:10]):  # 只显示前10个
                    href_info = f" -> {item['href']}" if item['href'] else ""
                    print(f"  {i+1}. [{item['tag']}] '{item['text']}'{href_info}")
            else:
                print("🔍 未找到明显的下载按钮")
                
            # 查找所有可能包含下载功能的元素
            all_elements = self.driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'symbol') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'change') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'instrument')]")
            
            if all_elements:
                print(f"🔍 找到 {len(all_elements)} 个包含关键词的元素")
                for i, element in enumerate(all_elements[:10]):  # 只显示前10个
                    try:
                        text = element.text.strip()
                        if text and len(text) < 100:  # 只显示短文本
                            print(f"  {i+1}. [{element.tag_name}] '{text}'")
                    except:
                        pass
                
        except Exception as e:
            print(f"❌ 获取页面信息时发生错误: {e}")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            print("🔚 关闭浏览器...")
            self.driver.quit()

    def run_with_retry(self, max_retries=3, retry_delay=300):
        """
        运行程序，包含重试机制
        max_retries: 最大重试次数
        retry_delay: 重试间隔(秒)，默认5分钟
        """
        self.logger.info("🚀 开始LSEG自动下载和文件处理程序...")
        self.logger.info(f"📋 配置信息:")
        self.logger.info(f"   - 下载目录: {self.downloads_path}")
        self.logger.info(f"   - 目标目录: {self.target_dir}")
        self.logger.info(f"   - SFTP服务器: {self.sftp_host}:{self.sftp_remote_dir}")
        self.logger.info(f"   - 邮件收件人: {self.email_recipient}")
        
        # 检查今天是否已经成功执行过
        self.logger.info("🔍 检查今日是否已执行...")
        already_executed, reason = self.check_today_execution()
        
        if already_executed:
            self.logger.info(f"⏹️ 程序今日已成功执行，跳过运行")
            self.logger.info(f"   原因: {reason}")
            print(f"⏹️ 程序今日已成功执行，跳过运行")
            print(f"   原因: {reason}")
            print(f"   如需强制重新执行，请删除今日日志文件或远程文件")
            return True
        
        self.logger.info("▶️ 今日尚未执行，开始运行程序...")
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"\n📍 第 {attempt + 1} 次尝试 (共 {max_retries} 次)")
                print(f"\n📍 第 {attempt + 1} 次尝试 (共 {max_retries} 次)")
                
                # 执行登录和下载
                if self.login():
                    self.logger.info("✅ 登录和页面导航成功")
                    print("✅ 登录和页面导航成功")
                    
                    # 处理下载的文件（包含智能下载等待、SFTP上传和邮件发送）
                    if self.process_downloaded_file():
                        self.logger.info("🎉 完整程序执行成功！")
                        print("🎉 完整程序执行成功！")
                        return True
                    else:
                        self.logger.error("❌ 文件下载、处理或上传失败")
                        print("❌ 文件下载、处理或上传失败")
                else:
                    self.logger.error("❌ 登录或页面导航失败")
                    print("❌ 登录或页面导航失败")
                    
            except Exception as e:
                self.logger.error(f"❌ 程序执行出错: {e}")
                print(f"❌ 程序执行出错: {e}")
            
            finally:
                # 关闭浏览器
                if self.driver:
                    try:
                        self.driver.quit()
                        self.logger.info("🔚 关闭浏览器...")
                        print("🔚 关闭浏览器...")
                    except:
                        pass
                    self.driver = None
                    self.wait = None
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                self.logger.warning(f"⏳ {retry_delay//60} 分钟后重试...")
                print(f"⏳ {retry_delay//60} 分钟后重试...")
                # 发送重试通知邮件
                self.send_email_report(False, None, f"第 {attempt + 1} 次尝试失败，将在 {retry_delay//60} 分钟后重试", 0)
                time.sleep(retry_delay)
        
        self.logger.error("❌ 所有尝试都失败了，程序退出")
        print("❌ 所有尝试都失败了，程序退出")
        # 发送最终失败邮件
        self.send_email_report(False, None, f"程序执行失败，已尝试 {max_retries} 次", 0)
        return False

def main():
    """主函数"""
    automation = LSEGLoginAutomation()
    try:
        success = automation.run_with_retry(max_retries=3, retry_delay=300)  # 5分钟重试间隔
        
        if success:
            print("\n🎉 程序执行成功完成，即将退出...")
        else:
            print("\n❌ 程序执行失败，即将退出...")
    
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断程序...")
    
    except Exception as e:
        print(f"\n❌ 程序发生未处理的错误: {e}")
    
    finally:
        # 强制清理所有资源
        try:
            if hasattr(automation, 'driver') and automation.driver:
                automation.driver.quit()
                print("🔧 强制关闭浏览器驱动...")
        except:
            pass
        
        print("🏁 程序完全退出")
        
        # 强制退出程序
        import sys
        sys.exit(0)

if __name__ == "__main__":
    main() 