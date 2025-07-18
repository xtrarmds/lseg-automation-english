#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
163邮箱发送测试脚本
验证授权码是否正确配置
"""

import smtplib
import configparser
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_email_send():
    """测试163邮箱发送功能"""
    print("📧 163邮箱发送测试...")
    
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
        print(f"🌐 SMTP服务器: {smtp_server}:{smtp_port}")
        print(f"🔑 授权码: {'*' * len(password)}")
        
        # 创建测试邮件
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = f"163邮箱测试邮件 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 邮件内容
        content = f"""163邮箱配置测试

测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
发件邮箱: {sender}
SMTP服务器: {smtp_server}:{smtp_port}

✅ 如果您收到这封邮件，说明163邮箱配置成功！

测试内容：
- SMTP连接测试
- 授权码验证测试
- 邮件发送测试

下一步可以运行完整的LSEG自动化程序。

---
此邮件由163邮箱测试程序发送"""
        
        msg.attach(MIMEText(content, 'plain', 'utf-8'))
        
        # 连接并发送邮件
        print("🔗 正在连接163 SMTP服务器...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        
        print("🔐 启用TLS加密...")
        server.starttls()
        
        print("🔑 正在验证授权码...")
        server.login(sender, password)
        
        print("📨 正在发送测试邮件...")
        text = msg.as_string()
        server.sendmail(sender, recipient, text)
        server.quit()
        
        print("✅ 163邮件发送成功！")
        print("📧 请检查邮箱接收测试邮件")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        
        # 提供具体的错误解决方案
        if "Authentication failed" in str(e):
            print("💡 认证失败，可能的原因：")
            print("   1. 授权码错误")
            print("   2. 163邮箱SMTP服务未开启")
            print("   3. 邮箱账户被锁定")
        elif "Connection" in str(e):
            print("💡 连接失败，可能的原因：")
            print("   1. 网络连接问题")
            print("   2. 防火墙阻止端口587")
            print("   3. SMTP服务器地址错误")
        else:
            print("💡 请检查配置文件格式和网络连接")
        
        return False

if __name__ == "__main__":
    print("🧪 163邮箱发送测试程序")
    print("=" * 50)
    
    if test_email_send():
        print("\n🎉 邮件测试成功！现在可以运行完整程序了。")
    else:
        print("\n❌ 邮件测试失败！请检查163邮箱配置。") 