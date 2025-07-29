# Speech-to-Text Transcriber

RSSフィード、ローカル音声ファイル、**X Spaces**から音声を取得し、OpenAIのWhisperモデル（ローカル実行）またはOpenAI APIを使用して自動で文字起こしを行うツールです。

## 🎯 主な機能

- **複数の音声ソース対応**
  - 📡 **RSSフィード**: ポッドキャスト等のRSSから自動取得
  - 📁 **ローカルファイル**: 指定ディレクトリの音声ファイルを処理
  - 🎙️ **X Spaces**: スペースURL・ツイートURLから音声を自動取得・処理
- **自動無音削除**: X Spacesの冒頭無音部分を自動検出・削除
- **日付フィルタリング**: today, yesterday, last-week, latest で期間指定
- **2つの文字起こしエンジン**
  - 🏠 **ローカルWhisper**: オフライン処理、プライバシー重視
  - ☁️ **OpenAI API**: 高精度、大容量ファイル対応（自動分割）
- **フォールバック機能**: ローカル失敗時にAPI自動切替
- **クロスプラットフォーム**: Windows, macOS, Linux対応

## 概要

**2つの動作モード**と**2つの文字起こしエンジン**をサポートしています：

### 動作モード
1. **RSSフィードモード**: RSSフィードから音声ファイルを自動ダウンロードして文字起こし
2. **ローカルファイルモード**: 既存のローカル音声ファイルを直接文字起こし

### 文字起こしエンジン
1. **ローカルWhisper（推奨・デフォルト）**: 
   - 完全無料、プライバシー保護
   - 初回のみモデルダウンロードが必要
   - ファイルサイズ制限なし

2. **OpenAI API**: 
   - 高速処理、セットアップ不要
   - **使用料金が発生**（1分あたり約$0.006）
   - ファイルサイズ制限：25MB/ファイル
   - ローカルWhisper失敗時の自動フォールバック対応

設定は環境変数で管理されます。

## 技術スタック
- Python
- OpenAI Whisper
- feedparser (RSS解析)
- click (CLI)
- yt-dlp (X Spaces音声取得)
- pydub (音声処理)
- requests (HTTP通信)

## インストール・セットアップ

### 方法1: 直接実行（推奨）

#### 1. リポジトリをクローン

```bash
git clone https://github.com/yourusername/speech-to-text.git
cd speech-to-text
```

#### 2. 依存関係をインストール

```bash
pip install -r requirements.txt
```

#### 3. 設定ファイルをコピー

```bash
# Unix/Linux/macOS
cp .env.example .env

# Windows (コマンドプロンプト)
copy .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

#### 4. 設定を編集

`.env`ファイルを編集して必要な設定を行います：

```bash
# RSS feed URL（RSSモード使用時）
STT_RSS_URL=https://your-rss-feed.com/rss

# OpenAI API（オプション）
OPENAI_API_KEY=sk-your-api-key-here
```

### 方法2: Pythonパッケージとしてインストール

```bash
# 開発モードでインストール（推奨）
pip install -e .

# 通常インストール
pip install .
```

インストール後は、どこからでも`stt`コマンドが使用可能になります。

## 実行方法

🎯 **推奨**: `scripts/`ディレクトリに統一されたクロスプラットフォーム対応スクリプトがあります。

### Unix/Linux/macOS環境

```bash
# scripts/stt を実行（推奨）
./scripts/stt --help

# Python直接実行
python3 scripts/stt --help

# パッケージインストール後
stt --help
```

### Windows環境

#### コマンドプロンプト
```cmd
REM バッチファイル使用
scripts\stt.bat --help

REM 直接Python実行
python scripts\stt --help

REM パッケージインストール後
stt --help
```

#### PowerShell
```powershell
# PowerShellスクリプト使用
scripts\stt.ps1 --help

# 直接Python実行
python scripts\stt --help

