#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速邮件测试 - 模拟失败情况报告
"""

import smtplib
import configparser
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_fail_report():
    """发送失败情况测试报告邮件"""
    print("📧 发送失败情况测试报告...")
    
    # 读取配置
    config = configparser.ConfigParser()
    config.read('config.cnf', encoding='utf-8')
    
    try:
        # 邮件配置
        smtp_server = config.get('email', 'smtp_server')
        smtp_port = config.getint('email', 'smtp_port')
        sender = config.get('email', 'sender')
        password = config.get('email', 'password')
        recipient = config.get('email', 'recipient')
        
        print(f"📤 发件人: {sender}")
        print(f"📥 收件人: {recipient}")
        
        # 创建测试邮件
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = f"RIC变更数据处理报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 模拟失败的报告内容
        report_content = f"""RIC变更数据处理报告

处理状态: ❌ 失败
处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
错误信息: OneTrust Cookie弹窗阻止登录操作

处理步骤:
- 文件下载: 失败
- AU数据筛选: 未执行
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
        
        # 发送邮件 (使用SSL)
        print("📨 正在通过163邮箱发送邮件...")
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender, password)
        text = msg.as_string()
        server.sendmail(sender, recipient, text)
        server.quit()
        
        print("✅ 163邮件发送成功！")
        print("📧 请检查邮箱接收失败情况测试邮件")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 快速邮件测试 - 模拟失败情况报告")
    print("=" * 50)
    
    if send_fail_report():
        print("\n🎉 失败情况邮件发送成功！")
        print("📬 请检查邮箱是否收到失败情况报告")
    else:
        print("\n❌ 邮件发送失败！") 