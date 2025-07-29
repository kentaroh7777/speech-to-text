# 音声ファイルの文字起こし

カスタマイズされた音声ファイルの文字起こしCLIです。
**ローカル版のWhisper**または**OpenAI API**を使用できるので、用途に応じて選択可能です。

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
- feedparser
- click

## インストール

1. リポジトリをクローン
```bash
git clone <repository-url>
cd speech-to-text
```

2. 依存関係をインストール
```bash
pip install -r requirements.txt
```

3. 環境設定（RSSモード使用時）
```bash
cp .env.example .env
# .envファイルを編集してRSS URLなどを設定
```

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

### コマンドラインオプション

```bash
./scripts/stt [OPTIONS]
```

#### 利用可能なオプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--local-dir TEXT` | **ローカル音声ファイルディレクトリ（優先）** | なし |
| `--rss-url TEXT` | RSS feed URL（local-dir未指定時に使用） | 環境変数から取得 |
| `--download-dir TEXT` | 音声ファイル保存ディレクトリ | `./downloads` |
| `--output-dir TEXT` | 文字起こしファイル保存ディレクトリ | `./transcripts` |
| `--date-range [today\|yesterday\|last-week\|latest]` | 処理対象の日付範囲 | `today` |
| `--output-format [txt\|markdown\|json]` | 出力フォーマット | `txt` |
| `--whisper-model TEXT` | Whisperモデル | `base` |
| `--max-episodes INTEGER` | 最大処理エピソード数 | `10` |
| `--delete-audio` | 文字起こし成功後に音声ファイルを削除 | 無効 |
| `--use-openai-api` | **OpenAI API強制使用** | 無効 |
| `--openai-api-key TEXT` | **OpenAI APIキー** | 環境変数から取得 |
| `--no-openai-fallback` | **OpenAI APIフォールバック無効化** | 無効 |
| `--debug` | デバッグログを有効化 | 無効 |

**注意**: `--local-dir`が指定された場合、`--rss-url`は無視されます（ローカルファイル優先）。

### 使用例

#### ローカルファイルの例

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

#### RSSフィードの例

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

### ファイルソース
1. **`--local-dir`指定時**: ローカルファイルモード（RSS URLは無視）
2. **`--local-dir`未指定時**: RSSフィードモード（RSS URL必須）

### 文字起こしエンジン
1. **デフォルト**: ローカルWhisper → 失敗時OpenAI APIフォールバック
2. **`--use-openai-api`指定時**: OpenAI API強制使用
3. **`--no-openai-fallback`指定時**: ローカルWhisperのみ（フォールバック無効）

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

8. **OpenAI API関連のエラー**
   - APIキーが正しく設定されているか確認
   - OpenAI API利用制限に達していないか確認
   - インターネット接続を確認
   - `pip install openai`でライブラリがインストールされているか確認