# パッケージインストール後
stt --help
```

⚠️ **PowerShell実行ポリシー注意**: PowerShellスクリプトを初回実行時にエラーが出る場合：

```powershell
# 実行ポリシーを確認
Get-ExecutionPolicy

# 必要に応じて実行ポリシーを変更（管理者権限が必要）
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

📖 **Windows環境の詳細**: [WINDOWS_SETUP.md](WINDOWS_SETUP.md)をご覧ください。

## 設定

`.env`ファイルで以下の設定が可能です：

### 基本設定
```bash
# RSS feed URL（RSSモード使用時のみ必須）
STT_RSS_URL=https://example.com/rss

# ディレクトリパス
STT_DOWNLOAD_DIR=./downloads
STT_OUTPUT_DIR=./transcripts

# 処理オプション
STT_DATE_RANGE=today  # today, yesterday, last-week, latest
STT_OUTPUT_FORMAT=txt  # txt, markdown, json
STT_WHISPER_MODEL=base  # tiny, base, small, medium, large
STT_MAX_EPISODES=10

# 音声処理設定
STT_CHUNK_SIZE_MB=50
STT_OVERLAP_SECONDS=15
```

### OpenAI API設定（オプション）
```bash
# OpenAI API キー（必須：APIを使用する場合）
OPENAI_API_KEY=sk-your-api-key-here

# OpenAI API強制使用（デフォルト: false）
STT_USE_OPENAI_API=false

# ローカルWhisper失敗時のOpenAI APIフォールバック（デフォルト: true）
STT_OPENAI_FALLBACK=true
```

⚠️ **OpenAI API使用時の注意事項**:
- **料金が発生します**（1分あたり約$0.006）
- ファイルは一時的にOpenAIのサーバーに送信されます
- 25MB/ファイルの制限があります

## 使い方

### 1. ローカルファイルモード（推奨）

ローカルディレクトリにある音声ファイルを直接文字起こしします。

```bash
# 指定ディレクトリの最新ファイルを文字起こし
./scripts/stt --local-dir /path/to/audio/files --date-range latest

# 今日のファイルをすべて文字起こし
./scripts/stt --local-dir /path/to/audio/files --date-range today

# 先週のファイルを最大3個まで処理
./scripts/stt --local-dir /path/to/audio/files --date-range last-week --max-episodes 3
```

#### 対応ファイル形式
- `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.aac`, `.wma`

#### 日付の自動認識
ファイル名から以下のパターンで日付を自動抽出します：
- `YYYYMMDD` (例: `20250728_タイトル.mp3`)
- `YYYY-MM-DD` (例: `2025-07-28_タイトル.mp3`)
- `YYYY_MM_DD` (例: `2025_07_28_タイトル.mp3`)

**ファイル名に日付がない場合の処理**:
- ファイルの更新日時（mtime）を自動的に使用
- 日付ありファイルと日付なしファイルが混在していても適切に処理
- 統計情報でどのファイルがどちらの方式を使っているかログに表示

#### `latest`オプションの詳細動作
- **基本動作**: 最新の日付のファイルを1つ選択
- **同じ日付の複数ファイル**: ファイルの更新日時（mtime）で最新のものを優先
- **混在ファイル対応**: 日付ありファイルと日付なしファイルが混在していても正しく処理
- **例**: `20250729_file1.mp3`、`recording.mp3`が両方とも同じ日付の場合、より新しく更新されたファイルを選択

### 2. RSSフィードモード

RSS フィードから音声ファイルを自動ダウンロードして処理します。

```bash
# 環境変数の設定を使用
./scripts/stt --rss-url "https://example.com/feed.rss"

# 今日の配信を文字起こし
./scripts/stt --rss-url "https://example.com/feed.rss" --date-range today

# 最新1件のみ処理
./scripts/stt --rss-url "https://example.com/feed.rss" --date-range latest --max-episodes 1
```

### 3. X Spacesモード

X Spaces（旧Twitter Spaces）の音声を直接取得して文字起こしします。

