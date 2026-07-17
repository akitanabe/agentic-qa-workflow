---
name: delegate-implementation
description: >-
  Codex で実装作業を委譲しつつ、親エージェントが計画、受け入れ条件、worktree 隔離、
  返却 diff の QA、テスト網羅性レビュー、副作用と責務境界の確認、最終検証、最終報告の責任を
  持つためのワークフロー。ユーザーが Codex に対して実装委譲、マネージャーとしての進行、
  エージェント分担を求めたとき、または `lite` / `standard` / `strict` を明示したときに使う。
  `direct` の明示時や、委譲指示なしにタスク規模だけを理由として使わない。
---
<!-- Generated from shared/. Do not edit directly. -->

# マネージャー＋QA としての委譲

親はタスク分割、Acceptance Criteria、委譲指示、返却 diff の QA、統合、最終検証を担当する。
Implementer は実装を担当するが、最終的な品質責任と受け入れ判断は親から移動しない。

## workflow mode の選択

| route / mode | 選択条件 |
| --- | --- |
| `direct` | 委譲要求がなく、仕様が明確で影響範囲が閉じ、親が直接処理する変更。 |
| `lite` | ユーザーが明示し、仕様が明確で影響範囲が局所的、容易に戻せる変更。 |
| `standard` | 通常の実装委譲、または mode 未指定の明示的な委譲。 |
| `strict` | `strict` が明示された変更、または高リスク、影響範囲が広い、誤実装の代償が大きい変更。 |

`direct` は親が実装する、この skill の外にある経路である。委譲要求がなく `direct` も指定されていない場合、
タスク規模だけでこの skill を発火しない。`direct` が明示された場合も、この skill を発火しない。
`direct` でも、親は必要なテストと検証を実行し、diff review と最終報告を行う。

`lite` / `standard` / `strict` の明示は委譲要求を兼ねる。委譲だけが明示され mode が指定されていない場合は
`standard` を選ぶ。`lite` を自動選択しない。`direct` と委譲が同時に指定された場合は、実装前にユーザーへ
確認する。

委譲 mode の強度は `lite < standard < strict` とする。mode を引き上げた場合は、その具体的なリスクを
ユーザーへ報告する。ユーザーが明示した mode を親都合で引き下げない。`direct` から委譲へ変更する場合は、
ユーザーへ確認する。`lite` の選択条件を満たさなくなった場合は `standard` 以上へ引き上げる。`standard` では
扱えないリスクが判明した場合は `strict` へ引き上げる。仕様が曖昧な場合は mode を選ぶ前に実装を止め、
ユーザーへ確認する。

## 委譲環境の前提

各実装枝は専用 worktree で隔離する。worktree を用意できない場合は委譲を開始しない。
委譲機構または必要な agent が利用できない場合は、利用不能の内容と未着手範囲を報告する。
ユーザーの確認なく親の直接実装へ切り替えない。

この Codex plugin は Claude Code の `Agent` や `subagent_type` 名に依存しない。現在の Codex 環境で
サブエージェントや multi-agent tool が使える場合は、その tool contract に従う。使えない場合は
委譲したふりをせず、要求された委譲面が利用できないことを報告する。

`spawn_agent` または `followup_task` で処理を依頼した後は、対象 worker ごとに `wait_agent` を繰り返し使い、完了通知または返答が返るまで待機する。
1回の待機 timeout は処理継続中を意味し、失敗や応答不能とはみなさない。数分間の無応答を理由に worker を `shutdown` または `interrupt_agent` しない。
worker を終了してよいのは、返答を受け取り、QA・差し戻しのための継続が不要になった後に限る。
ユーザーが明示的に取り消した場合、または tool が回復不能な異常を報告した場合は例外とし、理由を報告する。

## 全体の流れ

1. 目的、入力、出力、Acceptance Criteria、変更範囲、禁止範囲を確定する。
2. mode を選び、共有土台と直列に受け入れる実装枝へ分ける。
3. [実装枝の準備と委譲](references/implementation-branches.md) を読み、基準、worktree、Worker 選択、
   委譲 prompt を準備する。この時点では起動しない。
4. expert 候補の場合だけ、起動前に [Expert 選択](references/expert-selection.md) を読む。
5. 審査と準備が完了した先頭の枝だけを委譲する。
6. Implementer の返答を待ち、返却 commit と実行結果を受け取る。
7. [QA・修正・統合](references/qa-and-integration.md) を読み、diff、テスト、専門 review、修正経路を判断する。
8. 1枝だけを受け入れて統合後の green を確認し、その commit を次の枝の基準にする。
   次の枝があれば手順3へ戻る。
9. 全枝の完了後、統合済み diff review、最終検証、親の最終判断を行う。
10. 最終 gate 後に、各 worker worktree の cleanup の実施可否と結果を確定する。
11. 永続 QA レポートの出力条件を満たす場合だけ
    [永続 QA レポート](references/qa-report.md) を読む。
12. 会話上の最終報告を行う。

共有土台の作成は、実装枝の委譲前に親が行える明示的な例外とする。複数枝が同じ fixture、設定、
テストデータ、生成物を必要とするときだけ先に確定し、検証して基準 commit にする。この例外は、
返却後の機能修正を親が引き取る根拠にはしない。

全ての委譲 mode で、親による統合後の検証と最終的な受け入れ判断を省略しない。
