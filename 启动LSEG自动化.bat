@echo off
chcp 65001 >nul
echo =========================================
echo    LSEG自动化程序启动脚本
echo =========================================
echo.

:: 设置脚本所在目录为工作目录
cd /d "%~dp0"
echo 📁 工作目录: %CD%

:: 检查Python是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到Python，请确保Python已安装并在PATH中
    echo.
    echo 💡 提示: 
    echo    1. 安装Python 3.8+
    echo    2. 安装时勾选 "Add Python to PATH"
    echo    3. 或手动将Python添加到系统PATH
    echo.
    pause
    exit /b 1
)

:: 显示Python版本信息
echo 🐍 Python版本信息:
python --version
echo.

:: 检查配置文件是否存在
if not exist "config.cnf" (
    echo ❌ 错误: 未找到配置文件 config.cnf
    echo.
    echo 💡 提示: 请确保 config.cnf 文件存在并包含正确的配置信息
    echo.
    pause
    exit /b 1
)

:: 检查主程序文件是否存在
if not exist "lseg_login_simple.py" (
    echo ❌ 错误: 未找到主程序文件 lseg_login_simple.py
    echo.
    pause
    exit /b 1
)

:: 创建日志目录
if not exist "logs" mkdir logs

:: 获取当前日期时间
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%-%MM%-%DD% %HH%:%Min%:%Sec%"

echo ⏰ 启动时间: %timestamp%
echo.

:: 记录启动到日志文件
set "startup_log=logs\startup_%YYYY%%MM%%DD%.log"
echo [%timestamp%] 启动LSEG自动化程序 >> "%startup_log%"
echo [%timestamp%] 工作目录: %CD% >> "%startup_log%"

:: 检查是否在计划任务中运行（通过检查环境变量）
if "%SESSIONNAME%"=="Console" (
    set "INTERACTIVE=1"
    echo 🖱️ 运行模式: 交互模式（双击启动）
) else (
    set "INTERACTIVE=0"
    echo 🤖 运行模式: 后台模式（计划任务）
)
echo.

echo 🚀 正在启动LSEG自动化程序...
echo ========================================
echo.

:: 运行Python程序并捕获退出代码
python lseg_login_simple.py
set "exit_code=%errorlevel%"

echo.
echo ========================================

:: 根据退出代码显示结果
if %exit_code% equ 0 (
    echo ✅ 程序执行完成 ^(退出代码: %exit_code%^)
    echo [%timestamp%] 程序执行成功 ^(退出代码: %exit_code%^) >> "%startup_log%"
) else (
    echo ❌ 程序执行失败 ^(退出代码: %exit_code%^)
    echo [%timestamp%] 程序执行失败 ^(退出代码: %exit_code%^) >> "%startup_log%"
)

:: 获取结束时间
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "end_timestamp=%dt:~0,4%-%dt:~4,2%-%dt:~6,2% %dt:~8,2%:%dt:~10,2%:%dt:~12,2%"
echo ⏰ 结束时间: %end_timestamp%
echo [%end_timestamp%] 程序结束 >> "%startup_log%"

:: 交互模式下暂停，让用户查看结果
if "%INTERACTIVE%"=="1" (
    echo.
    echo 💡 程序执行完成，按任意键退出...
    pause >nul
)

exit /b %exit_code% 