```bash
# スペース直接URLから文字起こし
./scripts/stt --X-space "https://x.com/i/spaces/1yNGaLgdDRqKj"

# ツイートURLからスペースを自動検出
./scripts/stt --X-space "https://x.com/username/status/1234567890"

# ダウンロード先を指定
./scripts/stt --X-space "https://x.com/i/spaces/1yNGaLgdDRqKj" --download-dir x-spaces-audio

# JSON形式で詳細なメタデータを含む出力
./scripts/stt --X-space "https://x.com/i/spaces/1yNGaLgdDRqKj" --output-format json
```

#### X Spaces特有機能
- **自動無音削除**: 冒頭の無音部分を自動検出・削除（-50dB閾値、0.1秒以上）
- **URL形式**: スペース直接URL・ツイートURL両方対応
- **音声形式**: MP3形式で高品質ダウンロード

## 📊 出力形式

### TXT形式（デフォルト）
```txt
文字起こし結果がプレーンテキストで保存されます
```

### JSON形式
```bash
./scripts/stt --output-format json
```

JSON出力には以下のメタデータが含まれます：
```json
{
  "transcript": "文字起こしテキスト",
  "filename": "処理ファイル名",
  "date": "2025-07-29 11:00:00",
  "source": "audio.mp3|https://example.com/feed.rss",
  "duration": 440.5,
  "size_mb": 2.83,
  "model": "tiny",
  "engine": "local_whisper|openai_api",
  "processed_at": "2025-07-29 11:00:00",
  "processing_time": "153.8s",
  "author": "作成者名",
  "contact": "contact@example.com"
}
```

**dateフィールド詳細:**
- **RSS**: 配信日時（時刻含む）
- **X Spaces**: ダウンロード日時（TODO: 実際の配信時刻）
- **ローカルファイル**: ファイル名から抽出（YYYYMMDD_HHMM等）、なければファイル更新日時

JSON形式は以下の用途に最適です：
- **データ分析**: 処理時間・ファイルサイズの分析
- **品質管理**: 使用モデル・エンジンの追跡
- **自動化**: 他のシステムとの連携
- **セキュリティ**: ローカルファイルはファイル名のみ表示

### コマンドラインオプション

```bash
./scripts/stt [OPTIONS]
```

#### 利用可能なオプション

| オプション | 説明 | デフォルト値 |
|-----------|------|-------------|
| `--rss-url` | RSS feed URL | - |
| `--local-dir` | ローカル音声ファイルのディレクトリ | - |
| `--X-space` | X Spaces URL（スペースURL または ツイートURL） | - |
| `--download-dir` | 音声ファイルのダウンロード先 | `downloads` |
| `--output-dir` | 文字起こし結果の保存先 | `transcripts` |
| `--output-format` | 出力形式 (`txt`, `json`) | `txt` |
| `--date-range` | 処理する日付範囲 (`today`, `yesterday`, `last-week`, `latest`) | `today` |
| `--whisper-model` | Whisperモデル (`tiny`, `base`, `small`, `medium`, `large`) | `base` |
| `--delete-audio` | 処理後にダウンロードした音声ファイルを削除 | `False` |
| `--delete-original` | 処理後に元の音声ファイルを削除（X Spaces用） | `False` |
| `--use-openai-api` | OpenAI APIを優先使用 | `False` |
| `--openai-api-key` | OpenAI APIキー（環境変数でも設定可能） | - |
| `--no-openai-fallback` | ローカルWhisper失敗時のAPI切替を無効化 | `False` |
| `--author` | 作成者名（JSONメタデータ用） | `STT_AUTHOR` |
| `--contact` | 連絡先情報（JSONメタデータ用） | `STT_CONTACT` |

**注意**: `--local-dir`が指定された場合、`--rss-url`は無視されます（ローカルファイル優先）。

### 使用例

#### ローカルファイルの例

