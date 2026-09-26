# 旅クイズ

旅行や飲み会の会話から Claude Code でクイズを作り、帰り道にスマホが読み上げて遊ぶための道具一式です。

- **アプリ**（司会用・スマホで開く）: https://macafat-alpha.github.io/trip-quiz/
- **クイズを作る skill**（Claude Code 用）: [`skill/trip-quiz/`](skill/trip-quiz/)

## skill の入れ方

```bash
git clone https://github.com/Macafat-alpha/trip-quiz.git
mkdir -p ~/.claude/skills
cp -R trip-quiz/skill/trip-quiz ~/.claude/skills/
```

Claude Code を開き直すと `/trip-quiz` が使えます。

Plaud で録音する場合は、Plaud CLI も入れてログインしておきます（テキストの文字起こしだけで作るなら不要です）。

```bash
npm i -g @plaud-ai/cli
plaud login
```

## 使い方

1. 当日の会話を録音する（Plaud、または任意の文字起こしアプリ）
2. Claude Code で `/trip-quiz` を実行し、参加者の名前と読みを伝える
3. できた `trip-quiz/quiz-YYYYMMDD.json` を司会のスマホに送る
4. アプリで読み込んで遊ぶ

- クイズの中身はサーバーに送りません。アプリは読み込んだ端末の中だけで動きます
- アプリは `index.html` 1ファイルで、読み上げはブラウザ標準の音声合成を使います
