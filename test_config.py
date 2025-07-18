#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件测试脚本
验证config.cnf是否能正确加载
"""

import os
import configparser

def test_config():
    """测试配置文件加载"""
    print("🧪 测试配置文件加载...")
    
    config_file = 'config.cnf'
    
    # 检查文件是否存在
    if not os.path.exists(config_file):
        print(f"❌ 配置文件 {config_file} 不存在！")
        return False
    
    config = configparser.ConfigParser()
    
    try:
        # 读取配置文件
        config.read(config_file, encoding='utf-8')
        print(f"✅ 配置文件 {config_file} 读取成功")
        
        # 测试各个配置段
        sections = ['lseg_login', 'sftp', 'email', 'paths']
        
        for section in sections:
            if config.has_section(section):
                print(f"✅ 配置段 [{section}] 存在")
                for key, value in config.items(section):
                    # 隐藏密码显示
                    if 'password' in key.lower():
                        display_value = '*' * len(value)
                    else:
                        display_value = value
                    print(f"   {key} = {display_value}")
            else:
                print(f"❌ 配置段 [{section}] 不存在")
                return False
        
        # 测试关键配置项
        print("\n🔍 验证关键配置项...")
        
        # LSEG登录
        username = config.get('lseg_login', 'username')
        password = config.get('lseg_login', 'password')
        print(f"🔐 LSEG账户: {username} / {'*' * len(password)}")
        
        # SFTP配置
        sftp_host = config.get('sftp', 'host')
        sftp_user = config.get('sftp', 'username')
        sftp_pass = config.get('sftp', 'password')
        sftp_dir = config.get('sftp', 'remote_dir')
        print(f"📤 SFTP: {sftp_user}@{sftp_host}:{sftp_dir} / {'*' * len(sftp_pass)}")
        
        # 邮件配置
        smtp_server = config.get('email', 'smtp_server')
        smtp_port = config.getint('email', 'smtp_port')
        email_sender = config.get('email', 'sender')
        email_pass = config.get('email', 'password')
        email_recipient = config.get('email', 'recipient')
        enable_email = config.getboolean('email', 'enable_email')
        print(f"📧 邮件: {email_sender} -> {email_recipient}")
        print(f"📧 SMTP: {smtp_server}:{smtp_port} / {'*' * len(email_pass)}")
        print(f"📧 启用: {enable_email}")
        
        # 路径配置
        downloads_path = config.get('paths', 'downloads_path')
        target_dir = config.get('paths', 'target_dir')
        target_file = config.get('paths', 'target_file')
        print(f"📁 下载路径: {downloads_path}")
        print(f"📁 目标目录: {target_dir}")
        print(f"📁 目标文件: {target_file}")
        
        print("\n✅ 配置文件验证通过！")
        return True
        
    except Exception as e:
        print(f"❌ 配置文件读取失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 LSEG配置文件测试程序")
    print("=" * 50)
    
    if test_config():
        print("\n🎉 配置测试成功！可以运行主程序了。")
    else:
        print("\n❌ 配置测试失败！请检查config.cnf文件。") 