**Unix/Linux/macOS:**
```bash
# 音声ファイルディレクトリの最新ファイルを高精度で文字起こし
./scripts/stt --local-dir ~/Downloads/audio --date-range latest --whisper-model medium

# 今日録音した音声を全てMarkdown形式で出力
./scripts/stt --local-dir ~/Documents/recordings --date-range today --output-format markdown

# 先週の音声ファイルを最大5件処理（デバッグモード）
./scripts/stt --local-dir /Users/user/audio --date-range last-week --max-episodes 5 --debug

# OpenAI APIを強制使用（高速処理）⚠️料金注意
./scripts/stt --local-dir ~/audio --use-openai-api --openai-api-key sk-your-key

# OpenAI APIキーを環境変数で設定して使用
export OPENAI_API_KEY=sk-your-api-key-here
./scripts/stt --local-dir ~/audio --use-openai-api
```

**Windows (コマンドプロンプト):**
```cmd
REM 音声ファイルディレクトリの最新ファイルを高精度で文字起こし
scripts\stt.bat --local-dir C:\Users\%USERNAME%\Downloads\audio --date-range latest --whisper-model medium

REM 今日録音した音声を全てMarkdown形式で出力
scripts\stt.bat --local-dir C:\Users\%USERNAME%\Documents\recordings --date-range today --output-format markdown

REM OpenAI APIを強制使用（高速処理）⚠️料金注意
scripts\stt.bat --local-dir C:\Users\%USERNAME%\audio --use-openai-api --openai-api-key sk-your-key

REM OpenAI APIキーを環境変数で設定して使用
set OPENAI_API_KEY=sk-your-api-key-here
scripts\stt.bat --local-dir C:\Users\%USERNAME%\audio --use-openai-api
```

**Windows (PowerShell):**
```powershell
# 音声ファイルディレクトリの最新ファイルを高精度で文字起こし
scripts\stt.ps1 --local-dir "$env:USERPROFILE\Downloads\audio" --date-range latest --whisper-model medium

# 今日録音した音声を全てMarkdown形式で出力
scripts\stt.ps1 --local-dir "$env:USERPROFILE\Documents\recordings" --date-range today --output-format markdown

# OpenAI APIを強制使用（高速処理）⚠️料金注意
scripts\stt.ps1 --local-dir "$env:USERPROFILE\audio" --use-openai-api --openai-api-key sk-your-key

# OpenAI APIキーを環境変数で設定して使用
$env:OPENAI_API_KEY = "sk-your-api-key-here"
scripts\stt.ps1 --local-dir "$env:USERPROFILE\audio" --use-openai-api
```

**パッケージインストール後（全OS共通）:**
```bash
# どこからでも実行可能
stt --local-dir ~/audio --date-range latest --whisper-model medium
stt --local-dir ./recordings --date-range today --output-format markdown
```

#### RSSフィードの例

**Unix/Linux/macOS:**
```bash
# 昨日の配信を全て処理
./scripts/stt --rss-url "https://example.com/feed.rss" --date-range yesterday

# 最新3件をMarkdown形式で出力
./scripts/stt --rss-url "https://example.com/feed.rss" --date-range latest --max-episodes 3 --output-format markdown

# より高精度なモデルを使用
./scripts/stt --rss-url "https://example.com/feed.rss" --whisper-model medium

# 文字起こし後に音声ファイルを自動削除（ストレージ節約）
./scripts/stt --rss-url "https://example.com/feed.rss" --delete-audio

# ローカルWhisper失敗時にOpenAI APIフォールバック無効化
./scripts/stt --rss-url "https://example.com/feed.rss" --no-openai-fallback
```

**Windows (コマンドプロンプト):**
```cmd
REM 昨日の配信を全て処理
scripts\stt.bat --rss-url "https://example.com/feed.rss" --date-range yesterday

REM 最新3件をMarkdown形式で出力
scripts\stt.bat --rss-url "https://example.com/feed.rss" --date-range latest --max-episodes 3 --output-format markdown

REM より高精度なモデルを使用
scripts\stt.bat --rss-url "https://example.com/feed.rss" --whisper-model medium
```

