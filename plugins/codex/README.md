# Agentic QA Workflow for Codex

実装を subagent へ委譲しながら、親 Codex エージェントが計画、受け入れ判断、QA、最終検証の責任を持つための Codex plugin です。

## 構成

- `skills/delegate-implementation/SKILL.md`
  - タスク分割、worktree 隔離、委譲、返却 diff とテストの QA、最終検証を定義します。
- `skills/install-custom-agents/SKILL.md`
  - 同梱 custom agent のインストール状況を確認し、安全に導入・更新します。
- `install/agents/*.toml`
  - Codex の user scope または project scope へコピーする custom agent 定義です。
- `install/install-agents.sh`
  - 既存ファイルを確認なしに上書きせず、custom agent の導入・更新を行います。

`delegate-implementation` skill と `install/agents/*.toml` はリポジトリの `shared/` から生成されています。生成済みファイルを直接編集せず、共通原稿を更新してください。開発方法は[ルート README](../../README.md)を参照してください。

## Plugin のインストール

GitHub repository を marketplace として登録し、plugin をインストールします。

```text
codex plugin marketplace add akitanabe/agentic-qa-workflow
codex plugin add agentic-qa-workflow@personal
```

ローカル checkout を使う場合は、repository root で次を実行します。

```text
codex plugin marketplace add .agents/plugins
codex plugin add agentic-qa-workflow@personal
```

登録状態は次のコマンドで確認できます。

```text
codex plugin marketplace list
codex plugin list
```

Plugin の追加後は Codex session を再起動してください。Codex plugin の marketplace と構造については、[Codex の公式ドキュメント](https://developers.openai.com/codex/plugins/build)を参照してください。

## Custom agent のインストール

Codex plugin は skill を配布しますが、`install/agents/*.toml` を custom agent directory へ自動登録しません。Custom agent は利用範囲を選んで別途インストールします。

- user scope: `~/.codex/agents/`
- project scope: `<repo>/.codex/agents/`

Plugin をインストールした場合は、新しい Codex session で `$install-custom-agents` を使うのが基本です。user scope または対象 repository を指定して、状態確認からインストールまでを依頼してください。

ローカル checkout から直接実行する場合は、最初に現在の状態を確認します。

```text
plugins/codex/install/install-agents.sh --check --user
# or
plugins/codex/install/install-agents.sh --check --repo <repo>
```

未インストールまたは更新が必要な場合、`--check` は終了コード `3` を返します。新規インストールは同じ scope で `--check` を外して実行します。

```text
plugins/codex/install/install-agents.sh --user
# or
plugins/codex/install/install-agents.sh --repo <repo>
```

既存または古い定義がある場合は自動で上書きしません。内容を確認し、上書きしてよい場合だけ `--force` を付けます。

```text
plugins/codex/install/install-agents.sh --force --user
# or
plugins/codex/install/install-agents.sh --force --repo <repo>
```

インストール後は Codex session を再起動してください。再起動するまでは custom agent の導入後に委譲作業を続行しません。

Custom agent の配置と設定形式については、[Codex subagents の公式ドキュメント](https://developers.openai.com/codex/agent-configuration/subagents)を参照してください。

## Custom agent

| Agent | 担当 |
| --- | --- |
| `implementer` | 仕様が明確で範囲が閉じた通常実装 |
| `senior-implementer` | 設計判断や広い影響範囲を伴う高難度実装 |
| `responsibility-boundary-reviewer` | 責務混在、境界違反、副作用分散のレビュー |
| `test-quality-reviewer` | テストの仕様対応、振る舞い、網羅性のレビュー |
| `writing-principles-refactorer` | `How / What / Why / Why Not` の配置、命名、説明の局所修正 |
| `security-side-effect-reviewer` | 外部 I/O、破壊的操作、機密データ、セキュリティ影響のレビュー |
| `review-patch-refactorer` | 専門 reviewer が具体的に指摘した範囲の最小修正 |

## 使い方

Custom agent の登録を確認した新しい session で、実装委譲を明示して `$delegate-implementation` を使います。

```text
$delegate-implementation を使い、この実装を subagent に委譲して親が QA まで担当してください。
```

タスクが大きいという理由だけでは自動的に委譲しません。親 Codex エージェントは返却報告だけで受け入れず、diff、テスト内容、副作用、責務境界を確認してから統合します。

## Marketplace の更新

Git marketplace の snapshot は次のコマンドで更新できます。

```text
codex plugin marketplace upgrade personal
```

Plugin または custom agent を更新した場合は、custom agent の状態を再確認し、必要に応じて明示的に上書きした後で Codex session を再起動してください。
