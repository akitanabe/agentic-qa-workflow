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

実装枝を開始するときは `spawn_agent` で新規 Implementer を生成する。
新規 Implementer の生成時は必ず `fork_turns: "none"` を指定する。親の会話 context や前の枝の履歴を
継承させず、確定済みの実装指示だけを渡す。同一枝の段階ゲートと差し戻しには `followup_task` を使い、
別の枝へ進むために同じ worker を継続しない。

## worktree と基準 commit

各実装枝は専用 worktree で隔離する。worktree を用意できない場合は委譲を開始しない。
worktree の目的は並列速度ではなく、枝ごとの diff、検証、差し戻し、revert を独立させることにある。

親が最新の基準 commit から枝専用 worktree と branch を作成し、絶対 worktree path、branch、基準 commit を
Implementer へ渡す。Implementer はファイル変更前に、作業場所が指定 worktree であること(`pwd -P`)、
branch 一致、HEAD が基準 commit と一致すること、`git status --short` が空であることの開始条件4点を
確認し、1つでも不成立なら何も変更せず親へ返す。reset / merge / checkout などで自力修復しない。
worker は指定 worktree の外を編集しない。cleanup は親が `git worktree remove` で行う。


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

### Red 証跡と regression Green 例外

`standard` と `strict` では、新機能または未実装仕様を検証する test は Red 必須とし、失敗出力または
段階 commit で未実装時の失敗を確認する。この要件を、test 追加時にすでに存在する振る舞いを固定する
ための作業へ形式的に適用しない。既存挙動を固定する regression test に限り、次の根拠を返却物へ含める
ことで追加時点で Green であることを許可する。

- 既存挙動を固定する追補 test であること
- 対応する AC
- 期待値の根拠
- 既存実装がすでに仕様を満たしていたこと

これは「最初から Green ならよい」という一般例外ではない。`strict` でも Test plan / Red / Green /
Refactor の段階順序を維持し、Red gate で上記の Green 結果と根拠を確認する。既存実装がすでに AC を
満たすため Green 実装が不要な段階では、空 commit を要求しない。形式的な Red を作るために本番 code を
一時変更してはならない。

mutation は親が明示した一時検証に限定する。親は対象、方法、復元確認、検証 command を明示し、mutation
を commit してはならない。変更禁止範囲や本番 code を mutation の対象にしてはならない。検証後は変更が
残っていないことを親と Implementer の双方が確認する。

`strict` は同じ Implementer と worktree を次の段階で継続する。

1. **テスト計画** — どの AC、境界、異常系をどう検証するかだけを返させ、親が承認する。
2. **失敗テスト** — 新機能または未実装仕様では、実装せず、狙いどおり fail するテストと失敗出力だけを
   返させ、親が確認する。regression Green 例外では、追加時点で Green の test と上記4項目を返させる。
3. **Green の実装** — 最小実装で test を通し、後から期待値を実装へ合わせていないか親が確認する。
4. **Refactor と再検証** — 振る舞いを保った整理、focused test、必要な全体検証を行い、親が最終 diff を確認する。

テスト計画では commit を作らない。Red、Green、Refactor の各段階では、段階の変更を commit する。
新機能または未実装仕様の Red commit は failing test を含むため統合せず、同じ worktree で次段階へ進める。
regression Green 例外の Red 段階では passing test を commit し、変更がない Green / Refactor 段階に空 commit
を作らない。各段階の返答には、その段階に commit があれば SHA と検証結果を含め、最終返却では先頭から
末尾までの commit SHA range を返す。段階の commit 後に未コミット変更を残さない。

段階ゲートを使う枝は、同じサブエージェント（同じ worktree）を `followup_task` で継続する。
新しい worker の起動は別 context になるため、同一枝の途中で切り替えない。継続不能の場合は、
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

worker を選ぶ前に Codex の custom agent リストを確認する。`implementer`、`senior-implementer`、
`expert-implementer`、`expert-selection-reviewer`、`responsibility-boundary-reviewer`、
`test-quality-reviewer`、`writing-principles-reviewer`、`security-side-effect-reviewer`、
`review-patch-refactorer` がすべて表示されるなら、この確認だけで次へ進む。

custom agent が不足する場合は `$install-custom-agents` を使い、scope と既存版を確認する。
ユーザー確認なしに既存ファイルを上書きしない。インストールまたは更新後は Codex session の再起動を
依頼して処理を終了し、再起動後に agent リストを確認する。

通常または senior の agent 名を指定できない場合は、prompt 内の短い role profile で代替できる。
ただし expert は、登録または agent 名の指定ができない場合は role profile へ代替せず、
[Expert 選択](expert-selection.md) の利用不能時ルールに従う。

## 委譲 prompt

新規 Implementer は親や前の枝の context を持たない前提にする。次の Data を自己完結して渡す。

- 実装枝の目的
- Acceptance Criteria
- 変更を許可する物理的範囲、変更を禁止する物理的範囲、この枝でやらないこと
- 最新の基準コミット
- 絶対 worktree path と branch 名
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
- 絶対 worktree path と branch 名: <path / branch>
- 確定済みの設計判断と制約: <なければ「なし」>
- 検証 command: <focused test / build / typecheck / lint>

## 受け入れ条件
- AC-1: <条件>
- AC-2: <条件>

## scope
- 変更を許可する物理的範囲: <allowed_paths>
- 変更を禁止する物理的範囲: <forbidden_paths>
- この枝でやらないこと: <out_of_scope。空なら「なし」>
- 再利用する共有基盤: <fixture / helper / test data>
- 最低限の境界値・異常系: <具体列挙>

## タスク固有の制約
- <この枝だけに追加する禁止事項や外部制約。なければ「なし」>

## 段階の返却条件
- commit: <不要 / Red commit / Green commit / Refactor commit / 最終 commit SHA range>
- 証跡: <この mode と段階で必要な AC 対応表、Red 出力、検証結果>
```

`out_of_scope` はパス制約へ統合せず、各項目の意味を変えずに「この枝でやらないこと」へ列挙する。
Implementer は、その責務・作業が枝の完成に必要になった場合は変更せず、必要性と理由を親へ報告する。

`lite` では、親が明示した場合だけ AC 対応表と Red 時点の失敗出力を付けること。
`standard` では、Red 時点の失敗出力と
「AC-n → それを検証するテスト名 → 期待値の根拠（仕様のどこから導いたか）」の対応表を必ず付けること。
`strict` の途中段階では、その段階で要求した成果物だけを返させ、最終返却には `standard` と同じ
AC 対応表と Red 証跡を含める。regression Green 例外では、Red 時点の失敗出力に代えて上記4項目と
追加時点の Green 結果を付ける。

role profile で代替する場合だけ、担当難度、仕様を広げないこと、指定された段階を越えないこと、
既存 test の弱体化と未承認依存を禁止すること、Code=How / test=What / commit=Why /
comment=Why Not、段階別 commit と返却 schema を短く補う。

最も価値があるのは、親が境界値・異常系を具体化することである。ここを Implementer へ丸投げしない。
