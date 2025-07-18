# LSEG自动化程序 Git备份使用说明

## 📦 备份文件信息

**Git Bundle文件**: `LSEG_Automation_Git_Bundle_20250718_122042.bundle`
- 文件大小: 8.66 MB  
- 创建时间: 2025-07-18 12:20:42
- 包含内容: 完整的Git仓库历史和所有文件（包括配置文件）

## 🔧 如何使用Git备份

### 1. 恢复完整项目

```bash
# 从bundle文件克隆项目到新目录
git clone LSEG_Automation_Git_Bundle_20250718_122042.bundle LSEG_Automation_Restored

# 进入恢复的目录
cd LSEG_Automation_Restored

# 查看文件列表
ls -la
```

### 2. 在现有Git仓库中导入

```bash
# 验证bundle文件完整性
git bundle verify LSEG_Automation_Git_Bundle_20250718_122042.bundle

# 从bundle文件拉取到现有仓库
git pull LSEG_Automation_Git_Bundle_20250718_122042.bundle master
```

### 3. 查看备份内容

```bash
# 列出bundle中的引用
git bundle list-heads LSEG_Automation_Git_Bundle_20250718_122042.bundle

# 查看提交历史（不需要克隆）
git log --oneline --graph LSEG_Automation_Git_Bundle_20250718_122042.bundle/master
```

## 📋 备份包含的文件

✅ **核心程序文件**:
- `lseg_login_simple.py` - 主程序文件
- `config.cnf` - 配置文件（已包含）
- `requirements.txt` - Python依赖

✅ **文档和说明**:
- `README_CONFIG.md` - 配置说明
- `项目文件说明.md` - 项目文档
- `Windows计划任务设置指南.md` - 任务设置指南
- `LSEG自动化项目开发经验分享.md` - 开发经验

✅ **脚本和工具**:
- `启动LSEG自动化.bat` - Windows批处理启动脚本
- `启动LSEG自动化.ps1` - PowerShell启动脚本
- `测试启动脚本.bat` - 测试脚本

✅ **备份历史文件**:
- `lseg_*.py.bak` - 程序历史版本
- `test_*.py` - 测试文件

## 🚀 推荐使用方式

### 日常开发
```bash
# 1. 从bundle恢复项目
git clone LSEG_Automation_Git_Bundle_20250718_122042.bundle MyLSEG

# 2. 进入项目目录
cd MyLSEG

# 3. 检查配置文件
cat config.cnf

# 4. 安装依赖
pip install -r requirements.txt

# 5. 运行程序
python lseg_login_simple.py
```

### 创建新的备份
```bash
# 在项目目录中
git bundle create LSEG_Backup_$(date +%Y%m%d_%H%M%S).bundle master

# 或者在PowerShell中
git bundle create "LSEG_Backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').bundle" master
```

## 🔒 安全说明

⚠️ **重要提醒**: 
- 此备份**包含配置文件** `config.cnf`
- 如果配置文件中包含敏感信息（密码、密钥等），请妥善保管备份文件
- 建议将备份文件存储在安全的位置，避免泄露

## 🆘 故障恢复

如果原项目损坏或丢失：

1. **完全恢复**:
   ```bash
   git clone LSEG_Automation_Git_Bundle_20250718_122042.bundle LSEG_Recovery
   ```

2. **验证恢复完整性**:
   ```bash
   cd LSEG_Recovery
   git log --oneline
   ls -la
   ```

3. **测试程序**:
   ```bash
   python lseg_login_simple.py --help
   ```

## 📊 Git仓库统计

- **提交数量**: 1个初始提交
- **文件总数**: 27个文件
- **代码行数**: 4,942行
- **分支**: master (主分支)
- **提交ID**: 27b0c2d

---

💡 **提示**: Git Bundle是Git的完整备份格式，包含了所有历史记录、分支和标签信息，是最可靠的代码备份方式。 