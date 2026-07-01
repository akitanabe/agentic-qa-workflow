# agentic-qa-workflow

実装作業をサブエージェントへ委譲しつつ、親エージェントがマネージャー兼 QA として品質責任を持つための Claude 向けスキル/エージェント定義です。

## 内容

- `plugins/claude/skills/delegate-implementation/SKILL.md`
  - タスク分割、worktree による隔離、委譲プロンプト、返却物の QA、最終検証の進め方を定義します。
- `plugins/claude/agents/implementer.md`
  - 仕様が明確で範囲が閉じた通常実装向けのサブエージェント定義です。
- `plugins/claude/agents/senior-implementer.md`
  - 設計判断や広い影響範囲を伴う高難度実装向けのサブエージェント定義です。

## 基本方針

このリポジトリの中心方針は、委譲しても品質責任を親エージェントが持つことです。サブエージェントは実装を担当し、親エージェントは分割、指示、受け入れ条件、テスト品質、最終検証を主導します。

## 使い方

Claude の plugin/skill/agent 読み込み先に `plugins/claude` 配下を配置して利用します。実装を委譲する場合は、`delegate-implementation` スキルの手順に従い、枝の難度に応じて `implementer` または `senior-implementer` を選択します。

## License

MIT License. See [LICENSE](LICENSE).
