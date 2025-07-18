# LSEG Automation Program - PowerShell Startup Script
# English Version

# Set console title
$Host.UI.RawUI.WindowTitle = "LSEG Automation Program"

# Function to write colored output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Function to check if command exists
function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to check if file exists
function Test-FileExists {
    param([string]$Path)
    return Test-Path $Path
}

# Function to create directory if not exists
function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-ColorOutput "✅ Created directory: $Path" "Green"
    } else {
        Write-ColorOutput "✅ Directory exists: $Path" "Green"
    }
}

# Main execution
try {
    Write-ColorOutput "========================================" "Cyan"
    Write-ColorOutput "    LSEG Automation Program Startup" "Cyan"
    Write-ColorOutput "========================================" "Cyan"
    Write-Host ""

    # Step 1: Check Python installation
    Write-ColorOutput "[1/5] Checking Python installation..." "Yellow"
    if (Test-Command "python") {
        $pythonVersion = python --version 2>&1
        Write-ColorOutput "✅ Python found: $pythonVersion" "Green"
    } else {
        Write-ColorOutput "❌ Python is not installed or not in PATH" "Red"
        Write-ColorOutput "💡 Please install Python 3.7+ and add it to PATH" "Yellow"
        Write-ColorOutput "💡 Download from: https://www.python.org/downloads/" "Yellow"
        Read-Host "Press Enter to exit"
        exit 1
    }

    # Step 2: Check virtual environment
    Write-Host ""
    Write-ColorOutput "[2/5] Checking virtual environment..." "Yellow"
    if (-not (Test-FileExists ".venv")) {
        Write-ColorOutput "⚠️ Virtual environment not found, creating..." "Yellow"
        try {
            python -m venv .venv
            Write-ColorOutput "✅ Virtual environment created" "Green"
        }
        catch {
            Write-ColorOutput "❌ Failed to create virtual environment" "Red"
            Read-Host "Press Enter to exit"
            exit 1
        }
    } else {
        Write-ColorOutput "✅ Virtual environment found" "Green"
    }

    # Step 3: Activate virtual environment and install dependencies
    Write-Host ""
    Write-ColorOutput "[3/5] Activating virtual environment and installing dependencies..." "Yellow"
    
    # Activate virtual environment
    $activateScript = ".venv\Scripts\Activate.ps1"
    if (Test-FileExists $activateScript) {
        & $activateScript
        Write-ColorOutput "✅ Virtual environment activated" "Green"
    } else {
        Write-ColorOutput "❌ Failed to activate virtual environment" "Red"
        Read-Host "Press Enter to exit"
        exit 1
    }

    # Upgrade pip
    Write-ColorOutput "Upgrading pip..." "Yellow"
    python -m pip install --upgrade pip

    # Install required packages
    Write-ColorOutput "Installing required packages..." "Yellow"
    if (Test-FileExists "requirements.txt") {
        try {
            pip install -r requirements.txt
            Write-ColorOutput "✅ Dependencies installed successfully" "Green"
        }
        catch {
            Write-ColorOutput "❌ Failed to install dependencies" "Red"
            Write-ColorOutput "💡 Please check requirements.txt file" "Yellow"
            Read-Host "Press Enter to exit"
            exit 1
        }
    } else {
        Write-ColorOutput "⚠️ requirements.txt not found, skipping dependency installation" "Yellow"
    }

    # Step 4: Check configuration file
    Write-Host ""
    Write-ColorOutput "[4/5] Checking configuration file..." "Yellow"
    if (-not (Test-FileExists "config.cnf")) {
        Write-ColorOutput "❌ Configuration file config.cnf not found" "Red"
        Write-ColorOutput "💡 Please create config.cnf file with proper settings" "Yellow"
        Read-Host "Press Enter to exit"
        exit 1
    } else {
        Write-ColorOutput "✅ Configuration file found" "Green"
    }

    # Step 5: Create necessary directories
    Write-Host ""
    Write-ColorOutput "[5/5] Creating necessary directories..." "Yellow"
    Ensure-Directory "logs"
    Ensure-Directory "downloads"
    Ensure-Directory "target"
    Ensure-Directory "drivers"

    # Check Chrome driver
    Write-Host ""
    Write-ColorOutput "Checking Chrome driver..." "Yellow"
    if (-not (Test-FileExists "drivers\chromedriver.exe")) {
        Write-ColorOutput "⚠️ Chrome driver not found in drivers folder" "Yellow"
        Write-ColorOutput "💡 Selenium will attempt to download automatically" "Yellow"
        Write-ColorOutput "💡 For manual installation, download from: https://chromedriver.chromium.org/" "Yellow"
    } else {
        Write-ColorOutput "✅ Chrome driver found" "Green"
    }

    Write-Host ""
    Write-ColorOutput "========================================" "Cyan"
    Write-ColorOutput "    Starting LSEG Automation Program" "Cyan"
    Write-ColorOutput "========================================" "Cyan"
    Write-Host ""

    # Run the automation program
    Write-ColorOutput "🚀 Starting automation program..." "Green"
    
    # Check if English version exists, otherwise use Chinese version
    if (Test-FileExists "lseg_login_english.py") {
        python lseg_login_english.py
    } elseif (Test-FileExists "lseg_login_simple.py") {
        Write-ColorOutput "⚠️ English version not found, using Chinese version..." "Yellow"
        python lseg_login_simple.py
    } else {
        Write-ColorOutput "❌ No automation script found" "Red"
        Write-ColorOutput "💡 Please ensure lseg_login_english.py or lseg_login_simple.py exists" "Yellow"
        Read-Host "Press Enter to exit"
        exit 1
    }

    # Check program exit code
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-ColorOutput "✅ Program execution completed" "Green"
    } else {
        Write-Host ""
        Write-ColorOutput "❌ Program execution failed" "Red"
        Write-ColorOutput "💡 Check logs for detailed error information" "Yellow"
    }

}
catch {
    Write-ColorOutput "❌ An error occurred: $($_.Exception.Message)" "Red"
    Write-ColorOutput "💡 Please check the error details above" "Yellow"
}
finally {
    Write-Host ""
    Write-ColorOutput "Press any key to exit..." "Cyan"
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} 