**Windows (PowerShell):**
```powershell
# 昨日の配信を全て処理
scripts\stt.ps1 --rss-url "https://example.com/feed.rss" --date-range yesterday

# 最新3件をMarkdown形式で出力
scripts\stt.ps1 --rss-url "https://example.com/feed.rss" --date-range latest --max-episodes 3 --output-format markdown

# より高精度なモデルを使用
scripts\stt.ps1 --rss-url "https://example.com/feed.rss" --whisper-model medium
```

### X Spaces実用例

**Unix/Linux/macOS:**
```bash
# 基本的なX Spaces処理
./scripts/stt --X-space "https://x.com/i/spaces/1yNGaLgdDRqKj"

# 高精度モデルでX Spaces処理
./scripts/stt --X-space "https://x.com/username/status/1234567890" --whisper-model large

# OpenAI APIでX Spaces処理（高精度・高速）
./scripts/stt --X-space "https://x.com/i/spaces/1yNGaLgdDRqKj" --use-openai-api

# 処理後にダウンロードファイルを削除
./scripts/stt --X-space "https://x.com/i/spaces/1yNGaLgdDRqKj" --delete-original
```

**Windows (コマンドプロンプト):**
```cmd
REM 基本的なX Spaces処理
scripts\stt.bat --X-space "https://x.com/i/spaces/1yNGaLgdDRqKj"

REM 高精度モデルでX Spaces処理
scripts\stt.bat --X-space "https://x.com/username/status/1234567890" --whisper-model large
```

**Windows (PowerShell):**
```powershell
# 基本的なX Spaces処理
scripts\stt.ps1 --X-space "https://x.com/i/spaces/1yNGaLgdDRqKj"

# OpenAI APIでX Spaces処理
scripts\stt.ps1 --X-space "https://x.com/username/status/1234567890" --use-openai-api
```

## 出力ファイル

文字起こしファイルは以下の形式で保存されます：

### ローカルファイルモード
```
transcripts/
├── 20250728_ファイル名.txt
├── 20250727_別のファイル名.md
└── 20250726_さらに別のファイル名.json
```

### RSSフィードモード
```
transcripts/
├── 20250728_エピソードタイトル.txt
├── 20250727_エピソードタイトル.md
└── 20250726_エピソードタイトル.json
```

## 動作モードの選択

### 📊 ファイル取得元
1. **RSSフィード** (`--rss-url`): ポッドキャスト等のRSSから音声を自動取得
2. **ローカルファイル** (`--local-dir`): 指定ディレクトリの音声ファイルを処理
3. **X Spaces** (`--X-space`): スペースまたはツイートURLから音声を取得

### 🤖 文字起こしエンジン
1. **ローカルWhisper** (デフォルト): ローカル環境でオフライン処理
2. **OpenAI API** (`--use-openai-api`): クラウドで高精度処理

### 推奨設定
- **コスト重視**: ローカルWhisperのみ（`--no-openai-fallback`）
- **速度重視**: OpenAI API（`--use-openai-api`）⚠️料金注意
- **バランス重視**: デフォルト設定（ローカル + フォールバック）

## 注意事項

- 大きな音声ファイルは自動的にチャンクに分割されて処理されます
- 既に文字起こしファイルが存在する場合はスキップされます
- `--delete-audio`オプションはRSSモードでのみ有効です（ローカルファイルは削除されません）
- SSL証明書エラーが発生する場合がありますが、自動的に処理されます
- ローカルファイルモードでは、サブディレクトリも再帰的に検索されます

### OpenAI API使用時の注意事項
- **料金が発生します**: 音声1分あたり約$0.006
- **プライバシー**: 音声ファイルがOpenAIのサーバーに送信されます
- **ファイルサイズ制限**: 25MB/ファイル（超過時は自動的にチャンク分割）
- **APIキー管理**: 環境変数での設定を推奨（セキュリティ）

