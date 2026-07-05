---
name: delegate-implementation
description: >-
  Codex で実装作業を委譲しつつ、親エージェントが計画、受け入れ条件、worktree 隔離、
  返却 diff の QA、テスト網羅性レビュー、副作用と責務境界の確認、最終検証、最終報告の責任を
  持つためのワークフロー。ユーザーが Codex に対して、サブエージェントや worker への実装委譲、
  マネージャーとしての進行、エージェント分担、agentic implementation workflow を明示的に
  求めたときに使う。タスクが大きいだけでは自動起動せず、委譲が明示または明確に求められたときだけ使う。
---

# マネージャー + QA としての委譲

委譲は実行手段であって、責任の移譲ではない。設計、タスク分割、受け入れ条件、レビュー、最終検証は
親 Codex エージェントが握る。worker は実装者として扱い、その成果物は受け入れ前に必ず親が確認する。

この Codex plugin は Claude Code の `Agent` や `subagent_type` 名に依存しない。現在の Codex 環境で
サブエージェントや multi-agent tool が使える場合は、その tool contract に従って使う。使えない場合は
委譲したふりをせず、親が直接作業するか、要求された委譲面が利用できないことを報告する。

## 全体フロー

1. タスクを「共有の土台」と「直列に受け入れる枝」に分ける。
2. 共有の土台を先に作り、検証し、委譲前の初期 baseline としてコミットする。
3. 依存関係、リスク、検証しやすさに基づいて枝をキュー化する。
4. 最新 baseline から先頭の枝だけを委譲する。可能なら git worktree で隔離する。
5. 返却された diff とテストを親が読む。worker の完了報告だけで受け入れない。
6. diff が層をまたぐ、副作用を追加する、構造を変える場合は責務境界ゲートを通す。
7. 1枝だけ統合ブランチへ取り込み、focused check と関連する広めの check を実行する。
8. green になった統合状態を次の baseline としてコミットし、次の枝へ進む。
9. サイクル最後に、環境が提供するなら現在の `/review` workflow を実行する。なければ同等の
   統合済み diff review を親が行い、その結果を最終報告に含める。

## Baseline ルール

baseline はコミットで前進させる。親の未コミット変更を worker に暗黙に渡さない。各枝は最新の
受け入れ済み baseline から作り、reject した枝を捨てても受け入れ済み作業に影響しないようにする。

複数の枝が共有 fixture、設定、lockfile、生成物、helper を必要とする場合は、それらを先に共有の土台へ
寄せる。複数 worker に同じ土台を別々に再実装させない。

## 枝の種別ごとの TDD 強度

| 枝の種別 | 必要な強度 |
| --- | --- |
| 軽い明確な修正 | worker をやや信頼し、親は diff とテストを読んで green を確認する。必要でなければ段階ゲートや AC 表は課さない。 |
| 通常実装 | AC とテストの対応表、境界値・異常系、Red 証跡、親 QA、親による green 確認を求める。 |
| 重要または高リスク実装 | テスト計画、失敗テスト、実装の段階ゲートに分ける。可能なら同じ worker / worktree で継続する。 |
| 仕様が曖昧 | まず仕様質問とテスト計画を返させる。推測で実装しない。 |

既存テストや共有の土台に触る枝は「軽い」にしない。迷う場合は一段重い側に倒す。

## Worktree 隔離

利用できる場合は、委譲する枝ごとに専用 git worktree を使う。目的は並列速度ではなく、隔離と
レビューしやすさである。外部リソースは worktree では隔離されないため、必要に応じて port、DB、
queue、temp path、cache、`.env`、API mock を枝ごとに分ける。

worker には次を返させる。

- worktree path と branch 名
- baseline commit
- 返却 commit SHA range
- 変更ファイル
- 実行した command と結果要約
- 未コミット変更が残る場合は、その内容と理由

## Worker 選択

Codex 環境によって worker の起動方法は異なる。plugin 固有の agent 名に依存せず、prompt 内で次の
role profile を使い分ける。

| role profile | 使う場面 |
| --- | --- |
| 通常 implementer | 仕様が明確で範囲が閉じた実装またはテスト追加。 |
| senior implementer | 設計判断、複数 module への波及、非自明な algorithm / concurrency、誤実装の代償が大きい枝。 |
| responsibility-boundary reviewer | 実装済み diff の責務混在、境界違反、副作用分散を確認する。ファイルは編集しない。 |
| refactor patch worker | responsibility-boundary reviewer の指摘を解消する最小 patch だけを作る。 |

同じ worker conversation を継続できる環境では、段階ゲートや差し戻しにそれを使う。継続できない場合は、
親が受け入れ済みの失敗テストや review input を枝へコミットしてから次フェーズを委譲する。

## 委譲プロンプトテンプレート

