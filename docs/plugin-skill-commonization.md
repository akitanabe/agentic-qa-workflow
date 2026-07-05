# Plugin Skill Commonization

## 概要

このドキュメントは、Claude Code 用 skill と Codex 用 skill の共通化方針をまとめます。

対象は主に次の2ファイルです。

* `plugins/claude/skills/delegate-implementation/SKILL.md`
* `plugins/codex/skills/delegate-implementation/SKILL.md`

両者は同じ workflow を表しますが、実行環境、tool 名、配布形式、custom agent の扱いが異なります。
そのため、`SKILL.md` を1つに物理共有するのではなく、共通原稿から各 plugin 用の配布物を生成する方針を取ります。

## 結論

`plugins/claude/` と `plugins/codex/` は、それぞれ独立した plugin root として維持します。

`.codex-plugin` を `plugins/` 直下へ移動して Codex plugin root を広げる案は採用しません。
plugin root を広げると、Codex plugin の配布単位に Claude Code 用 plugin まで含まれ、責務境界が曖昧になります。

共通化は directory 構造ではなく、生成元の分離で行います。

```text
shared/
  delegate-implementation-core.md
plugins/
  claude/
    skills/delegate-implementation/SKILL.md
  codex/
    skills/delegate-implementation/SKILL.md
scripts/
  build_delegate_skills.py
```

## 共通化する範囲

次の内容は platform に依存しないため、共通原稿に寄せます。

* 親エージェントが品質責任を持つこと
* baseline を commit で前進させること
* 枝の種別ごとの TDD 強度
* worker の完了報告だけで受け入れないこと
* diff と test を親が読むこと
* 責務境界レビューゲート
* hard reject 条件
* 最終報告に含める項目

## 分離する範囲

Claude Code 固有の記述は Claude 用 template に置きます。

* `Agent` tool
* `SendMessage`
* `subagent_type`
* `isolation: "worktree"`
* `CLAUDE.md` や Claude Code 固有の検証文脈

Codex 固有の記述は Codex 用 template に置きます。

* Codex custom agent の確認
* `plugins/codex/install/agents/*.toml` のコピー手順
* Codex plugin の有効化だけでは custom agent が自動登録されない前提
* multi-agent tool がある場合だけ委譲する前提
* Claude Code の `Agent` や `subagent_type` に依存しない説明

## 生成物の扱い

各 plugin 配下の `SKILL.md` は配布物として repository に commit します。
利用者や plugin validator は生成済みファイルだけを見ればよく、生成 script の実行を前提にしません。

編集時は、原則として共通原稿または platform template を更新し、生成 script で両方の `SKILL.md` を再生成します。
手作業で片方だけを更新する場合は、もう片方へ反映すべき共通変更がないか確認します。

## 検証

共通化後の最低検証は次の通りです。

* Claude 用 plugin validation
* Codex 用 plugin validation
* skill validation
* generated `SKILL.md` が最新であることの確認
* `git diff --check`

生成 script を追加する場合は、再生成後に差分が出ないことを確認する command も用意します。

```text
python3 scripts/build_delegate_skills.py --check
```

## 採用しない案

### Codex plugin root を `plugins/` に広げる

`.codex-plugin` を `plugins/codex/.codex-plugin` から `plugins/.codex-plugin` へ移動すると、
Codex plugin root が `plugins/` になります。

この場合、`skills` に `./codex/skills/` のような path は書けますが、同時に `plugins/claude/` も
Codex plugin root 配下に入ります。
これは配布単位と責務境界を曖昧にするため採用しません。

### `../` で兄弟 directory を参照する

Codex plugin manifest の `skills` は plugin root 配下の `./skills/` を指す形が素直です。
兄弟 directory を `../` で参照する構成は、plugin validation や install 後の配置に依存しやすくなります。

共通化のために path 参照を広げるのではなく、生成元を共有して、配布物は各 plugin root 内に閉じます。
