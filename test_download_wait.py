#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试下载等待功能
"""

import os
import time
from pathlib import Path

# 模拟智能下载等待功能
def wait_for_download_completion(downloads_path, max_wait_time=60):
    """智能等待下载完成"""
    print(f"⏳ 智能等待下载完成（最多等待{max_wait_time}秒）...")
    
    start_time = time.time()
    check_interval = 2  # 每2秒检查一次
    
    while time.time() - start_time < max_wait_time:
        # 检查Downloads目录中的所有xlsx文件
        xlsx_files = list(downloads_path.glob("*.xlsx"))
        
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
    xlsx_files = list(downloads_path.glob("*.xlsx"))
    if xlsx_files:
        latest_file = max(xlsx_files, key=lambda f: f.stat().st_mtime)
        print(f"📁 使用最新文件: {latest_file.name}")
        return latest_file
    
    return None

def main():
    """测试下载等待功能"""
    downloads_path = Path("C:/Users/jacky/Downloads")
    
    print("🧪 测试智能下载等待功能")
    print(f"📁 监控目录: {downloads_path}")
    print("=" * 50)
    
    # 检查当前Downloads目录状态
    xlsx_files = list(downloads_path.glob("*.xlsx"))
    if xlsx_files:
        print(f"📄 当前已有 {len(xlsx_files)} 个xlsx文件:")
        for file in xlsx_files:
            size = file.stat().st_size
            mtime = time.ctime(file.stat().st_mtime)
            print(f"   - {file.name} ({size} 字节, {mtime})")
    else:
        print("📂 Downloads目录中没有xlsx文件")
    
    print("\n开始等待测试...")
    result = wait_for_download_completion(downloads_path, max_wait_time=30)
    
    if result:
        print(f"\n🎉 测试成功! 找到文件: {result}")
        print(f"   大小: {result.stat().st_size} 字节")
        print(f"   修改时间: {time.ctime(result.stat().st_mtime)}")
    else:
        print(f"\n❌ 测试失败: 没有找到合适的文件")

if __name__ == "__main__":
    main() 