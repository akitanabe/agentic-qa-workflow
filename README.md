# agentic-qa-workflow

実装作業をサブエージェントへ委譲しつつ、親エージェントがマネージャー兼 QA として品質責任を持つための Claude / Codex 向けスキル定義です。

## 内容

- `plugins/claude/skills/delegate-implementation/SKILL.md`
  - タスク分割、worktree による隔離、委譲プロンプト、返却物の QA、最終検証の進め方を定義します。
- `plugins/codex/skills/delegate-implementation/SKILL.md`
  - Codex plugin として利用するための同等の skill 定義です。Claude Code 固有の `Agent` / `subagent_type` には依存せず、Codex 側の利用可能なサブエージェント機能に合わせて委譲プロンプトを組み立てます。
- `plugins/codex/install/agents/*.toml`
  - Codex 用 custom agent の同梱インストール素材です。Codex plugin の有効化後、必要に応じて user または repo の custom agents へコピーして使います。
- `plugins/claude/agents/implementer.md`
  - 仕様が明確で範囲が閉じた通常実装向けのサブエージェント定義です。
- `plugins/claude/agents/senior-implementer.md`
  - 設計判断や広い影響範囲を伴う高難度実装向けのサブエージェント定義です。
- `plugins/claude/agents/responsibility-boundary-reviewer.md`
  - 実装済み diff の責務混在・境界違反・副作用分散を確認する専用 reviewer 定義です。
- `plugins/claude/agents/refactor-patch-agent.md`
  - reviewer の指摘範囲だけを最小修正するリファクタリング patch 専用エージェント定義です。

## 基本方針

このリポジトリの中心方針は、委譲しても品質責任を親エージェントが持つことです。サブエージェントは実装を担当し、親エージェントは分割、指示、受け入れ条件、テスト品質、最終検証を主導します。

## Claude Code 配布

Claude Code 用 marketplace catalog は `.claude-plugin/marketplace.json` に置き、plugin 本体は `plugins/claude/` にまとめています。GitHub から追加する場合は次を使います。

```text
/plugin marketplace add akitanabe/agentic-qa-workflow
/plugin install agentic-qa-workflow@agentic-qa-workflow-marketplace
```

## Codex 配布

Codex 用 marketplace catalog は `.agents/plugins/marketplace.json` に置き、plugin 本体は `plugins/codex/` にまとめています。ローカル checkout から使う場合は、repo 内の `.agents/plugins` を marketplace として追加し、`agentic-qa-workflow` plugin を有効化します。

```text
codex plugin marketplace add .agents/plugins
```

Custom agent 定義は Codex plugin だけでは自動登録されないため、配布物に含める install 素材として `plugins/codex/install/agents/` に置いています。使う環境では、plugin checkout または plugin install 先から、plugin の利用スコープに合う custom agents directory へコピーします。

- ユーザーインストールとして使う場合: `~/.codex/agents`
- repo に閉じて使う場合: `<repo>/.codex/agents`

```text
plugins/codex/install/install-agents.sh --user
# or: plugins/codex/install/install-agents.sh --repo <repo>
```

コピー後は Codex session を再起動してください。再起動後、Codex の subagent workflow から `implementer`、`senior-implementer`、`responsibility-boundary-reviewer`、`refactor-patch-agent` を明示的に使えます。

## License

MIT License. See [LICENSE](LICENSE).
