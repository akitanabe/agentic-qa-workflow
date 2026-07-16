# agentic-qa-workflow

実装作業をサブエージェントへ委譲しつつ、親エージェントがマネージャー兼 QA として品質責任を持つための Claude / Codex 向けスキル定義です。共通原稿から各 platform の plugin 配布物を生成します。

## 構成

編集元は `shared/` に集約しています。

- `shared/skill/delegate-implementation/`
  - `SKILL.md` に workflow の核、`references/*.md` に実装枝、expert 選択、QA・統合の詳細を分けた共通原稿です。
- `shared/agents/*.md`
  - 通常実装、高難度実装、expert 実装、専門レビュー、指摘範囲の最小修正を担当する 9 種類の agent の共通原稿です。
- `shared/terms.toml`
  - Claude Code と Codex で異なる用語を定義します。
- `shared/VERSION`
  - 両 plugin と Codex custom agent インストール素材の共通 version です。

`scripts/build_plugin_assets.py` が共通原稿を platform ごとに変換し、次の配布物を生成します。

- `plugins/claude/skills/delegate-implementation/SKILL.md`
- `plugins/claude/skills/delegate-implementation/references/*.md`
- `plugins/claude/agents/*.md`
- `plugins/codex/skills/delegate-implementation/SKILL.md`
- `plugins/codex/skills/delegate-implementation/references/*.md`
- `plugins/codex/install/agents/*.toml`
- 両 plugin の manifest version と `plugins/codex/install/VERSION`

`plugins/` 以下の生成対象ファイルには generated warning が付いています。これらを直接編集せず、対応する `shared/` の原稿を変更してください。

## 基本方針

このリポジトリの中心方針は、委譲しても品質責任を親エージェントが持つことです。サブエージェントは実装を担当し、親エージェントは分割、指示、受け入れ条件、テスト品質、最終検証を主導します。

## 配布

導入方法と platform 固有の構成は、それぞれの README を参照してください。

- [Claude Code plugin](plugins/claude/README.md)
- [Codex plugin](plugins/codex/README.md)

## 編集と生成

共通原稿を編集したら、配布物を再生成します。

```text
python3 scripts/build_plugin_assets.py
```

生成物が共通原稿と一致しているかは、ファイルを書き換えない `--check` で確認できます。

```text
python3 scripts/build_plugin_assets.py --check
python3 -B -m unittest discover -s tests -p 'test_build_plugin_assets*.py'
```

## License

MIT License. See [LICENSE](LICENSE).
