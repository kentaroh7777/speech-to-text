# Speech-to-Text Transcriber Launcher for PowerShell
# このスクリプトはどのディレクトリからでも実行できます

param([Parameter(ValueFromRemainingArguments = $true)]$RemainingArgs)

# 実行時の作業ディレクトリを保存
$originalCwd = Get-Location

# スクリプトのあるディレクトリの絶対パスを取得
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path -Parent $scriptDir

# メインスクリプトのパス
$mainScript = Join-Path $projectRoot "src\main.py"

# 実行前の環境チェック
if (-not (Test-Path $mainScript)) {
    Write-Error "エラー: メインスクリプトが見つかりません: $mainScript"
    exit 1
}

# Python環境のチェック
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
} catch {
    Write-Error "エラー: Pythonが見つかりません。Pythonをインストールしてください。"
    exit 1
}

# 実行時作業ディレクトリを環境変数に設定
$env:STT_ORIGINAL_CWD = $originalCwd.Path

# プロジェクトディレクトリに移動してスクリプト実行
Set-Location $projectRoot

try {
    if ($RemainingArgs) {
        & python $mainScript @RemainingArgs
    } else {
        & python $mainScript
    }
} finally {
    # 元のディレクトリに戻る
    Set-Location $originalCwd
} 