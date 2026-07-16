<!-- Generated from shared/. Do not edit directly. -->

# 実装枝の準備と委譲

## 目次

- Implementer context と枝の lifecycle
- worktree と基準 commit
- mode に応じた TDD/QA
- Implementer の選択
- 委譲 prompt

## Implementer context と枝の lifecycle

上位ルールは **1実装枝 = 1つの新規 Implementer context** とする。実装枝は外部から観測可能な振る舞いを
単位として分け、単独の Acceptance Criteria、検証、受け入れ判断、revert が可能な大きさにする。
各実装枝を開始するときは新しい Implementer を生成し、別の実装枝に同じ Implementer を再利用しない。

同じ Implementer を継続できるのは、同一実装枝を完成させるための段階ゲートと差し戻しに限る。
Acceptance Criteria 未達、仕様誤解、機能欠落、テスト失敗、正常系・異常系・境界値不足、スコープ逸脱、
再検証、`strict` mode の Red / Green / Refactor は、同じ context と worktree で継続する。

枝を統合し、統合後の green を確認して差し戻しが不要になった時点で、その Implementer の役割を終了する。
次の枝は最新の統合済み green な基準コミットから開始する。前の枝から引き継ぐ変更は統合済みコードへ
反映し、コードから読み取れない確定済み制約だけを次の指示へ明記する。

実装枝を開始するときは新規の `Agent` 呼び出しで Implementer を生成する。同一枝の段階ゲートと
差し戻しには `SendMessage` を使い、別の枝へ進むために同じ Agent を継続しない。

## worktree と基準 commit

各実装枝は専用 worktree で隔離する。worktree を用意できない場合は委譲を開始しない。
worktree の目的は並列速度ではなく、枝ごとの diff、検証、差し戻し、revert を独立させることにある。
`isolation: "worktree"` を使い、最新の基準 commit から枝専用の作業環境を作る。

`Agent` ツールの `isolation: "worktree"` を指定し、最新の基準 commit から枝専用 worktree を作る。
実際の worktree path と branch 名は起動後に決まるため、親は値を推測せず、Implementer に確認して
返却物へ含めさせる。

- 共有 fixture、設定、ロックファイル、テストデータ、自動生成物などを複数枝が必要とする場合は、
  親が共有土台として先に確定し、検証済みの基準 commit にする。
- DB、Redis、queue、port、共有 temp、生成 cache、`.env`、外部 API mock は worktree では隔離されない。
  枝専用 resource を割り当てるか、直列実行で衝突を避ける。
- 委譲直前に基準 commit で既存 test、build、typecheck、lint を実行し、green を確認する。
- 基準が red の場合は委譲を開始せず、既存失敗として切り分ける。

## mode に応じた TDD/QA

| 委譲 mode | TDD/QA の強度 |
| --- | --- |
| `lite` | 親は返却の diff とテストを確認し、focused test で green を確認する。段階ゲート、AC 対応表、Red 証跡は親が明示した場合だけ要求する。 |
| `standard` | AC→テスト対応表、境界値、異常系、Red 時点の失敗出力を要求する。返却物を QA ルーブリックの全観点で精査し、親が green を確認する。 |
| `strict` | テスト計画→失敗テスト→実装→Refactor の段階ゲートに分ける。各段階を親が確認し、最終返却物には `standard` と同じ QA を行う。 |

全ての委譲 mode で、親による統合後の検証と最終的な受け入れ判断を省略しない。

`strict` は同じ Implementer と worktree を次の段階で継続する。

1. **テスト計画** — どの AC、境界、異常系をどう検証するかだけを返させ、親が承認する。
2. **失敗テスト** — 実装せず、狙いどおり fail するテストと失敗出力だけを返させ、親が確認する。
3. **Green の実装** — 最小実装で test を通し、後から期待値を実装へ合わせていないか親が確認する。
4. **Refactor と再検証** — 振る舞いを保った整理、focused test、必要な全体検証を行い、親が最終 diff を確認する。

