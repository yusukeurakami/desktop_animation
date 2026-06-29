# Liberty Desktop Pet

Macの画面上で動く、リバティアイランド風のピクセル馬ペットです。
枠なし・透明背景のMacネイティブ表示で動きます。

## 起動

`start.command` をダブルクリックします。

初回だけ小さな実行ファイルを自動で作ります。

## 操作

- ドラッグ: 場所を移動
- クリック: 頭を撫でる
- ダブルクリック: すぐ肉を食べる
- 右クリック: 終了
- `q` または `Esc`: 終了

## 素材

- 元画像: `assets/source/Liberty-pixel.png`
- 透過済みフレーム: `assets/frames/`
- フレーム再生成: `tools/build_frames.py`
- Mac表示本体: `src/LibertyPet.swift`

フレームを作り直す場合は、Codex内では以下で再生成できます。

```bash
/Users/0000404949/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 tools/build_frames.py
```
