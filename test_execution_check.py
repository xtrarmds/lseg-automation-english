#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试程序执行检查功能
"""

import os
import configparser
from datetime import datetime
from pathlib import Path
from lseg_login_simple import LSEGLoginAutomation

def test_execution_check():
    """测试执行检查功能"""
    print("🧪 测试程序执行检查功能")
    print("="*50)
    
    try:
        # 创建自动化实例（这会自动设置日志）
        automation = LSEGLoginAutomation()
        
        print(f"📁 日志文件位置: {automation.log_file}")
        
        # 测试检查今日执行状态
        print("\n🔍 检查今日执行状态...")
        already_executed, reason = automation.check_today_execution()
        
        if already_executed:
            print(f"✅ 今日已执行: {reason}")
        else:
            print(f"⏸️ 今日未执行: {reason}")
        
        # 显示日志目录内容
        log_dir = Path("logs")
        if log_dir.exists():
            print(f"\n📋 日志目录内容 ({log_dir}):")
            for log_file in log_dir.glob("*.log"):
                size = log_file.stat().st_size
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                print(f"   - {log_file.name} ({size} 字节, {mtime})")
        else:
            print("\n📂 日志目录不存在")
        
        # 显示今日日志内容（如果存在）
        today = datetime.now().strftime("%Y%m%d")
        today_log = log_dir / f"lseg_automation_{today}.log"
        
        if today_log.exists():
            print(f"\n📄 今日日志内容 ({today_log.name}):")
            print("-" * 40)
            try:
                with open(today_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines[-10:], 1):  # 显示最后10行
                        print(f"{len(lines)-10+i:2d}: {line.rstrip()}")
            except Exception as e:
                print(f"❌ 读取日志失败: {e}")
            print("-" * 40)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def simulate_successful_execution():
    """模拟成功执行，在日志中写入成功标记"""
    print("\n🎭 模拟成功执行（写入成功标记到日志）")
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    today = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"lseg_automation_{today}.log"
    
    # 写入模拟的成功执行记录
    with open(log_file, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"\n{timestamp} - INFO - 🎭 模拟测试执行\n")
        f.write(f"{timestamp} - INFO - ✅ 登录和页面导航成功\n")
        f.write(f"{timestamp} - INFO - 📊 处理完成，共 123 条AU记录\n")
        f.write(f"{timestamp} - INFO - 📤 SFTP上传成功\n")
        f.write(f"{timestamp} - INFO - 🎉 完整程序执行成功！\n")
    
    print(f"✅ 已写入成功标记到: {log_file}")

def clear_today_logs():
    """清理今日日志"""
    print("\n🧹 清理今日日志文件")
    
    log_dir = Path("logs")
    today = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"lseg_automation_{today}.log"
    
    if log_file.exists():
        log_file.unlink()
        print(f"✅ 已删除: {log_file}")
    else:
        print(f"ℹ️ 文件不存在: {log_file}")

def main():
    """主测试函数"""
    print("🧪 LSEG自动化程序执行检查测试")
    print("="*60)
    
    while True:
        print("\n请选择测试选项:")
        print("1. 检查今日执行状态")
        print("2. 模拟成功执行（写入成功标记）")
        print("3. 清理今日日志")
        print("4. 查看日志目录")
        print("0. 退出")
        
        choice = input("\n请输入选项 (0-4): ").strip()
        
        if choice == "1":
            test_execution_check()
        elif choice == "2":
            simulate_successful_execution()
        elif choice == "3":
            clear_today_logs()
        elif choice == "4":
            log_dir = Path("logs")
            if log_dir.exists():
                print(f"\n📁 日志目录: {log_dir.absolute()}")
                files = list(log_dir.glob("*.log"))
                if files:
                    for file in files:
                        size = file.stat().st_size
                        mtime = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                        print(f"   - {file.name} ({size} 字节, {mtime})")
                else:
                    print("   📂 目录为空")
            else:
                print("\n📂 日志目录不存在")
        elif choice == "0":
            print("👋 退出测试")
            break
        else:
            print("❌ 无效选项，请重新选择")

if __name__ == "__main__":
    main() 