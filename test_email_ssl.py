#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
163邮箱SSL发送测试脚本
尝试使用端口465 SSL连接
"""

import smtplib
import configparser
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_email_ssl():
    """测试163邮箱SSL发送功能"""
    print("📧 163邮箱SSL发送测试...")
    
    # 读取配置
    config = configparser.ConfigParser()
    config.read('config.cnf', encoding='utf-8')
    
    sender = config.get('email', 'sender')
    password = config.get('email', 'password')
    recipient = config.get('email', 'recipient')
    
    print(f"📤 发件人: {sender}")
    print(f"📥 收件人: {recipient}")
    print(f"🔑 授权码: {'*' * len(password)}")
    
    # 尝试不同的SMTP配置
    smtp_configs = [
        {"server": "smtp.163.com", "port": 465, "ssl": True, "name": "163 SSL"},
        {"server": "smtp.163.com", "port": 587, "ssl": False, "name": "163 STARTTLS"},
        {"server": "smtp.163.com", "port": 25, "ssl": False, "name": "163 普通"}
    ]
    
    for config_item in smtp_configs:
        try:
            print(f"\n🔄 尝试 {config_item['name']} ({config_item['server']}:{config_item['port']})")
            
            # 创建测试邮件
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = recipient
            msg['Subject'] = f"163邮箱SSL测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            content = f"""163邮箱SSL配置测试

测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
连接方式: {config_item['name']}
服务器: {config_item['server']}:{config_item['port']}
加密方式: {'SSL' if config_item['ssl'] else 'STARTTLS'}

✅ 此邮件发送成功说明配置正确！

---
此邮件由163邮箱SSL测试程序发送"""
            
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # 连接SMTP服务器
            if config_item['ssl']:
                print("🔐 使用SSL连接...")
                server = smtplib.SMTP_SSL(config_item['server'], config_item['port'])
            else:
                print(f"🔗 连接到 {config_item['server']}:{config_item['port']}")
                server = smtplib.SMTP(config_item['server'], config_item['port'])
                if config_item['port'] == 587:
                    print("🔐 启用STARTTLS...")
                    server.starttls()
            
            print("🔑 验证授权码...")
            server.login(sender, password)
            
            print("📨 发送邮件...")
            text = msg.as_string()
            server.sendmail(sender, recipient, text)
            server.quit()
            
            print(f"✅ {config_item['name']} 发送成功！")
            print("📧 请检查邮箱接收测试邮件")
            return True
            
        except Exception as e:
            print(f"❌ {config_item['name']} 失败: {e}")
            continue
    
    print("\n❌ 所有配置都失败了")
    print("💡 可能的问题：")
    print("   1. 网络连接问题")
    print("   2. 防火墙阻止SMTP端口")
    print("   3. 163邮箱SMTP服务未开启")
    print("   4. 授权码错误")
    print("   5. 邮箱被锁定")
    
    return False

if __name__ == "__main__":
    print("🧪 163邮箱多协议测试程序")
    print("=" * 50)
    
    if test_email_ssl():
        print("\n🎉 邮件测试成功！")
    else:
        print("\n❌ 邮件测试失败！") 