テスト計画では commit を作らない。Red、Green、Refactor の各段階では、段階の変更を commit する。
Red commit は failing test を含むため統合せず、同じ worktree で次段階へ進める。各段階の返答には
その段階の commit SHA と検証結果を含め、最終返却では先頭から末尾までの commit SHA range を返す。
段階の commit 後に未コミット変更を残さない。

段階ゲートを使う枝は、同じサブエージェント（同じ worktree）を `SendMessage` で継続する。
新規の `Agent` 呼び出しは別 context になるため、同一枝の途中で切り替えない。継続不能の場合は、
親が受け入れ済みの失敗テストをその枝へ commit してから次フェーズを委譲する。

## Implementer の選択

難度は行数ではなく、設計の自由度、影響範囲、ドメインの罠、誤実装の代償で判断する。

| Implementer | 使う場面 |
| --- | --- |
| `implementer` | 仕様が明確で範囲が閉じた通常の実装・テスト追加。 |
| `senior-implementer` | 設計判断、複数 module への波及、非自明な algorithm・concurrency、高い失敗コストを伴う枝。 |
| `expert-implementer` | 親相当の推論が必要で、senior では不足する具体的根拠があり、事前審査を通過した枝。 |

通常と senior で迷ったら `senior-implementer` を選ぶ。難所と定型作業が混在する場合は枝を分ける。
expert と迷う場合は senior を選び、expert 候補にする場合だけ
[Expert 選択](expert-selection.md) の事前審査を行う。


## 委譲 prompt

新規 Implementer は親や前の枝の context を持たない前提にする。次の Data を自己完結して渡す。

- 実装枝の目的
- Acceptance Criteria
- 対象範囲と変更禁止範囲
- 最新の基準コミット
- worktree の隔離条件。実際の path と branch 名は起動後に Implementer が確認する
- コードから読み取れない確定済みの設計判断や制約
- 委譲 mode と TDD 要件
- 検証 command
- 完了条件
- commit と返却報告の形式

custom agent の developer instructions にある安定契約を長く再掲せず、タスク固有の Data を中心にする。

```text
## タスク
- 目的: <外部から観測可能な振る舞い>
- 実装内容: <実現する振る舞い>

## 実行 context
- 委譲 mode: <lite / standard / strict>
- 現在の段階: <一括実装 / test plan / Red / Green / Refactor>
- 最新の基準コミット: <green を確認した SHA>
- worktree path と branch 名: <`isolation: "worktree"` で起動後に確認し、返却物へ含める>
- 確定済みの設計判断と制約: <なければ「なし」>
- 検証 command: <focused test / build / typecheck / lint>

## 受け入れ条件
- AC-1: <条件>
- AC-2: <条件>

## scope
- 対象範囲: <path>
- 変更禁止範囲: <path>
- 再利用する共有基盤: <fixture / helper / test data>
- 最低限の境界値・異常系: <具体列挙>

## タスク固有の制約
- <この枝だけに追加する禁止事項や外部制約。なければ「なし」>

## 段階の返却条件
- commit: <不要 / Red commit / Green commit / Refactor commit / 最終 commit SHA range>
- 証跡: <この mode と段階で必要な AC 対応表、Red 出力、検証結果>
```

`lite` では、親が明示した場合だけ AC 対応表と Red 時点の失敗出力を付けること。
`standard` では、Red 時点の失敗出力と
「AC-n → それを検証するテスト名 → 期待値の根拠（仕様のどこから導いたか）」の対応表を必ず付けること。
`strict` の途中段階では、その段階で要求した成果物だけを返させ、最終返却には `standard` と同じ
AC 対応表と Red 証跡を含める。

role profile で代替する場合だけ、担当難度、仕様を広げないこと、指定された段階を越えないこと、
既存 test の弱体化と未承認依存を禁止すること、Code=How / test=What / commit=Why /
comment=Why Not、段階別 commit と返却 schema を短く補う。

最も価値があるのは、親が境界値・異常系を具体化することである。ここを Implementer へ丸投げしない。
