# Windows環境セットアップガイド

Windows環境でSpeech-to-Text Transcriberを使用するための詳細手順です。

## 前提条件

### 1. Pythonのインストール

#### オプション1: Microsoft Store（推奨）
1. Microsoft Storeを開く
2. "Python"で検索して最新バージョンをインストール
3. 自動的にPATHに追加される

#### オプション2: 公式サイト
1. [Python公式サイト](https://www.python.org/downloads/windows/)にアクセス
2. 最新版をダウンロード
3. インストール時に「Add Python to PATH」にチェック

### 2. インストール確認

コマンドプロンプトまたはPowerShellで以下を実行：

```cmd
python --version
pip --version
```

## セットアップ手順

### 1. プロジェクトのダウンロード

```cmd
git clone https://github.com/yourusername/speech-to-text.git
cd speech-to-text
```

### 2. 依存関係のインストール

```cmd
pip install -r requirements.txt
```

### 3. 設定ファイルの作成

#### コマンドプロンプト
```cmd
copy .env.example .env
notepad .env
```

#### PowerShell
```powershell
Copy-Item .env.example .env
notepad .env
```

### 4. 設定の編集

`.env`ファイルを編集してOpenAI APIキー等を設定：

```
OPENAI_API_KEY=sk-your-actual-api-key-here
STT_RSS_URL=https://your-rss-feed.com/rss
```

## 実行方法

### コマンドプロンプトを使用

```cmd
REM ヘルプ表示
scripts\stt.bat --help

REM ローカルファイルの文字起こし
scripts\stt.bat --local-dir C:\Users\%USERNAME%\Downloads\audio --date-range latest

REM RSSフィードからの処理
scripts\stt.bat --rss-url "https://example.com/feed.rss" --date-range yesterday
```

### PowerShellを使用

初回実行時に実行ポリシーの設定が必要：

```powershell
# 実行ポリシーを確認
Get-ExecutionPolicy

# 実行ポリシーを設定（必要に応じて）
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

実行例：

```powershell
# ヘルプ表示
scripts\stt.ps1 --help

# ローカルファイルの文字起こし
scripts\stt.ps1 --local-dir "$env:USERPROFILE\Downloads\audio" --date-range latest

# RSSフィードからの処理
scripts\stt.ps1 --rss-url "https://example.com/feed.rss" --date-range yesterday
```

## パッケージインストール（推奨）

開発モードでインストールすると、どこからでも`stt`コマンドが使用可能：

```cmd
pip install -e .
```

インストール後：

```cmd
stt --help
stt --local-dir .\audio --date-range latest
```

## トラブルシューティング

### Python not found
- PythonがPATHに追加されているか確認
- コマンドプロンプトを再起動

### PowerShell実行エラー
- 実行ポリシーを設定：`Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 日本語ファイル名の問題
- ファイル名は英数字を推奨
- 文字化けする場合はファイル名を変更

### パスの指定
- Windowsでは`\`（バックスラッシュ）を使用
- パスにスペースが含まれる場合は`"`で囲む

## 環境変数の設定

### 一時的な設定

**コマンドプロンプト：**
```cmd
set OPENAI_API_KEY=sk-your-key
```

**PowerShell：**
```powershell
$env:OPENAI_API_KEY = "sk-your-key"
```

### 永続的な設定

```cmd
setx OPENAI_API_KEY "sk-your-key"
```

注意：setx実行後は新しいコマンドプロンプトを開く必要があります。

## よくある質問

### Q: ffmpegが必要ですか？
A: 音声形式によっては必要です。[公式サイト](https://ffmpeg.org/download.html)からダウンロードしてPATHに追加してください。

### Q: Whisperモデルはどこに保存される？
A: `C:\Users\[ユーザー名]\.cache\whisper\`に保存されます。

### Q: 大きな音声ファイルの処理が遅い
A: より小さなWhisperモデル（`tiny`や`base`）を試すか、OpenAI APIを使用してください。 