## トラブルシューティング

### よくある問題

1. **ローカルファイルが見つからない**
   - ディレクトリパスが正しいか確認
   - 対応ファイル形式（mp3、wav、m4a等）か確認
   - ファイルのアクセス権限を確認

2. **RSS フィードが読み込めない**
   - RSS URLが正しいか確認
   - インターネット接続を確認

3. **音声ファイルのダウンロードに失敗**
   - ディスク容量を確認
   - ネットワーク接続を確認

4. **ローカルWhisperが動作しない**
   - Pythonの依存関係を確認: `pip install -r requirements.txt`
   - モデルファイルのダウンロード容量を確認
   - **自動フォールバック**: OpenAI APIキーが設定されていれば自動的に切り替わります

5. **文字起こしが遅い**
   - STT_WHISPER_MODELでより小さなWhisperモデル（`tiny`）を試す
   - チャンクサイズを小さくする
   - **高速化**: OpenAI APIを使用（`--use-openai-api`）⚠️料金注意

6. **文字起こしの精度が悪い**
   - STT_WHISPER_MODELでより大きなWhisperモデル（`medium`, `large`）を試す
   - OpenAI APIは一般的に高精度

7. **メモリエラー**
   - STT_WHISPER_MODELより小さなWhisperモデルを使用
   - 処理するエピソード数を減らす
   - OpenAI APIを使用（メモリ使用量が少ない）

8. **X Spacesのダウンロードに失敗**
   - `yt-dlp`が最新版か確認: `pip install --upgrade yt-dlp`
   - URLが正しいか確認（スペースURL または ツイートURL）
   - スペースが終了済みで録音が利用可能か確認
   - ネットワーク接続とX/Twitterへのアクセスを確認

9. **X Spacesの音声が無音すぎる**
   - 自動無音削除が正常に動作しています（-50dB閾値）
   - 音声レベルが極端に低い場合は手動で音量調整を検討
   - より感度の高い無音検出が必要な場合はffmpegオプションのカスタマイズを検討

10. **OpenAI API関連のエラー**
    - APIキーが正しく設定されているか確認
    - OpenAI API利用制限に達していないか確認
    - インターネット接続を確認
    - `pip install openai`でライブラリがインストールされているか確認

11. **Windows環境での問題**
    - **PowerShell実行ポリシーエラー**: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`を実行
    - **Python not found**: Microsoft StoreまたはPython公式サイトからPythonをインストール
    - **パスの区切り文字**: Windowsでは`\`、Unix系では`/`を使用
    - **日本語ファイル名**: 文字化けが発生する場合は英数字のファイル名を使用

12. **クロスプラットフォーム環境変数設定**
    ```bash
    # Unix/Linux/macOS (.bashrc, .zshrc等)
    export OPENAI_API_KEY=sk-your-key

    # Windows (コマンドプロンプト)
    set OPENAI_API_KEY=sk-your-key

    # Windows (PowerShell)
    $env:OPENAI_API_KEY = "sk-your-key"

    # 永続的に設定（Windows）
    setx OPENAI_API_KEY "sk-your-key"
    ```

## 開発・貢献

このプロジェクトはオープンソースです。バグ報告、機能提案、プルリクエストを歓迎します。

### セットアップ

```bash
git clone https://github.com/yourusername/speech-to-text.git
cd speech-to-text
pip install -r requirements.txt
cp .env.example .env
# .envファイルを編集して設定

# 実行テスト
./scripts/stt --help
```

## ライセンス

このプロジェクトは [MIT License](LICENSE) の下でライセンスされています。

## 作者

- **Hayashi** - [GitHub](https://github.com/yourusername)

## 謝辞

- [OpenAI Whisper](https://github.com/openai/whisper) - ローカル音声認識エンジン
- [OpenAI API](https://platform.openai.com/) - クラウド音声認識サービス