実装 worker にはこのテンプレートをタスクに合わせて埋めて渡す。最も価値があるのは、親が境界値と
異常系を具体的に列挙することである。

```markdown
## 役割
あなたはこの枝の <通常 implementer / senior implementer> です。
仕様を勝手に広げないでください。要件が曖昧、または既存設計と衝突する場合は、推測せず判断点として
返してください。

## タスク
<外部から観測できる振る舞いとして実装内容を書く。>

## 実行コンテキスト
- 枝の種別: <軽い / 通常 / 高リスク / 仕様曖昧>
- baseline commit: <SHA>
- 作業環境: <worktree path が分かれば書く。分からなければ自分で確認して返すよう指示する>
- 検証 command: <親が確認した focused test / build / typecheck / lint command>
- 完了条件: 検証済み変更を commit し、返却 commit SHA range を報告する

## 受け入れ条件
- AC-1: <条件>
- AC-2: <条件>

通常実装と高リスク実装では、次の対応表を返してください:
AC -> test name -> expected value の根拠。

## Scope
- 触ってよい file: <paths>
- 触ってはいけない file: <paths>
- 再利用する共有の土台: <fixtures/helpers/test data>
- 禁止: test の削除や skip、既存 assertion の弱体化、依存追加、無関係 file の変更。
  必要な場合は判断点として返す。

## Test 品質
- 外部から観測できる振る舞いだけを test する。private internals や実装手順を test しない。
- 正常系、境界値、異常系、分岐を cover する。
- 最低限 cover する case: <null/empty/zero/max/min/invalid/exception paths>
- Red -> Green -> Refactor を守る。Red 時点の失敗出力を返す。
- comment は非自明な制約、前提、test 意図に限って追加する。

## 返却物
- worktree path、branch、baseline commit、返却 commit SHA range
- 変更 file
- AC -> test 対応、境界値/異常系 coverage
- 実行した command と結果
- Red の失敗出力
- 前提、判断点、未 cover case
```

## 親 QA ルーブリック

必ず diff と test を親が開いて読む。

実装を確認する。

- scope creep、無関係 file、隠れた依存追加、公開 API 破壊がないこと
- 既存の設計、命名、error handling pattern に従っていること
- 既存 test が削除、skip、弱体化されていないこと
- resource handling、security、concurrency、副作用が悪化していないこと

test を確認する。

- 外部から観測できる振る舞いを assert していること
- 親が列挙した境界値と異常系が実際に cover されていること
- expected value が実装から逆算された値ではなく、仕様から導かれていること
- Red 証跡または Red/Green commit により、実装前に test が失敗したことが分かること

検証 command は親が自分で実行する。枝 worktree の green は、その枝が自己完結していることだけを示す。
統合ブランチでの検証は、受け入れ済み baseline と組み合わせても動くことを示す。worktree を使う場合は
両方を省略しない。

## 責務境界ゲート

親 QA の後、必ず軽量な責務確認を行う。次のいずれかに該当する場合は専用 reviewer worker を使う。

- diff が複数層をまたぐ
- DB、API、HTTP、file、mail、time、random、queue などの外部 I/O を追加する
- boolean flag や mode argument で大きな振る舞いを切り替える
- adapter、service、manager、handler、processor、新しい layer などの抽象化を追加する
- 入力整理、業務判断、副作用、出力整形が混在して見える
- 親 QA で境界問題の疑いがあるが、通常の correctness check だけでは判断しにくい

reviewer には commit range、変更 file list、`git diff <base>...HEAD`、task summary、acceptance criteria
だけを渡す。reviewer が枝 worktree を見られる前提にしない。

reviewer の出力は次の形式にする。

1. 全体判定: `問題なし`、`軽微`、`修正推奨`、`修正必須`
2. 指摘: location、type、reason、impact、minimal fix
3. 過剰抽象化を避ける注意点
4. diff 外の既存課題。判定とは分ける

`修正推奨` と `修正必須` は、原則として同じ implementer / worktree へ戻す。元 worker を継続できない、
または修正が reviewer 指摘範囲の最小 refactor に閉じる場合だけ refactor patch worker を使う。

## 受け入れまたは reject

親がその場で直してよいのは、product 判断や設計判断を伴わない表層だけである。例: import、format、
明らかな名前、comment。

次は黙って直さず hard reject する。

- 境界値または異常系 test の欠落
- expected value の根拠不明または捏造疑い
- 禁止 file の変更
- 既存 test の弱体化
- 未承認 dependency
- 仕様拡張
- scope creep
- test 未実行、または失敗 test の放置

reject するときは、何が失敗し、なぜ受け入れ不可で、どう修復するかを AC に紐づけて具体的に返す。

## 最終報告

報告には次を含める。

- 変更内容
- worker が検証したこと
- 統合後に親が検証したこと
- `/review` または同等の統合済み diff review で確認したこと
- 未検証の残り
