<!-- Generated from shared/. Do not edit directly. -->

# QA・修正・統合

## 目次

- 返却と統合
- 親の QA
- 専門 reviewer
- 修正先の選択
- 未統合で終了する場合
- 責務境界
- 統合済み diff review
- 後始末と最終報告

## 返却と統合

ここでは Green / Refactor まで完了した枝の最終返却を扱う。`strict` のテスト計画、Red、Green の
中間ゲートは [実装枝の準備と委譲](implementation-branches.md) に従い、未完成の枝を統合しない。
直列受け入れは、commit 単位で返し、親が diff を読んでから1枝ずつ取り込む。

1. Implementer は worktree path、branch、基準 commit、返却 commit SHA range、変更ファイル、
   実行した command と結果、未コミット変更を返す。
2. 親は `git -C <worktree> status --short` と `git -C <worktree> diff <base>...HEAD` を確認する。
   併せて親の checkout を `git -C <親 checkout> status --short` で確認し、worker の変更が worktree の外へ
   混入していないことを確かめる。
3. 報告だけで受け入れず、対象 test と実装 diff を開く。
4. QA hard reject は同じ枝へ `SendMessage` で差し戻し、修正 commit を追加させる。
5. 専門 reviewer には task、AC、commit 範囲、変更ファイル、diff text、対象 risk を渡す。
   周辺コンテキストの追加は「reviewer へ渡すコンテキスト」の選択基準に従う。
   新規 `Agent` は別 worktree で始まり枝の変更を見ないため、作業 tree の存在を前提にさせない。
6. 受け入れ後は統合 branch で `git cherry-pick <sha>` または commit range を取り込み、focused test と
   関連する build、typecheck、lint を再実行する。
7. 統合後の green commit を次の枝の基準にする。枝 worktree の green と統合後の green の片方を省略しない。

## 親の QA

`standard` と `strict` では全観点を手を動かして確認する。`lite` では観点0（diff を読む）と観点5
（自分で green を確認）に絞ってよい。`lite` の前提が崩れた場合は mode を引き上げる。

0. **実装 diff** — scope 逸脱、既存設計からの逸脱、公開契約の破壊、既存 test の弱体化、未承認依存、
   error handling、resource 解放、concurrency、security を確認する。
1. **振る舞い** — test が private API や実装手順ではなく、外部から観測可能な振る舞いを検証しているか。
2. **網羅性** — AC、境界値、異常系、例外経路、分岐、期待値の根拠が実際の test と一致するか。
3. **TDD** — 新機能または未実装仕様なら Red 出力または段階 commit を確認し、test を実装へ合わせて
   弱めていないか。既存挙動を固定する regression test が追加時点で Green なら、親は AC、test、期待値の
   根拠、既存挙動の対応を実際の test と実装から確認し、既存実装がすでに仕様を満たすという返却根拠が
   妥当か判断する。形式的な Red のための本番 code 変更がなく、mutation を使った場合は親が明示した
   一時検証だけであること、mutation が commit されておらず、変更禁止範囲や本番 code に接触していない
   ことも確認する。
4. **記述原則** — Code=How、test=What、commit=Why、comment=Why Not の配置になっているか。
5. **親の実行** — focused test と関連する全体検証を親が実行し、green を確認する。

## 専門 reviewer

専門 reviewer は特定の risk を深く確認する役割であり、専門 reviewer を汎用コードレビューの代替にしない。
専門 reviewer は mode 名だけを理由に一律起動しない。原則として次の場合だけ使用する。

- ユーザーが専門 reviewer を明示的に要求した場合。
- 親が reviewer の責務と一致する具体的なリスクを特定した場合。

| Reviewer | 対象リスク |
| --- | --- |
| `responsibility-boundary-reviewer` | 責務混在、設計境界、分散した副作用 |
| `test-quality-reviewer` | 弱いテスト、欠けているケース、実装詳細に依存したテスト |
| `security-side-effect-reviewer` | 外部 I/O、破壊的操作、機密データ、セキュリティ影響 |

