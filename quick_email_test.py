#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速邮件测试 - 模拟完整流程邮件报告
"""

import smtplib
import configparser
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_test_report():
    """发送测试报告邮件"""
    print("📧 发送测试流程报告...")
    
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
        print(f"🌐 SMTP: {smtp_server}:{smtp_port}")
        
        # 创建测试邮件
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = f"RIC变更数据处理报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 模拟成功的报告内容
        report_content = f"""RIC变更数据处理报告

处理状态: ✅ 成功
处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
处理文件: AU_RicChangeEvents_20250717.xlsx
AU记录数量: 27
SFTP上传结果: 文件成功上传到 /home/ian/ricchange/AU_RicChangeEvents_20250717.xlsx

详细信息:
- 原始文件下载: 成功
- AU数据筛选: 成功 (筛选出 27 条记录)
- 文件保存: 成功
- SFTP上传: 成功
- Downloads清理: 已完成

文件保存位置: c:\\ric_change\\AU_RicChangeEvents_20250717.xlsx
远程服务器: 192.168.0.117:/home/ian/ricchange

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
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        
        server.login(sender, password)
        text = msg.as_string()
        server.sendmail(sender, recipient, text)
        server.quit()
        
        print("✅ 163邮件发送成功！")
        print("📧 请检查邮箱 ian.zhu@lseg.com 接收测试邮件")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 快速邮件测试 - 模拟完整流程报告")
    print("=" * 50)
    
    if send_test_report():
        print("\n🎉 邮件发送成功！")
        print("📬 请检查邮箱是否收到RIC变更数据处理报告")
    else:
        print("\n❌ 邮件发送失败！") 