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

## workflow の利用例

次の例は、変更名ではなく、具体的な作業内容とリスクから必要な QA を判断するための代表例です。

### direct: typo・文書・小さく閉じた設定修正

委譲要求がなく、仕様が明確で影響範囲が閉じている typo、文書、小さな設定修正は、委譲 mode ではなく skill 外の `direct` route で親が直接処理します。不要な委譲を避けつつ、親が変更に必要な検証、diff review、最終報告を行います。

### standard: 小機能・validation rule・振る舞い変更

通常の小機能、validation rule の追加、test を伴う振る舞い変更を明示的に委譲する場合は `standard` を使います。親は AC と境界値・異常系を具体化し、専用 worktree で実装させます。Implementer は Red 証跡と AC → test → 期待値の根拠の対応を返し、親は diff と test を確認して、統合後の green と最終判断まで担います。

### strict: 失敗コストが高い変更

本番 data migration、file import / export、認証、破壊的操作のような変更でも、名前だけで一律に決めません。失敗コスト、復旧の難しさ、部分失敗時の整合性、認可の誤りという具体的なリスクが高い場合に `strict` を使います。同じ実装枝、Implementer context、worktree でテスト計画 → Red → Green → Refactor を段階 gate に分け、親が各段階と統合後の green を確認します。

### 専門 reviewer を選ぶとき

責務境界、test 品質、security / side-effect の専門 reviewer は、`strict` であることだけを理由に一律で選びません。返却 diff に対応する具体的なリスクがある場合、またはユーザーが明示した場合だけ選び、reviewer に最終判断を委ねません。記述原則を最終整理する `writing-principles-refactorer` は、これらの専門 reviewer とは別の役割です。

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