対象リスクがない専門 reviewer を無条件で起動しない。起動する場合は対象リスクと review 範囲を明示する。
reviewer は最終的な受け入れ判断を行わない。親が diff、テスト、検証結果を確認し、最終的な受け入れを判断する。

### reviewer へ渡すコンテキスト

親は、レビュー対象とリスクに応じて、必要な周辺コンテキストを選択して reviewer へ渡す。
各 reviewer には原則として次の基本情報を渡す。

- タスクの目的と Acceptance Criteria
- 変更対象と commit 範囲
- 変更ファイル一覧と diff text
- reviewer に確認させる具体的な観点

diff だけでは関連する既存設計や利用箇所を判断できない場合は、次を必要に応じて追加する。

- 関連する interface、type、schema
- 主要な呼び出し元
- 関連する既存テスト
- 周辺の directory 構造
- generated file とその生成元
- 変更対象に関係する既存実装
- 外部指示と、`AGENTS.md`、`CLAUDE.md`、`README.md` の関連部分

コンテキストの選択では次を守る。

- repository 全体を無条件に渡さない。
- reviewer の役割に関係しない情報を過剰に渡さない。
- 親の結論だけを渡さず、reviewer が独立して判断できる一次情報を渡す。
- 周辺コードを渡す場合は、なぜ必要なのかを明示する。
- 外部指示と repository 内の指示が競合する場合は、優先関係を明示する。

## 記述原則の必須完了ゲート

`writing-principles-reviewer` は必須の完了ゲートであり、上記の任意起動条件の対象外とする。
`writing-principles-reviewer` は `lite` / `standard` / `strict` のすべてで、各実装枝を受け入れる前に必ず起動する。

親が取得する `git diff`、`git status`、commit log、テスト結果を、Data として `writing-principles-reviewer` へ渡す。
対象は基準 commit からの diff が導入または悪化させた問題に限定し、既存問題を広く探索しない。
これらの情報を取得するために reviewer 自身へ Bash や編集 tool を与えない。

reviewer は、指摘がある場合は指摘IDを含む構造化 Data を返す。
`no-change` は reviewer の指摘が0件である正常なゲート通過結果として扱う。
指摘がある場合、親は各指摘IDについて内容を確認し、修正先または不採用を判断して、その判断を記録する。

- 局所的で振る舞いを変えない修正は `review-patch-refactorer` へ渡す。
- テストケース追加、期待値の再検討、仕様判断、設計変更、振る舞い判断が必要な修正は元 Implementer へ差し戻す。
- 指摘を採用しない場合は、親が指摘IDと不採用理由を記録する。

`review-patch-refactorer` による修正後の親QAと reviewer 再確認は、元 Implementer による修正にも適用する。
`review-patch-refactorer` または元 Implementer による修正後は、親が変更後の diff とテスト結果を確認し、
`writing-principles-reviewer` を再実行する。

指摘がある場合は、次のいずれかになるまで枝を受け入れない。

- すべての指摘が修正され、再確認を通過している。
- 親が不採用とした指摘について、理由が記録されている。

未解決または判断未記録の指摘がある枝を受け入れない。

## 修正先の選択

次の条件をすべて満たす場合に限り `review-patch-refactorer` を起動する。

- 専門 reviewer（必須の `writing-principles-reviewer` を含む）の具体的な指摘が存在する。
- 親が指摘を確認し、修正対象として採用している。
- Acceptance Criteria は満たされている。
- Acceptance Criteria を変更する必要がない。
- 機能的なテストは green である。
- 修正範囲が局所的である。
- 仕様の再解釈を必要としない。
- 新機能追加ではない。
- 振る舞いを維持したまま修正できる。
- reviewer が修正方針または問題箇所を明示している。

起動 prompt には少なくとも次の Data を含める。

- 指摘元 reviewer、対象となる指摘ID、指摘本文
- 親が採用した修正条件
- 対象 worktree、branch、基準 commit、対象 commit 範囲
- Acceptance Criteria
- 変更を許可するファイルと変更を禁止するファイル
- 削除・移動・新規作成の可否と commit の要否
- 必須検証 command

