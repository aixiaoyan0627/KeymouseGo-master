# KeymouseGo 测试包制作脚本（简化版 - 不含venv）
# 使用方法：在PowerShell中运行 .\build_test_package_simple.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Version = "1.0.0"
$PackageName = "KeymouseGo_Test_v$Version"
$PackageDir = Join-Path $ScriptDir $PackageName

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  KeymouseGo Test Package Builder v$Version" -ForegroundColor Cyan
Write-Host "  (Simple Version - Requires Python installed)" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Clean old package directory
if (Test-Path $PackageDir) {
    Write-Host "[1/7] Cleaning old package directory..." -ForegroundColor Yellow
    Remove-Item -Path $PackageDir -Recurse -Force
    Write-Host "      Deleted: $PackageDir" -ForegroundColor Green
}

# 2. Create package directory
Write-Host "[2/7] Creating package directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $PackageDir | Out-Null
Write-Host "      Created: $PackageDir" -ForegroundColor Green

# 3. Copy main program files
Write-Host "[3/7] Copying main program files..." -ForegroundColor Yellow
$MainFiles = @(
    "KeymouseGo.py",
    "UIFunc.py",
    "UIView.py",
    "UIFileDialogFunc.py",
    "UIFileDialogView.py",
    "assets_rc.py",
    "Mondrian.ico",
    "测试说明.md",
    "问题报告模板.md",
    "requirements.txt"
)
foreach ($File in $MainFiles) {
    $SrcPath = Join-Path $ScriptDir $File
    if (Test-Path $SrcPath) {
        Copy-Item -Path $SrcPath -Destination $PackageDir
        Write-Host "      Copied: $File" -ForegroundColor Green
    } else {
        Write-Host "      Warning: $File not found" -ForegroundColor Red
    }
}

# 4. Copy core modules
Write-Host "[4/7] Copying core modules..." -ForegroundColor Yellow
$Modules = @("Util", "Event", "Recorder", "Plugin")
foreach ($Module in $Modules) {
    $SrcPath = Join-Path $ScriptDir $Module
    if (Test-Path $SrcPath) {
        Copy-Item -Path $SrcPath -Destination $PackageDir -Recurse
        Write-Host "      Copied: $Module/" -ForegroundColor Green
    } else {
        Write-Host "      Warning: $Module/ not found" -ForegroundColor Red
    }
}

# 5. Copy image resources
Write-Host "[5/7] Copying image resources..." -ForegroundColor Yellow
$ImageFolders = @("imgsA", "imgsB", "imgsC", "imgsE", "imgsF", "imgsG")
foreach ($Folder in $ImageFolders) {
    $SrcPath = Join-Path $ScriptDir $Folder
    if (Test-Path $SrcPath) {
        Copy-Item -Path $SrcPath -Destination $PackageDir -Recurse
        Write-Host "      Copied: $Folder/" -ForegroundColor Green
    } else {
        Write-Host "      Warning: $Folder/ not found" -ForegroundColor Red
    }
}

# 6. Copy scripts and configs
Write-Host "[6/7] Copying scripts and configs..." -ForegroundColor Yellow
$ScriptFolders = @("scripts_enhanced", "configs")
foreach ($Folder in $ScriptFolders) {
    $SrcPath = Join-Path $ScriptDir $Folder
    if (Test-Path $SrcPath) {
        Copy-Item -Path $SrcPath -Destination $PackageDir -Recurse
        Write-Host "      Copied: $Folder/" -ForegroundColor Green
    } else {
        Write-Host "      Warning: $Folder/ not found" -ForegroundColor Red
    }
}

# 7. Create startup script
Write-Host "[7/7] Creating startup script..." -ForegroundColor Yellow
$BatContent = @"
@echo off
chcp 65001 >nul
echo ========================================
echo   KeymouseGo Test Version v$Version
echo ========================================
echo.
echo [Requirements] Please install Python 3.10+ first
echo.
echo Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [Error] Python not found! Please install Python 3.10 or higher
    echo.
    pause
    exit /b 1
)

echo.
echo Installing dependencies (only needed on first run)...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo Starting...
echo.

cd /d "%~dp0"
python KeymouseGo.py

if errorlevel 1 (
    echo.
    echo Program exited with error, please take screenshot or copy error message!
    echo.
    pause
)
"@
$BatPath = Join-Path $PackageDir "run_test.bat"
[System.IO.File]::WriteAllLines($BatPath, ($BatContent -split "`r?`n"), [System.Text.Encoding]::GetEncoding("GBK"))
Write-Host "      Created: run_test.bat" -ForegroundColor Green

# 8. Create ZIP
Write-Host ""
Write-Host "Compressing test package..." -ForegroundColor Cyan
$ZipPath = Join-Path $ScriptDir "$PackageName.zip"
if (Test-Path $ZipPath) {
    Remove-Item -Path $ZipPath -Force
}
Compress-Archive -Path $PackageDir -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Test package created successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Package location: $ZipPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "Test Instructions:" -ForegroundColor Cyan
Write-Host "1. Install Python 3.10 or higher" -ForegroundColor White
Write-Host "2. Extract $PackageName.zip to any location (avoid Chinese in path)" -ForegroundColor White
Write-Host "3. Double-click 'run_test.bat' (will auto-install dependencies first time)" -ForegroundColor White
Write-Host "4. Follow instructions in '测试说明.md'" -ForegroundColor White
Write-Host ""

