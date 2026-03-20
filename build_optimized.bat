@echo off
REM ==========================================
REM KeymouseGo 优化版打包脚本
REM ==========================================
REM 使用说明：
REM 1. 确保已安装所有依赖：pip install -r requirements.txt
REM 2. 可选：下载UPX并解压到 upx/ 目录
REM 3. 运行此脚本进行打包
REM ==========================================

echo ==========================================
echo KeymouseGo 优化版打包工具
echo ==========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 检查PyInstaller是否安装
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [信息] PyInstaller未安装，正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller安装失败
        pause
        exit /b 1
    )
)

echo.
echo 请选择打包方式：
echo 1. 优化版（推荐）- 体积小，速度快
echo 2. 标准版 - 兼容性最好
echo 3. 调试版 - 显示控制台，便于调试
echo.
set /p choice="请输入选项 (1-3): "

if "%choice%"=="1" (
    set SPEC_FILE=KeymouseGo_optimized.spec
    echo.
    echo [信息] 使用优化版打包配置
) else if "%choice%"=="2" (
    set SPEC_FILE=KeymouseGo_release.spec
    echo.
    echo [信息] 使用标准版打包配置
) else if "%choice%"=="3" (
    set SPEC_FILE=KeymouseGo.spec
    echo.
    echo [信息] 使用调试版打包配置
) else (
    echo [错误] 无效选项
    pause
    exit /b 1
)

REM 检查spec文件是否存在
if not exist "%SPEC_FILE%" (
    echo [错误] 找不到配置文件: %SPEC_FILE%
    pause
    exit /b 1
)

echo.
echo ==========================================
echo 开始打包...
echo ==========================================
echo.

REM 执行打包
pyinstaller --clean "%SPEC_FILE%"

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo.
echo ==========================================
echo 打包成功！
echo ==========================================
echo.
echo 可执行文件位置: dist\KeymouseGo.exe
echo.

REM 显示文件大小
if exist "dist\KeymouseGo.exe" (
    for %%I in ("dist\KeymouseGo.exe") do set SIZE=%%~zI
    set /a SIZE_MB=%SIZE% / 1024 / 1024
    echo 文件大小: %SIZE_MB% MB
)

echo.
echo 是否打开输出目录？(Y/N)
set /p open_dir=
if /i "%open_dir%"=="Y" (
    explorer dist
)

echo.
echo 打包完成！
pause