入力が不足する場合、`review-patch-refactorer` は推測で補わず、ファイルを変更せず親へ返す。

`review-patch-refactorer` は指摘範囲だけを修正し、新しい問題を探索しない。仕様変更、ついで修正、
大規模再設計、新規依存追加、通常実装の代行をさせない。親が個別に許可しない限り、ファイルの
新規作成・削除・移動、指摘外のテストケース追加、fixture や helper の追加をさせない。

返却後、親は自己申告だけを信用せず、次を再確認する。

- `git -C <worktree> status --short`
- 基準 commit からの変更ファイル一覧と diff
- 許可範囲外の変更がないこと
- ファイルの追加・削除・移動がないこと
- reviewer 指摘外の変更がないこと
- テストケース、期待値、skip 設定の変更がないこと
- Acceptance Criteria と外部から観測可能な振る舞いが維持されていること
- focused test と関連する全体検証が green であること

次は元 Implementer へ差し戻す。

- Acceptance Criteria 未達
- 仕様誤解
- 機能欠落
- テスト失敗
- 正常系・異常系・境界値不足
- security や副作用の修正に振る舞い変更が必要
- test 品質の修正にケース追加や期待値の再検討が必要
- `strict` mode の Red / Green / Refactor 継続
- 元の調査・実装判断が必要

親がその場で直してよいのは、返却後の import 整理と formatter 適用だけとする。共有土台の作成は
委譲前の明示的な例外であり、返却後の仕様判断、case 追加、命名、comment、test 名、設計修正を親が
引き取る理由にはしない。

## 未統合で終了する場合

通常の `Needs revision` は上の修正先へ差し戻し、top-level workflow を継続する。
親が未統合の枝について `Rejected` / `Needs revision` を最終判断とし、
top-level workflow を終了する場合だけ、実行可能な検証を行い、未実行の検証、未統合の理由、
worktree を保持する理由を Data として記録し、
main の手順9へ戻る。

## 責務境界

返却物 QA を通過した diff は、最終検証前に親が次を軽量確認する。

- 1つの function、class、module に複数の変更理由が混ざっていないか。
- input validation、業務判断、永続化、外部 I/O、表示整形が同じ場所に詰め込まれていないか。
- DB、API、HTTP、file、framework の具体実装を上位層が知りすぎていないか。
- 副作用が分散し、再実行、test、失敗時の扱いが難しくなっていないか。
- boolean flag や mode 引数で大きく責務を切り替えていないか。
- 既存の責務配置、命名、directory 構成から不自然に外れていないか。
- 分割や抽象化が過剰になっていないか。

複数層、複数の外部 I/O、新しい abstraction・adapter・service、責務混在の疑いがある場合は
`responsibility-boundary-reviewer` を起動する。

- `問題なし`: 通過。
- `軽微` / `修正推奨`: 局所的で全起動条件を満たす場合だけ `review-patch-refactorer`、それ以外は元 Implementer。
- `修正必須`: 解消するまで完了しない。振る舞い変更や AC 再解釈が必要なら元 Implementer。

`responsibility-boundary-reviewer` は修正しない。新規 Agent として diff text を渡し、
全体判定と、指摘ごとの問題箇所、種類、理由、影響範囲、最小修正方針を返させる。
diff にない既存問題は「既存課題」として判定から分ける。

## 統合済み diff review

全枝の統合と検証後、後始末より前に統合済み diff を review する。

親が統合済み diff、test、残存 risk を読み、最終受け入れ判断を記録する。

## 後始末

後始末は、受け入れ判断、最終検証、必要な統合済み diff review を含む最終ゲートをすべて通過した後にだけ行う。
差し戻しまたは再検証の可能性がある間は始めない。

親がこのタスク用に作成した、統合済みで未コミット変更のない worktree を `git worktree remove <worktree path>`
で削除する。削除できない worktree は理由と残った path を最終報告に含める。

## 最終報告

- 変更内容
- Implementer が検証したこと
- 統合後に親が検証したこと
- 統合済み diff review で確認したこと
- 未検証の残り
