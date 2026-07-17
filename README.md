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

## workflow mode の選択

`direct` は委譲 mode ではなく、親エージェントが直接処理する、この skill の外にある route です。`lite`、`standard`、`strict` は実装を委譲するときの mode です。

| route / mode | 用途 |
| --- | --- |
| `direct` | 委譲要求がなく、仕様が明確で影響範囲が閉じる変更。 |
| `lite` | ユーザーが明示し、仕様が明確で影響範囲が局所的、容易に戻せる変更。 |
| `standard` | 通常の実装委譲、または mode 未指定の明示的な委譲。 |
| `strict` | `strict` が明示された変更、または高リスク、影響範囲が広い、誤実装の代償が大きい変更。 |

委譲要求がない場合は、タスク規模だけを理由にこの skill を発火しません。そのうち、仕様が明確で影響範囲が閉じる変更は `direct` を選びます。明示的な委譲で mode が未指定なら `standard` を選びますが、具体的なリスクが高ければ `strict` へ引き上げます。`lite` はユーザーが明示した場合だけ選び、`lite` を自動選択しません。

委譲 mode の強度は `lite < standard < strict` です。具体的なリスクに応じて引き上げますが、ユーザーが明示した mode を親都合で引き下げません。`direct` から委譲への変更は強度の変更ではなく責務境界の変更であるため、ユーザーに確認します。

詳細な選択条件と委譲手順は、共通原稿の正本である [shared/skill/delegate-implementation/SKILL.md](shared/skill/delegate-implementation/SKILL.md) を参照してください。

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
