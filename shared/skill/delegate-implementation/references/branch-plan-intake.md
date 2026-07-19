# Branch Plan の受け入れ

## 目次

- 受け入れ口の規定
- Executor 側の再検証
- implementation_stages の実行規約

`plan-implementation-branches` が出力した確定済み Branch Plan を
`delegate-implementation` の入力として受け入れるための規約を定める。親は
Branch Plan の自己申告を信用せず、再検証してから枝と mode の入力にする。
Branch Plan の正規スキーマ(状態・violation code・状態遷移)の正本は
[Branch Plan 正規スキーマ](../../plan-implementation-branches/references/branch-plan-schema.md)
であり、本 reference は実行規約と Executor 側の再検証の正本を担う。

## 受け入れ口の規定

確定済み Branch Plan が渡された場合、親は次の手順で受け入れる。

- 自己申告を信用せず、本 reference「Executor 側の再検証」の4項目を委譲開始前に
  確認する。blocking violation code 表は planning Skill と同じ規則を入力 Data から
  再計算する。code 表の正本は
  [Branch Plan 正規スキーマ](../../plan-implementation-branches/references/branch-plan-schema.md)
  の「blocking violation code」とする。
- 再検証を満たさない場合は実装を開始せず、Branch Plan の修正(または委譲要求の
  有無の確認)を要求する。
- Branch Plan の各枝は、既存の委譲 prompt の Data へそのまま流し込む。目的は
  `purpose`、Acceptance Criteria は `covers_acceptance_criteria` の原文と
  `branch_criteria`、対象範囲は `allowed_paths`、変更禁止範囲は `forbidden_paths`、
  必須テストは `tests` に対応させる。責務制約は `out_of_scope` の各項目を意味を変えず
  委譲 prompt の「この枝でやらないこと」へ渡す。委譲 prompt の構成は
  [実装枝の準備と委譲](implementation-branches.md) に従う。
- 枝の `tests` に列挙された種別が、委譲 prompt の必須テストと検証 command で
  すべて充足されることを委譲前に確認する。テスト種別の意味は正規スキーマの
  「tests / stage_tests の意味」に従う。
- `purpose`、`branch_criteria`、`tests` から、各追加 test が新機能または未実装仕様を検証するのか、
  既存挙動を固定する regression test なのかを委譲前に確認する。後者だけが Red 証跡の Green 例外を
  利用できる。分類できない場合は Green 例外を適用せず判断点として返す。regression と確認できた場合は、
  [実装枝の準備と委譲](implementation-branches.md) の4項目の根拠を返却条件へ追加する。
- `implementation_stages` を宣言した枝は `strict` の段階ゲート機構で実行する。
  `delegation.requested_mode` が `strict` でない場合の引き上げは、SKILL.md
  「workflow mode の選択」の mode 引き上げ契約に従う。
- Branch Plan が渡されていない場合は、現行どおり親が inline に枝を分ける。分割
  シグナルに該当する場合は `plan-implementation-branches` の使用を推奨する
  (強制しない)。

## Executor 側の再検証

`delegate-implementation` は Branch Plan の自己申告を信用せず、委譲開始前に次を再検証する。

1. `status: approved` であり、`approval.method` が設定済みである。
2. `delegation.authorized: true` かつ `authorized_by: user` である。
3. `unresolved_decisions` が空である。
4. blocking violation code 表のすべての検査規則を入力 Data から再計算し、違反が0件である。

いずれかを満たさない場合は実装を開始せず、Branch Plan の修正(または委譲要求の有無の確認)を
要求する。

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
- 既存挙動を固定する regression test は、追加時点で Green でも段階順序を省略せず、Red gate で Green
  結果と根拠を親が確認する。新機能または未実装仕様の `stage_tests` は Red 必須のままとする。
