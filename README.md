# GIMP python-fu: Sekayu Retouch チュートリアル

GIMP 3.x pyton-fu用プラグインのリポジトリ。
・sakura - 桜の写真をエモく見せるプラグイン

## 1. これは何か

`sakura.py` は、選択したレイヤーに対して以下のような処理を行う GIMP プラグインです。

- 背景色の明るさと色味を調整
- 色温度を変更して春らしい雰囲気に寄せる
- ぼかしとグローで柔らかい仕上がりにする
- 必要に応じて細部を強調する

GIMP の「フィルター」メニューから実行できます。

## 2. 必要な環境

- GIMP 3.x
- Python 3
- PyGObject / GI 互換環境

## 3. インストール方法

1. このフォルダ全体を GIMP から読み込める場所に配置します。
   - GIMP > 設定 > フォルダー > プラグイン で確認可能
   - 例: Mac GIMP のプラグイン用ディレクトリ
     /Applications/GIMP.app/Contents/Resources/lib/gimp/3.0/plug-ins
   - もしくは、任意のディレクトリをプラグイン用フォルダーに追加。
2. `sakura/sakura.py` に実行権限追加
```bash
chmod +x sakura/sakura.py
```
3. GIMP を再起動します。
4. 画像を開いた状態で、メニューから次を選びます。
```text
Filters > Sekayu > Sekayu Retouch
```

## 4. 使い方チュートリアル

### Step 1: 画像を開く

- GIMP で対象画像を開きます。
- まずは単一レイヤーの画像を使うとわかりやすいです。

### Step 2: 対象レイヤーを選択する

- 編集したいレイヤーを選択します。
- プラグインは「1つのレイヤー」を対象に動作します。

### Step 3: プラグインを実行する

- メニューから以下を選択します。

```text
Filters > Sekayu > Sekayu Retouch
```

### Step 4: 設定を調整する

ダイアログで次のような項目を調整できます。

- 色温度
- ガンマ補正
- 白のクリップ
- 黒の持ち上げ
- 詳細強調(Enhance)の有効化 ※処理が重いのでdefault offです...

### Step 5: 確定する

- 画面の「OK」を押すと処理が適用されます。
- もし気に入らなければ、GIMP の元に戻す操作を使って調整できます。

## 5. プロジェクト構成

```text
.
├── README.md
├── sakura/
│   └── sakura.py
├── sekayu_common/
│   ├── dialog.py
│   ├── filter.py
│   └── __init__.py
```

- `sakura/`: 実際のプラグイン本体
- `sekayu_common/`: UI とフィルタ処理を共通化したモジュール

## 6. 実装のポイント

このプラグインでは、次のような構成で処理を分けています。

- `create_effect_layer()`: 派生レイヤーを作成
- `add_background_adjustments()`: 背景の色味を調整
- `create_derived_effect_layers()`: ぼかしと光のエフェクトを追加
- `run()`: GIMP の procedure として実行

GEGL フィルタと GIMP API を組み合わせることで、レイヤーを重ねたような見た目の調整を行っています。

## 7. トラブルシューティング

### プラグインが表示されない

- GIMP を再起動してみてください。
- Python の依存関係が入っているか確認してください。
- プラグインの配置先が正しいか確認してください。

### エラーが出る

- ターミナルや GIMP のコンソールに表示されたエラーメッセージを確認してください。
- `gi` や `GIMP` / `GTK` の導入状態を確認
