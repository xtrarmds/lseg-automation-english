@echo off
chcp 65001 >nul

echo ========================================
echo         启动脚本测试工具
echo ========================================
echo.

cd /d "%~dp0"
echo 📁 当前目录: %CD%
echo.

echo 请选择要测试的启动脚本:
echo.
echo 1. 测试批处理脚本 (启动LSEG自动化.bat)
echo 2. 测试PowerShell脚本 (启动LSEG自动化.ps1)
echo 3. 检查文件完整性
echo 4. 查看日志目录
echo 0. 退出
echo.

set /p choice="请输入选项 (0-4): "

if "%choice%"=="1" goto test_bat
if "%choice%"=="2" goto test_ps1
if "%choice%"=="3" goto check_files
if "%choice%"=="4" goto view_logs
if "%choice%"=="0" goto exit

echo ❌ 无效选项，请重新运行脚本
pause
goto exit

:test_bat
echo.
echo 🧪 测试批处理脚本...
echo ========================================
if exist "启动LSEG自动化.bat" (
    echo ✅ 找到批处理脚本
    echo 🚀 启动测试...
    echo.
    call "启动LSEG自动化.bat"
) else (
    echo ❌ 未找到 启动LSEG自动化.bat 文件
)
goto end

:test_ps1
echo.
echo 🧪 测试PowerShell脚本...
echo ========================================
if exist "启动LSEG自动化.ps1" (
    echo ✅ 找到PowerShell脚本
    echo 🚀 启动测试...
    echo.
    powershell -ExecutionPolicy Bypass -File "启动LSEG自动化.ps1"
) else (
    echo ❌ 未找到 启动LSEG自动化.ps1 文件
)
goto end

:check_files
echo.
echo 🔍 检查文件完整性...
echo ========================================

echo 📋 必需文件检查:
if exist "lseg_login_simple.py" (
    echo ✅ lseg_login_simple.py
) else (
    echo ❌ lseg_login_simple.py - 主程序文件缺失
)

if exist "config.cnf" (
    echo ✅ config.cnf
) else (
    echo ❌ config.cnf - 配置文件缺失
)

if exist "启动LSEG自动化.bat" (
    echo ✅ 启动LSEG自动化.bat
) else (
    echo ❌ 启动LSEG自动化.bat - 批处理启动脚本缺失
)

if exist "启动LSEG自动化.ps1" (
    echo ✅ 启动LSEG自动化.ps1
) else (
    echo ❌ 启动LSEG自动化.ps1 - PowerShell启动脚本缺失
)

echo.
echo 📋 可选文件检查:
if exist "test_execution_check.py" (
    echo ✅ test_execution_check.py - 执行检查测试工具
) else (
    echo ⚠️ test_execution_check.py - 测试工具缺失（可选）
)

if exist "Windows计划任务设置指南.md" (
    echo ✅ Windows计划任务设置指南.md
) else (
    echo ⚠️ Windows计划任务设置指南.md - 文档缺失（可选）
)

echo.
echo 📁 目录检查:
if exist "logs" (
    echo ✅ logs目录存在
) else (
    echo ⚠️ logs目录不存在（程序运行时会自动创建）
)

if exist "processed_files" (
    echo ✅ processed_files目录存在
) else (
    echo ⚠️ processed_files目录不存在（程序运行时会自动创建）
)

echo.
echo 🐍 Python环境检查:
python --version >nul 2>&1
if %errorlevel% equ 0 (
    python --version
    echo ✅ Python环境正常
) else (
    echo ❌ Python未找到或未正确安装
)

goto end

:view_logs
echo.
echo 📋 查看日志目录...
echo ========================================

if exist "logs" (
    echo 📁 日志目录: %CD%\logs
    echo.
    echo 📄 日志文件列表:
    dir /b "logs\*.log" 2>nul
    if %errorlevel% neq 0 (
        echo    （目录为空）
    )
    echo.
    
    echo 📊 目录统计:
    for /f %%i in ('dir "logs\*.log" 2^>nul ^| find "个文件"') do echo    %%i
    
    echo.
    echo 💡 提示: 
    echo    - startup_YYYYMMDD.log - 启动脚本日志
    echo    - lseg_automation_YYYYMMDD.log - 程序执行日志
) else (
    echo ⚠️ logs目录不存在
    echo 💡 提示: 日志目录会在程序首次运行时自动创建
)

goto end

:end
echo.
echo ========================================
pause

:exit 