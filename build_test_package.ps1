# KeymouseGo 测试包制作脚本
# 使用方法：在PowerShell中运行 .\build_test_package.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Version = "1.0"
$PackageName = "KeymouseGo_Test_v$Version"
$PackageDir = Join-Path $ScriptDir $PackageName

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  KeymouseGo 测试包制作工具 v$Version" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 清理旧的打包目录
if (Test-Path $PackageDir) {
    Write-Host "[1/8] 清理旧的打包目录..." -ForegroundColor Yellow
    Remove-Item -Path $PackageDir -Recurse -Force
    Write-Host "      已删除: $PackageDir" -ForegroundColor Green
}

# 2. 创建打包目录
Write-Host "[2/8] 创建打包目录..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $PackageDir | Out-Null
Write-Host "      已创建: $PackageDir" -ForegroundColor Green

# 3. 复制主程序文件
Write-Host "[3/8] 复制主程序文件..." -ForegroundColor Yellow
$MainFiles = @(
    "KeymouseGo.py",
    "UIFunc.py",
    "UIView.py",
    "UIFileDialogFunc.py",
    "UIFileDialogView.py",
    "assets_rc.py",
    "Mondrian.ico",
    "测试说明.md",
    "问题报告模板.md"
)
foreach ($File in $MainFiles) {
    $SrcPath = Join-Path $ScriptDir $File
    if (Test-Path $SrcPath) {
        Copy-Item -Path $SrcPath -Destination $PackageDir
        Write-Host "      已复制: $File" -ForegroundColor Green
    } else {
        Write-Host "      警告: 未找到 $File" -ForegroundColor Red
    }
}

# 4. 复制核心模块
Write-Host "[4/8] 复制核心模块..." -ForegroundColor Yellow
$Modules = @("Util", "Event", "Recorder", "Plugin")
foreach ($Module in $Modules) {
    $SrcPath = Join-Path $ScriptDir $Module
    if (Test-Path $SrcPath) {
        Copy-Item -Path $SrcPath -Destination $PackageDir -Recurse
        Write-Host "      已复制: $Module/" -ForegroundColor Green
    } else {
        Write-Host "      警告: 未找到 $Module/" -ForegroundColor Red
    }
}

# 5. 复制图片资源
Write-Host "[5/8] 复制图片资源..." -ForegroundColor Yellow
$ImageFolders = @("imgsA", "imgsB", "imgsC", "imgsE", "imgsF", "imgsG")
foreach ($Folder in $ImageFolders) {
    $SrcPath = Join-Path $ScriptDir $Folder
    if (Test-Path $SrcPath) {
        Copy-Item -Path $SrcPath -Destination $PackageDir -Recurse
        Write-Host "      已复制: $Folder/" -ForegroundColor Green
    } else {
        Write-Host "      警告: 未找到 $Folder/" -ForegroundColor Red
    }
}

# 6. 复制脚本和配置
Write-Host "[6/8] 复制脚本和配置..." -ForegroundColor Yellow
$ScriptFolders = @("scripts_enhanced", "configs")
foreach ($Folder in $ScriptFolders) {
    $SrcPath = Join-Path $ScriptDir $Folder
    if (Test-Path $SrcPath) {
        Copy-Item -Path $SrcPath -Destination $PackageDir -Recurse
        Write-Host "      已复制: $Folder/" -ForegroundColor Green
    } else {
        Write-Host "      警告: 未找到 $Folder/" -ForegroundColor Red
    }
}

# 7. 复制虚拟环境
Write-Host "[7/8] 复制虚拟环境 (这可能需要几分钟)..." -ForegroundColor Yellow
$VenvPath = Join-Path $ScriptDir "venv311"
if (Test-Path $VenvPath) {
    Copy-Item -Path $VenvPath -Destination $PackageDir -Recurse
    Write-Host "      已复制: venv311/" -ForegroundColor Green
} else {
    Write-Host "      警告: 未找到 venv311/" -ForegroundColor Red
    Write-Host "      请确保 venv311 虚拟环境存在！" -ForegroundColor Red
}

# 8. 创建启动脚本
Write-Host "[8/8] 创建启动脚本..." -ForegroundColor Yellow
$BatContent = @"
@echo off
chcp 65001 >nul
echo ========================================
echo   KeymouseGo 测试版 v$Version
echo ========================================
echo.
echo 正在启动...
echo.

cd /d "%~dp0"
venv311\Scripts\python.exe KeymouseGo.py

if errorlevel 1 (
    echo.
    echo 程序异常退出，请截图或复制错误信息反馈！
    echo.
    pause
)
"@
$BatPath = Join-Path $PackageDir "启动测试版.bat"
$BatContent | Out-File -FilePath $BatPath -Encoding Default
Write-Host "      已创建: 启动测试版.bat" -ForegroundColor Green

# 9. 压缩成ZIP
Write-Host ""
Write-Host "正在压缩测试包..." -ForegroundColor Cyan
$ZipPath = Join-Path $ScriptDir "$PackageName.zip"
if (Test-Path $ZipPath) {
    Remove-Item -Path $ZipPath -Force
}
Compress-Archive -Path $PackageDir -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  测试包制作完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "测试包位置: $ZipPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "分发说明：" -ForegroundColor Cyan
Write-Host "1. 将 $PackageName.zip 发给测试者" -ForegroundColor White
Write-Host "2. 测试者解压到任意位置（路径不要有中文）" -ForegroundColor White
Write-Host "3. 双击「启动测试版.bat」开始测试" -ForegroundColor White
Write-Host ""

