# 音声ファイルの文字起こし

カスタマイズされた音声ファイルの文字起こしCLIです。
ローカル版のwhisperを使うので、AIの利用料がかかりません。無料でいくらでも文字起こしできます。

## 概要

ほぼ毎日standfmにアップロードされる音声ファイルを指定された期間（デフォルトでは当日分）ダウンロードし、それらの音声ファイルから文字起こしテキストファイルを作成したくて作成しました。

バイブコーディングの練習作のようなものです。

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

3. 環境設定
```bash
cp .env.example .env
# .envファイルを編集してRSS URLなどを設定
```

## 設定

`.env`ファイルで以下の設定が可能です：

```bash
# RSS feed URL (必須)
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

## 使い方

### 基本的な使用方法

```bash
# 環境変数の設定を使用
./scripts/stt

# 今日の配信を文字起こし
./scripts/stt --date-range today

# 最新1件のみ処理
./scripts/stt --date-range latest --max-episodes 1
```

### コマンドラインオプション

```bash
./scripts/stt [OPTIONS]
```

#### 利用可能なオプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--rss-url TEXT` | RSS feed URL | 環境変数から取得 |
| `--download-dir TEXT` | 音声ファイル保存ディレクトリ | `./downloads` |
| `--output-dir TEXT` | 文字起こしファイル保存ディレクトリ | `./transcripts` |
| `--date-range [today\|yesterday\|last-week\|latest]` | 処理対象の日付範囲 | `today` |
| `--output-format [txt\|markdown\|json]` | 出力フォーマット | `txt` |
| `--whisper-model TEXT` | Whisperモデル | `base` |
| `--max-episodes INTEGER` | 最大処理エピソード数 | `10` |
| `--delete-audio` | 文字起こし成功後に音声ファイルを削除 | 無効 |
| `--debug` | デバッグログを有効化 | 無効 |

### 使用例

```bash
# 昨日の配信を全て処理
./scripts/stt --date-range yesterday

# 最新3件をMarkdown形式で出力
./scripts/stt --date-range latest --max-episodes 3 --output-format markdown

# より高精度なモデルを使用
./scripts/stt --whisper-model medium

# 文字起こし後に音声ファイルを自動削除（ストレージ節約）
./scripts/stt --delete-audio

# デバッグモードで実行
./scripts/stt --debug

# 特定のRSSフィードを指定
./scripts/stt --rss-url "https://example.com/feed.rss" --date-range today
```

## 出力ファイル

文字起こしファイルは以下の形式で保存されます：

```
transcripts/
├── エピソードタイトル_20250627.txt
├── エピソードタイトル_20250627.md
└── エピソードタイトル_20250627.json
```

## 注意事項

- 大きな音声ファイルは自動的にチャンクに分割されて処理されます
- 既に文字起こしファイルが存在する場合はスキップされます
- `--delete-audio`オプション使用時は、文字起こしが成功した音声ファイルのみが削除されます
- SSL証明書エラーが発生する場合がありますが、自動的に処理されます

## トラブルシューティング

### よくある問題

1. **RSS フィードが読み込めない**
   - RSS URLが正しいか確認
   - インターネット接続を確認

2. **音声ファイルのダウンロードに失敗**
   - ディスク容量を確認
   - ネットワーク接続を確認

3. **文字起こしが遅い**
   - STT_WHISPER_MODELでより小さなWhisperモデル（`tiny`）を試す
   - チャンクサイズを小さくする

4. **文字起こしの精度が悪い**
   - STT_WHISPER_MODELでより大きなWhisperモデル（`small`）を試す

5. **メモリエラー**
   - STT_WHISPER_MODELより小さなWhisperモデルを使用
   - 処理するエピソード数を減らす

