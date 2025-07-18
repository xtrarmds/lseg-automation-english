# LSEG自动化程序启动脚本 (PowerShell版本)
# 可用于双击运行或Windows计划任务

param(
    [switch]$Silent,  # 静默模式，不显示交互提示
    [switch]$Force    # 强制执行，跳过今日执行检查
)

# 设置控制台编码为UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 设置错误处理
$ErrorActionPreference = "Stop"

function Write-ColoredOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message" -ForegroundColor $Color
}

function Test-Prerequisites {
    Write-ColoredOutput "🔍 检查运行环境..." "Cyan"
    
    # 检查Python
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColoredOutput "🐍 $pythonVersion" "Green"
        } else {
            throw "Python未找到"
        }
    } catch {
        Write-ColoredOutput "❌ 错误: 未找到Python，请确保Python已安装并在PATH中" "Red"
        Write-ColoredOutput "💡 提示: 安装Python 3.8+并确保添加到PATH" "Yellow"
        return $false
    }
    
    # 检查配置文件
    if (-not (Test-Path "config.cnf")) {
        Write-ColoredOutput "❌ 错误: 未找到配置文件 config.cnf" "Red"
        return $false
    }
    
    # 检查主程序文件
    if (-not (Test-Path "lseg_login_simple.py")) {
        Write-ColoredOutput "❌ 错误: 未找到主程序文件 lseg_login_simple.py" "Red"
        return $false
    }
    
    Write-ColoredOutput "✅ 环境检查通过" "Green"
    return $true
}

function Initialize-Environment {
    # 设置工作目录为脚本所在目录
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location $scriptPath
    Write-ColoredOutput "📁 工作目录: $(Get-Location)" "Cyan"
    
    # 创建日志目录
    $logsDir = "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir | Out-Null
        Write-ColoredOutput "📁 创建日志目录: $logsDir" "Cyan"
    }
    
    # 设置启动日志文件
    $dateStr = Get-Date -Format "yyyyMMdd"
    $script:startupLogFile = "logs\startup_$dateStr.log"
}

function Write-StartupLog {
    param([string]$Message)
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] $Message"
    Add-Content -Path $script:startupLogFile -Value $logEntry -Encoding UTF8
}

function Test-IsInteractiveMode {
    # 检查是否在交互模式下运行
    if ($Silent) {
        return $false
    }
    
    # 检查是否从计划任务运行
    $parentProcess = Get-WmiObject -Class Win32_Process -Filter "ProcessId=$PID" | 
                    ForEach-Object { Get-WmiObject -Class Win32_Process -Filter "ProcessId=$($_.ParentProcessId)" }
    
    if ($parentProcess.Name -eq "svchost.exe" -or $parentProcess.Name -eq "taskeng.exe") {
        return $false  # 计划任务模式
    }
    
    return $true  # 交互模式
}

function Start-LSEGAutomation {
    $startTime = Get-Date
    Write-ColoredOutput "🚀 正在启动LSEG自动化程序..." "Green"
    Write-StartupLog "启动LSEG自动化程序"
    
    try {
        # 构建Python命令
        $pythonArgs = @("lseg_login_simple.py")
        
        if ($Force) {
            # 如果强制执行，先清理今日日志
            $today = Get-Date -Format "yyyyMMdd"
            $todayLog = "logs\lseg_automation_$today.log"
            if (Test-Path $todayLog) {
                Remove-Item $todayLog -Force
                Write-ColoredOutput "🧹 清理今日日志文件: $todayLog" "Yellow"
                Write-StartupLog "强制执行: 清理今日日志文件"
            }
        }
        
        # 运行Python程序
        $process = Start-Process -FilePath "python" -ArgumentList $pythonArgs -Wait -PassThru -NoNewWindow
        $exitCode = $process.ExitCode
        
        $endTime = Get-Date
        $duration = $endTime - $startTime
        
        if ($exitCode -eq 0) {
            Write-ColoredOutput "✅ 程序执行成功 (退出代码: $exitCode)" "Green"
            Write-ColoredOutput "⏱️ 执行时间: $($duration.ToString('hh\:mm\:ss'))" "Cyan"
            Write-StartupLog "程序执行成功 (退出代码: $exitCode, 耗时: $($duration.ToString('hh\:mm\:ss')))"
        } else {
            Write-ColoredOutput "❌ 程序执行失败 (退出代码: $exitCode)" "Red"
            Write-ColoredOutput "⏱️ 执行时间: $($duration.ToString('hh\:mm\:ss'))" "Cyan"
            Write-StartupLog "程序执行失败 (退出代码: $exitCode, 耗时: $($duration.ToString('hh\:mm\:ss')))"
        }
        
        return $exitCode
        
    } catch {
        Write-ColoredOutput "❌ 启动程序时发生错误: $($_.Exception.Message)" "Red"
        Write-StartupLog "启动程序时发生错误: $($_.Exception.Message)"
        return 1
    }
}

function Show-CompletionMessage {
    param([int]$ExitCode)
    
    Write-Host ""
    Write-Host "=" * 50 -ForegroundColor Gray
    
    if ($ExitCode -eq 0) {
        Write-ColoredOutput "🎉 LSEG自动化程序执行完成！" "Green"
    } else {
        Write-ColoredOutput "💥 程序执行遇到问题，请检查日志" "Red"
    }
    
    Write-ColoredOutput "📋 详细日志位置:" "Cyan"
    Write-ColoredOutput "   - 启动日志: $script:startupLogFile" "Gray"
    Write-ColoredOutput "   - 程序日志: logs\lseg_automation_$(Get-Date -Format 'yyyyMMdd').log" "Gray"
    
    Write-Host "=" * 50 -ForegroundColor Gray
}

# 主执行流程
try {
    Write-Host ""
    Write-Host "=" * 50 -ForegroundColor Green
    Write-Host "     LSEG自动化程序启动脚本 (PowerShell)" -ForegroundColor Green
    Write-Host "=" * 50 -ForegroundColor Green
    Write-Host ""
    
    # 初始化环境
    Initialize-Environment
    Write-StartupLog "PowerShell启动脚本开始执行"
    
    # 检查运行模式
    $isInteractive = Test-IsInteractiveMode
    if ($isInteractive) {
        Write-ColoredOutput "🖱️ 运行模式: 交互模式 (双击启动)" "Cyan"
    } else {
        Write-ColoredOutput "🤖 运行模式: 后台模式 (计划任务/静默)" "Cyan"
    }
    
    if ($Force) {
        Write-ColoredOutput "⚡ 强制执行模式: 将跳过今日执行检查" "Yellow"
    }
    
    Write-Host ""
    
    # 检查先决条件
    if (-not (Test-Prerequisites)) {
        exit 1
    }
    
    Write-Host ""
    
    # 启动程序
    $exitCode = Start-LSEGAutomation
    
    # 显示完成消息
    Show-CompletionMessage -ExitCode $exitCode
    
    # 交互模式下等待用户输入
    if ($isInteractive -and -not $Silent) {
        Write-Host ""
        Write-ColoredOutput "💡 按任意键退出..." "Yellow"
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
    
    Write-StartupLog "PowerShell启动脚本执行完成 (退出代码: $exitCode)"
    exit $exitCode
    
} catch {
    Write-ColoredOutput "❌ 脚本执行出现严重错误: $($_.Exception.Message)" "Red"
    Write-StartupLog "脚本执行出现严重错误: $($_.Exception.Message)"
    
    if ($isInteractive -and -not $Silent) {
        Write-Host ""
        Write-ColoredOutput "💡 按任意键退出..." "Yellow"
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
    
    exit 1
} 