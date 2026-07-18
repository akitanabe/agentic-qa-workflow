# Branch Plan 正規スキーマ仕様

`plan-implementation-branches` Skill の出力であり、`delegate-implementation` への入力となる
Branch Plan の完全なスキーマ仕様を定める。

運用上の正本は、plugin へ配布される次の2つの reference に分かれる。本書は両者を統合した
完全仕様であり、内容は正本と一致させる。

- スキーマ本体・blocking violation code・状態遷移・tests の意味:
  `shared/skill/plan-implementation-branches/references/branch-plan-schema.md`
- implementation_stages の実行規約・Executor 側の再検証:
  `shared/skill/delegate-implementation/references/branch-plan-intake.md`

設計の経緯とレビューでの確定事項は
[issue #46](https://github.com/akitanabe/agentic-qa-workflow/issues/46) と本ファイルの
git 履歴を参照。

## 設計方針

- 実装枝の契約(外部から観測可能な振る舞い単位、単独の Acceptance Criteria・検証・受け入れ判断・
  revert)は `delegate-implementation` の現行契約を変更せずそのまま使う。
- 大きすぎる振る舞いは独立した枝ではなく、1実装枝内の `implementation_stages` として表現する。
  stage は AC を所有せず、受け入れ判断・統合・revert はすべて枝単位で行う。
- AC の割り当ては枝側の一方向参照だけにする。AC 側と枝側の両方に割り当てを書くと二重管理になり、
  validation がどちらを正とするか決められないため。この正規化により「未割り当て AC」と
  「primary 不在の AC」は同一の検査に縮退する。
- Branch Plan の承認(`approval`)と委譲開始権限(`delegation`)は独立した Data とする。承認は
  計画の確定だけを意味し、委譲開始はユーザーの明示的な委譲要求だけを根拠に親エージェントが
  権限を設定する。
- `validation.blocking` は安定した code を持つ violation の配列とし、planning Skill と Executor が
  同じ検査規則を共有する。承認可否は blocking violation の有無だけで決まり、自己評価 boolean は
  参考情報に限定する。

## スキーマ本体

```yaml
# ============================================================
# Branch Plan 正規スキーマ (plan-implementation-branches の出力)
# ============================================================

status: blocked | awaiting_review | approved
# blocked:          unresolved_decisions または validation.blocking のいずれかが非空
# awaiting_review:  confirmation_mode: review で blocking なし。ユーザー承認待ち
# approved:         承認済み。unresolved_decisions と validation.blocking がすべて空であることが前提

confirmation_mode: review | auto
# すべての status で保持する。既定は review。auto はユーザーが明示した場合のみ。
# blocked の解消後にどちらへ遷移するかは、この値から復元する

approval:
  method: null | user | auto    # 未承認の間は null。auto は「Branch Plan の承認」だけを
                                # 自動化した記録であり、委譲開始権限を含まない

delegation:                     # 承認とは独立した委譲開始権限
  authorized: false             # planning Skill は常に false で返す
  authorized_by: null | user    # ユーザーの明示的な委譲要求だけを根拠に親エージェントが設定する。
                                # どの status でも記録できるが、委譲開始には status: approved が別途必要
  requested_mode: null | lite | standard | strict
  # ユーザーが明示した委譲 mode。mode の明示は現行契約どおり委譲要求を兼ねるため、
  # requested_mode が非 null なら authorized: true / authorized_by: user であること。
  # mode 未指定の明示的な委譲要求は null のまま保持し、Executor が standard を選ぶ。
  # Executor が実際に採用した mode は Branch Plan へ書き戻さず、実行 Data として保持して
  # 最終報告で報告する

implementation_plan:
  summary: <実装目的の1行要約>
  source: <元プランの所在。path / issue URL / 「会話内」>   # 任意

acceptance_criteria:            # 元プランの AC を原文のまま保持する。言い換え禁止
  - id: AC-1                    # 安定 ID。枝の増減で振り直さない
    text: <元プランの原文>

unresolved_decisions:           # blocking のみ。1件でもあれば status: blocked
  - question: <確定が必要な問い>
    affects:                    # 型付き参照。kind ごとに id の必須・禁止が決まる
      - kind: branch            # id 必須。branch id の存在を検査する
        id: <branch id>
      - kind: ac-assignment     # id 必須。AC id の存在を検査する
        id: <AC id>
      - kind: execution-order   # id を持たない
    # default_assumption は持たない。仮定で進めてよい不足は assumptions へ

assumptions:                    # minor のみ。枝構造・実行順序・AC 割り当てに影響しない仮定
  - topic: <対象>
    assumption: <置いた仮定>
    rationale: <この仮定が枝構造に影響しない理由>

shared_foundation:              # 親が委譲前に実装する明示的な例外。委譲枝としては表現しない
  required: true | false        # false の場合、以下のフィールドは省略可
  executor: parent              # 固定値
  condition: <複数枝が共有する fixture / 設定 / テストデータ等の具体>
  allowed_paths: []
  forbidden_paths: []
  foundation_criteria: []       # 共有土台自身の完成条件。元 AC の言い換え禁止
  verification: []              # 基準 commit にする前の検証 command
  covers_acceptance_criteria: []  # 固定で空。元 AC の完成責任を負わないことをスキーマ上明示

branches:
  - id: <kebab-case>
    title: <短い表題>
    purpose: <外部から観測可能な振る舞い>      # 委譲 prompt の「目的」にそのまま渡せる粒度
    depends_on: []                             # 他枝の id。循環禁止
    covers_acceptance_criteria: [AC-1]         # この枝が完成責任(primary)を持つ AC。
                                               # 全 AC がちょうど1枝の covers に現れ、
                                               # 各枝は1件以上の AC を所有すること
    verifies_acceptance_criteria: []           # 完成責任は負わないが検証に参加する AC
                                               # (旧APIパリティの再確認など)。枝間で重複可
    branch_criteria: []                        # 枝固有の派生条件。AC の言い換え禁止
    allowed_paths: []
    forbidden_paths: []
    tests: [unit | integration | e2e | contract | regression]
    # 1つ以上必須。テスト種別だけを保持し、具体的なテスト名・実行 command は持たない
    # (「tests / stage_tests の意味」の節を参照)
    out_of_scope: []
    risk:
      level: low | medium | high
      reasons: []
    implementation_stages:      # 任意。1つの振る舞いが大きすぎる場合のみ。宣言時は2 stage 以上。
                                # 宣言した枝は strict の段階ゲート機構で実行する(実行規約の節を参照)
      - id: <kebab-case>
        stage_goal: <この stage の中間ゲート条件。AC を所有しない>
        allowed_paths: []       # 任意。枝の allowed_paths の部分集合に限る
        stage_tests: []         # 全 stage の和集合が枝の tests と一致すること
    stages_reason: <stages を使う理由>   # implementation_stages 宣言時は必須

execution:
  order: []                     # 全枝の id を1回ずつ。depends_on の topological order であること

delegation_mode_proposal:       # high risk の枝が存在し、delegation.requested_mode が strict でない
                                # (null を含む)場合は出力必須。それ以外は出力しない
  propose: strict               # strict 以外は提案しない。low risk から lite を提案しない
  reasons: []

decision:                       # 分割しない(branches が1枝)場合は必須
  split: false
  reason: <1枝で受け入れ判断・差し戻し・テスト実行が閉じる根拠>

override:                       # ユーザーが分割の統合・修正を指示した場合のみ
  merge_branches: true
  reason: <ユーザーが示した理由>

validation:
  blocking: []                  # violation の配列。1件でもあれば status: blocked
  # - code: <violation code 表の安定 code>
  #   path: <問題があるスキーマ上の path。例: branches[1].allowed_paths>
  #   message: <修正に必要な説明>
  self_assessment:              # 参考情報。承認可否の判定には使わない
    action_boundaries_isolated: true      # 補助指標(第一基準ではない)
    test_boundaries_clear: true
    excessive_fragmentation: false
```

## blocking violation code

planning Skill と Executor は同じ検査規則を使う。Executor は planning Skill の自己申告を信用せず、
入力 Data から再計算する。

| code | 検査内容 |
| --- | --- |
| `duplicate-id` | branch / stage / AC の id 重複 |
| `unknown-reference` | 存在しない branch id / AC id への参照(`depends_on`、`covers_acceptance_criteria`、`verifies_acceptance_criteria`、`execution.order`、`unresolved_decisions.affects`) |
| `ac-unassigned` | どの枝の `covers_acceptance_criteria` にも現れない AC |
| `ac-duplicate-primary` | 複数枝の `covers_acceptance_criteria` に現れる AC |
| `branch-without-primary-ac` | primary AC を1件も所有しない実装枝 |
| `dependency-cycle` | `depends_on` の循環 |
| `execution-order-invalid` | `execution.order` の不足、重複、依存順序違反 |
| `scope-conflict` | 同一枝内の `allowed_paths` / `forbidden_paths` の矛盾、stage `allowed_paths` の枝範囲逸脱 |
| `tests-missing` | 枝の `tests` が空 |
| `stages-invalid` | stage 数不足(1個)、`stages_reason` 欠落、`stage_tests` の和集合が枝の `tests` と不一致 |
| `branch-contract-violation` | 外部から観測可能な振る舞い単位、単独の受け入れ判断、単独 revert という実装枝契約を満たさない枝 |
| `state-invalid` | `status` と他フィールドの矛盾(`approved` なのに `unresolved_decisions` が非空など)。有効な組み合わせ表から再計算する |
| `approval-invalid` | `approval.method` と `status` / `confirmation_mode` の矛盾(`awaiting_review` なのに `method` が非 null、`review` なのに `auto` 承認など) |
| `delegation-invalid` | `delegation` 内の矛盾(`authorized: false` なのに `authorized_by: user`、`requested_mode` が非 null なのに `authorized: false` など) |
| `mode-proposal-invalid` | `delegation_mode_proposal` の要否・内容が `requested_mode` と枝の risk からの再計算と一致しない(必要時の欠落、不要時の出力、`strict` 以外の提案) |

トップレベル状態は値を個別に検査せず、次の有効な組み合わせ表から検査する。表にない組み合わせは
`state-invalid` / `approval-invalid` / `delegation-invalid` を生成する。

| status | approval.method | confirmation_mode |
| --- | --- | --- |
| `blocked` | `null` | `review` / `auto` |
| `awaiting_review` | `null` | `review` のみ |
| `approved` | `user` | `review` のみ |
| `approved` | `auto` | `auto` のみ |

| delegation.authorized | authorized_by | requested_mode |
| --- | --- | --- |
| `false` | `null` | `null` |
| `true` | `user` | `null`(mode 未指定の委譲要求。Executor が `standard` を選ぶ) |
| `true` | `user` | `lite` / `standard` / `strict` |

`branch-contract-violation` は機械検査ではなく planning Skill と Executor の判定で生成する。
実装枝契約に関わる判定(単独 review 可能性、revert 範囲の隔離、禁止範囲の明確さ)はこの code と
`scope-conflict` で表現し、`false` のまま承認へ進む経路を持たない。

## 状態遷移と権限

| 遷移 | 実行主体 | 条件 |
| --- | --- | --- |
| (生成) → `blocked` | planning Skill | `unresolved_decisions` または `validation.blocking` が非空 |
| (生成) → `awaiting_review` | planning Skill | `confirmation_mode: review` かつ blocking なし |
| (生成) → `approved` (`method: auto`) | planning Skill | `confirmation_mode: auto` かつ blocking なし |
| `blocked` → `awaiting_review` | planning Skill(再実行) | 原因解消後に全 validation を再実行して blocking なし、`confirmation_mode: review` |
| `blocked` → `approved` (`method: auto`) | planning Skill(再実行) | 同上、`confirmation_mode: auto` |
| `awaiting_review` → `approved` (`method: user`) | 親エージェント | ユーザーの承認操作。blocking violation が残る場合は承認操作があっても遷移しない |
| `delegation.authorized: false → true`(必要なら `requested_mode` も設定) | 親エージェント | ユーザーの明示的な委譲要求。mode の明示は委譲要求を兼ねる。どの status でも記録できるが、委譲開始には `status: approved` が別途必要 |

承認と委譲開始は独立している。`awaiting_review` から承認された場合も、委譲要求がなければ
計画の確定だけで停止する。確認モードの既定値は `review` とし、`auto` はユーザーが明示した
場合のみ使う。

## implementation_stages の実行規約

`implementation_stages` は Domain / Repository / Endpoint のような実装上の中間段階であり、
`strict` の Test plan / Red / Green / Refactor とは別の軸である。両者の関係を次のとおり定める。

- stages を宣言した枝は `strict` の段階ゲート機構で実行する。`delegation.requested_mode` が
  `strict` でない場合(mode 未指定の `null` を含む)、Executor は現行の mode 引き上げ契約に従い、
  具体的なリスクを報告して `strict` へ引き上げる。引き上げが受け入れられない場合は stages を
  実行せず、枝の再分割または stages の削除を要求する。
- 各 stage を `strict` の1サイクル(テスト計画 → Red → Green → Refactor)として実行する。
  stage の Red は `stage_tests` のテストだけを対象とし、後続 stage のテストを先に書かない。
  このため「後続 stage のテストが red のまま進む」状態は発生しない。
- stage の Green / Refactor gate の条件は「基準 commit 時点の既存テスト、完了済み stage の
  `stage_tests`、現在 stage の `stage_tests` がすべて green」とする。stage 境界では、現在までに
  追加したすべてのテストが green であることを親が確認する。最終 stage 完了後は、枝の全必須テストを
  改めて実行し、外部向け AC の受け入れ判断を枝単位で行う。
- commit は `strict` の段階別 commit 規約に従い、stage ごとに Red / Green / Refactor の commit を
  作る。stage 境界(Refactor commit 後)で親が worktree の状態を確認する。
- stage ごとの返却証跡には、現在の stage だけでなく累積テストの実行結果を含める。最終返却には、
  先頭 stage の最初の commit から末尾 stage の最終 commit までの SHA range と、stage ごとの
  commit SHA・検証結果を含める。
- 追加時点で green が許される regression 系テストの扱いは、現行の Red 証跡契約に従う。

## tests / stage_tests の意味

`tests` と `stage_tests` はテスト種別だけを保持する。具体的なテスト名、実行 command、期待値は
Branch Plan では確定しない。

- 具体的なテストは、`strict` ではテスト計画の段階で、`standard` 以下では委譲 prompt の
  AC 対応表と検証 command で確定する。いずれも親が承認・確定する現行契約に従う。
- 実行規約の「`stage_tests` のテスト」は「`stage_tests` が要求する種別を満たす、親が承認した
  テスト計画のテスト」と読む。テスト計画から stage への対応は返却証跡に残す。
- 検証 command は対象 repository の設定に依存するため、planning Skill は command を推測しない。
- Executor は、枝の `tests` に列挙された種別が委譲 prompt の必須テストと検証 command で
  すべて充足されることを委譲前に確認する。

## Executor 側の再検証

`delegate-implementation` は Branch Plan の自己申告を信用せず、委譲開始前に次を再検証する。

1. `status: approved` であり、`approval.method` が設定済みである。
2. `delegation.authorized: true` かつ `authorized_by: user` である。
3. `unresolved_decisions` が空である。
4. blocking violation code 表のすべての検査規則を入力 Data から再計算し、違反が0件である。

いずれかを満たさない場合は実装を開始せず、Branch Plan の修正(または委譲要求の有無の確認)を
要求する。

## 現行契約との整合

- 枝の単位は `shared/skill/delegate-implementation/references/implementation-branches.md` の
  「外部から観測可能な振る舞い / 単独の AC・検証・受け入れ・revert」のまま。`purpose` は
  委譲 prompt の「目的: <外部から観測可能な振る舞い>」へそのまま流し込める。
- `implementation_stages` は `strict` mode の段階ゲート機構(同一 Implementer・同一 worktree・
  段階別 commit・親の境界確認)を stage 単位に適用したものであり、新しい委譲機構を追加しない。
  stage commit は枝の worktree に留まり、統合は枝の受け入れ時に1回だけ行うため、中間統合による
  原子性の問題は発生しない。
- `shared_foundation` は `delegate-implementation` SKILL.md の「親が委譲前に行える明示的な例外」の
  構造化であり、契約文面の変更を伴わない。
- stages 宣言枝の `strict` への引き上げと、high risk 時の `delegation_mode_proposal` は、いずれも
  「mode を引き上げた場合はリスクをユーザーへ報告する」「ユーザーが明示した mode を親都合で
  引き下げない」という現行契約の枠内で動く。引き下げ(`lite`)は表現できない構造にしている。
