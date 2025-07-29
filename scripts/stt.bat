@echo off
REM Speech-to-Text Transcriber Launcher for Windows
REM このスクリプトはどのディレクトリからでも実行できます

REM 実行時の作業ディレクトリを保存
set ORIGINAL_CWD=%CD%

REM スクリプトのあるディレクトリの絶対パスを取得
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Python環境の設定
set PYTHON_CMD=python

REM メインスクリプトのパス
set MAIN_SCRIPT=%PROJECT_ROOT%\src\main.py

REM 実行前の環境チェック
if not exist "%MAIN_SCRIPT%" (
    echo エラー: メインスクリプトが見つかりません: %MAIN_SCRIPT%
    exit /b 1
)

REM Python環境のチェック
python --version >nul 2>&1
if errorlevel 1 (
    echo エラー: Pythonが見つかりません。Pythonをインストールしてください。
    exit /b 1
)

REM 実行時作業ディレクトリを環境変数に設定
set STT_ORIGINAL_CWD=%ORIGINAL_CWD%

REM プロジェクトディレクトリに移動してスクリプト実行
cd /d "%PROJECT_ROOT%"
python "%MAIN_SCRIPT%" %* 