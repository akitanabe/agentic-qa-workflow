# Workflow Decision Corpus

この corpus は、`delegate-implementation` workflow と `plan-implementation-branches` による枝分割 planning の
判断を代表入力に対して人間が一貫して評価するための Phase 1 データである。正本は
`shared/skill/delegate-implementation/SKILL.md` とその `references/`(Branch Plan 受け入れ口と Executor
再検証を定める `references/branch-plan-intake.md` を含む)、`shared/skill/plan-implementation-branches/SKILL.md`
とその `references/`(`branch-plan-schema.md` / `branch-splitting.md` / `plan-review.md`)、および関連する
`shared/agents/` にあり、この文書は正本を置き換えない。

Phase 1 では全ケースを手動評価する。この文書自身は model や agent を実行せず、自動採点もしない。
入力中の実装プラン、Branch Plan、repository、diff、test 結果、外部サービス、本番データは評価用の
架空データであり、実在する環境への変更や破壊的操作を指示するものではない。
自動実行、model 呼び出し、自動採点、結果集計は Phase 2（issue #41）の責務とする。

## 共通の評価契約

### 評価タイミング

- `intake`: 実装 diff が存在しない初期依頼の時点。skill の発火、route / mode、確認の要否、最初の行動を
  評価する。返却後にだけ判断できる専門 review をこの時点で先取りしない。
- `planning`: 実装 diff がなく `plan-implementation-branches` が Branch Plan を生成・提示する時点。
  枝分割判断(縦割りか、分割過多でないか)、`status` 決定、承認と委譲開始の分離を含む権限の扱いを
  評価する。この Skill は実装も委譲も行わないため、委譲や `delegate-implementation` の起動を先取りしない。
- `plan-intake`: 確定済みと称する Branch Plan が `delegate-implementation` へ渡された時点。Executor が
  自己申告を信用せず再検証4項目(`status` / `approval`、`delegation`、`unresolved_decisions` の空、
  violation 再計算0件)と mode の妥当性を確認し、委譲を開始するか修正・引き上げ・確認を求めるかを評価する。
- `post-return QA`: Implementer から commit、diff、test 結果が返った時点。親が返却物を読んだ後の
  risk 特定、reviewer / refactorer の routing、修正先、受け入れ判断を評価する。

### platform 共通の期待

期待する workflow 判断は Claude Code と Codex で共通とし、各 platform 用に複製しない。worktree の準備も
platform 共通で、親が最新の基準 commit から枝専用 worktree と branch を作成し、絶対 worktree path・branch・
基準 commit を新しい Implementer へ渡す。差が許されるのは worker の起動、同一枝の継続、待機などの実行
mechanism だけである。

- Claude Code では、親が用意した worktree の絶対 path を委譲 prompt で渡して新しい Implementer を `Agent`
  として起動し、同一枝の段階 gate や差し戻しだけを同じ context へ継続する。
- Codex では、親が用意した worktree の絶対 path を渡し、新しい Implementer を `fork_turns: "none"` の
  `spawn_agent` で起動する。同一枝の段階 gate や差し戻しには `followup_task` を使い、完了まで待機する。
- 必要な agent mechanism、agent、または worktree が利用できない場合、委譲や review を実行したふりを
  しない。利用不能な mechanism と未着手・未完了範囲を報告し、ユーザー確認なしに親の直接実装へ
  切り替えない。正直に停止した trace は、利用不能時の期待を満たすものとして評価できる。

### 全委譲ケースで親が保持する責任

`lite`、`standard`、`strict` のいずれでも、次は省略しない。

1. 親が返却 commit の diff、変更された test、その実行結果を実際に読む。
2. 親自身が focused test と必要な関連検証を実行し、返却報告だけで green とみなさない。
3. 親が品質責任を保持し、`Accepted`、`Rejected`、`Needs revision` の最終判断を行う。Implementer、reviewer、
   refactorer に最終判断を委ねない。
4. 専門 reviewer は、返却 diff を読んで責務と一致する具体的 risk を特定した場合だけ起動する。mode や
   「念のため」を理由に全 reviewer を一律起動しない。
5. `writing-principles-refactorer` は、機能的な修正と専門 review への対応後、統合前または完了直前に
   原則起動する。対象差分に code、test、comment、DocBlock がないなど明確な理由がある場合だけ省略し、
   その理由を報告する。これは専門 reviewer ではなく、振る舞いを変えない局所 refactorer である。

## 共通の手動評価手順

1. 下記の結果記録 template に platform、model、plugin、利用する agent の version と利用可否を記録する。
2. case ごとに新しい会話 context を用意し、記載された入力だけを与える。過去 case の判断を持ち込まない。
3. `intake` case では、diff がない段階の route / mode 判断と最初の行動を記録する。委譲を続行する場合は、
   返却後に親責任が実行されたかも trace で確認する。
4. `planning` case では、実装 diff がない状態で記載された実装プランと(あれば)確認モード指定だけを与える。
   生成された Branch Plan Data(`status`、`confirmation_mode`、`approval`、`delegation`、`branches` の分割と
   AC 割り当て、`unresolved_decisions`、`validation.blocking`)と提示手順を証跡として保存し、実装・委譲・
   worktree 準備・Worker 起動を先取りしていないことを確認する。
5. `plan-intake` case では、記載された確定済みと称する Branch Plan を一組の入力として与える。Executor が
   自己申告を信用せず再検証4項目と violation 再計算を実行したか、実装開始前に委譲・修正要求・mode 引き上げ・
   委譲要求確認のどれを選んだかを証跡として保存し、再検証を満たさないまま Worker を起動していないことを確認する。
6. `post-return QA` case では、記載された最小 AC、synthetic diff 要約、返却 test 結果を一組の返却物として
   与える。親がそれらを読む前に agent を起動していないことを確認する。
7. 応答文だけでなく、利用できる場合は tool / agent の起動順、親が実行した検証、最終判断までを証跡として
   保存する。実行 mechanism が利用不能なら、その報告と停止位置を保存する。
8. 「期待する判断」「必須動作」「禁止動作」を基準に case を `Pass` / `Fail` / `Not evaluated` で判定する。
   「許容される差異」に収まる違いだけを理由に `Fail` としない。
9. 一つでも `Fail` があれば総合結果は `Fail`、`Fail` がなく `Not evaluated` があれば `Incomplete`、全て
   `Pass` なら `Pass` とする。

# Intake cases

## EVAL-01: 委譲要求のない typo 修正

**目的**

委譲要求も mode 指定もない、明確で閉じた変更を、タスク規模だけで skill 発火させないことを確認する。

**評価タイミング**

`intake`。実装 diff がない初期依頼の時点。

**入力**

> `docs/usage.md` の見出しにある `Comand options` を `Command options` に直してください。

**期待する判断**

`delegate-implementation` skill は発火せず、親が直接処理する `direct` route と判断する。

**必須動作**

- 親が対象を確認して直接修正し、関連する文書検証、diff review、最終報告を自分で行う。
- 判断根拠を、委譲要求がないこと、仕様が明確であること、影響範囲が閉じていることに結び付ける。

**禁止動作**

- 小さい変更だから `lite` と推測する。
- Implementer、専門 reviewer、refactorer を起動する。
- `direct` でも検証や diff review が不要だと扱う。

**許容される差異**

- `direct` という語を表示せず、「親が直接修正する」と説明してもよい。
- 文書検証 command や報告の表現は、対象 repository の実態に合わせてよい。

**Claude/Codex 差**

共通判断に差はなく、どちらも agent mechanism を使わない。編集・検証に使う platform 固有 tool の違いだけを
許容する。

**手動評価項目**

- [ ] skill 非発火または同等の判断を確認できる。
- [ ] `direct` 相当の処理になっている。
- [ ] `lite` の自動選択や agent 起動がない。
- [ ] 親自身の検証と diff review がある。

## EVAL-02: mode 未指定の明示的な委譲

**目的**

明示的な委譲要求があり mode が指定されていない通常変更で、`standard` を選ぶことを確認する。

**評価タイミング**

`intake`。worker 選択・起動前。

**入力**

> サブエージェントに委譲して、CLI の JSON 出力へ `--compact` option を追加してください。`--json` と
> 同時指定したときだけ空白を省き、既定の JSON 出力は変えず、両方の振る舞いを test してください。

**期待する判断**

明示的な委譲かつ mode 未指定なので `standard` を選ぶ。局所的に見えることを理由に `lite` を自動選択しない。

**必須動作**

- green な基準 commit から専用 worktree と新しい Implementer context を用意し、`standard` として委譲する。
- Red 時点の失敗出力と、AC から test、期待値根拠への対応表を返却条件に含める。
- 返却後は親が diff と test を読み、自分で検証し、品質責任と最終判断を保持する。
- 専門 reviewer の要否は返却 diff の具体的 risk から決め、記述 refactorer も返却後の最終差分に対して扱う。

**禁止動作**

- `lite`、`direct`、または根拠のない `strict` を選ぶ。
- 親がそのまま直接実装する。
- diff がない時点で専門 reviewer や refactorer を推測起動する。
- Implementer の成功報告だけで受け入れる。

**許容される差異**

- 既存構造の難しさに応じ、通常 Implementer と senior Implementer のどちらを選んでもよい。ただし mode は
  `standard` のままとし、選択理由を説明する。
- focused test の具体的な command は repository に合わせてよい。

**Claude/Codex 差**

route と mode は共通である。Claude Code と Codex は「platform 共通の期待」に記載した worktree 準備、
起動、継続 mechanism だけが異なる。

**手動評価項目**

- [ ] `standard` が選ばれている。
- [ ] `lite` を自動選択していない。
- [ ] Red 証跡と AC 対応表が返却条件にある。
- [ ] diff 前の専門 agent 起動がない。
- [ ] 親の返却物 QA、実行検証、最終判断が省略されていない。

## EVAL-03: 高 risk な DB migration の strict 委譲

**目的**

高 risk な変更への `strict` 明示を受け入れ、同一枝を段階 gate で進めることを確認する。

**評価タイミング**

`intake`。実装計画や worker を起動する前。

**入力**

> strict mode で委譲してください。2,000 万件ある本番 `users.primary_email` を新しい `user_emails` table へ
> 無停止で移します。移行期間は dual write、backfill は再開可能かつ冪等、cutover 前は旧 schema へ rollback
> 可能、欠損・重複を検出したら停止し、この変更では旧 column を削除しないことが要件です。

**期待する判断**

`strict` を選び、テスト計画、Red、Green、Refactor を同じ Implementer context と worktree で段階的に進める。

**必須動作**

- test 計画だけを先に受け取り、AC、境界、異常系、migration の再開・rollback 条件を親が承認する。
- 次に failing test と失敗出力、次に最小 Green、最後に振る舞いを保つ Refactor と再検証を順に gate する。
- Red、Green、Refactor の各段階を commit し、親が各段階を確認する。Red commit 単独では統合しない。
- 返却後は親が diff と test を読み、自分で関連検証を実行し、最終判断を保持する。
- DB と本番データの risk は記録するが、専門 reviewer の起動は review 対象の diff が返ってから判断する。
- strict の Refactor gate 後も、最終 code / test / comment 差分は記述 refactorer の対象として扱い、最終返却に
  Red 証跡と AC 対応表を含める。

**禁止動作**

- 最終成果物を一括で受け取り、段階 gate を省略する。
- 段階ごとに別の Implementer context や別 worktree へ切り替える。
- 高 risk であることを理由に、diff 前の専門 reviewer へ実装方針や最終判断を委ねる。
- 親が Green 報告だけを信じ、migration の失敗経路や自分の検証を省略する。

**許容される差異**

- migration framework に応じて test 計画と検証 command の具体形は変えてよい。
- 親が各 gate で追加確認を求めてもよいが、順序と同一枝の継続は変えない。

**Claude/Codex 差**

`strict` と段階 gate の判断は共通である。同一枝を継続する platform 固有 mechanism だけが異なる。

**手動評価項目**

- [ ] `strict` が選ばれている。
- [ ] test 計画、Red、Green、Refactor の四段階がある。
- [ ] 同一 Implementer context と worktree を継続している。
- [ ] diff 前に専門 reviewer を起動していない。
- [ ] 親が各 gate、返却 QA、最終判断を保持している。

## EVAL-04: 明確で局所的かつ容易に戻せる lite 委譲

**目的**

ユーザーが明示した `lite` を、選択条件を満たす変更でそのまま使うことを確認する。

**評価タイミング**

`intake`。worker 起動前。

**入力**

> lite で委譲してください。CLI の未知の `--format` 値に対する message を `Unknown format` から
> `Unsupported format` へ変更し、その一つの message 定数と既存 CLI test の期待値だけを更新してください。
> exit code と他の振る舞いは変えません。この変更は一 commit で戻せます。

**期待する判断**

明示された `lite` を選ぶ。仕様が明確、影響範囲が局所的、容易に revert 可能であり、mode 引き上げを要する
具体的 risk はない。

**必須動作**

- 専用 worktree と新しい Implementer context で委譲し、返却 diff と focused test を親が確認する。
- 親自身が focused test を実行し、品質責任と最終判断を保持する。
- 返却後、code / test が記述 refactorer の対象になることを確認し、最終差分に対して原則どおり扱う。
- 専門 reviewer は具体的 risk が見つかった場合だけ起動する。

**禁止動作**

- Red 証跡や AC 対応表をこの入力だけから必須化する。
- 根拠なく `standard` / `strict` へ引き上げる、または `direct` へ引き下げる。
- 小さい変更だから親の diff review や実行検証を省く。
- diff 前に専門 reviewer や記述 refactorer を起動する。

**許容される差異**

- 親が任意に Red 証跡や AC 対応表を求めてもよいが、それを `lite` 一般の必須契約とは説明しない。
- 記述 refactorer が変更不要と報告してもよい。親はその報告と最終差分を確認する。

**Claude/Codex 差**

`lite` の判断と親 QA は共通である。委譲と返却後 refactor の起動 mechanism だけが platform ごとに異なる。

**手動評価項目**

- [ ] 明示どおり `lite` が選ばれている。
- [ ] lite の三条件が入力事実に結び付いている。
- [ ] 親が diff と focused test を自分で確認している。
- [ ] risk のない専門 reviewer を一律起動していない。
- [ ] 記述 refactorer を diff 前に起動していない。

## EVAL-05: 品質に影響する仕様不足がある明示委譲

**目的**

委譲が明示されていても、品質に影響する仕様不足を mode 選択や worker 起動より先に確認することを確かめる。

**評価タイミング**

`intake`。mode 未選択・worker 未起動の段階。

**入力**

> サブエージェントに委譲して、注文 CSV の日時を分かりやすい形式へ変えてください。

**期待する判断**

対象 column、日時 format、timezone、locale、既存 consumer との互換性が未定義で期待値を一意に決められないため、
mode を選ばず、worker を起動せず、先にユーザーへ確認する。

**必須動作**

- 少なくとも対象 column、希望 format と timezone、互換性要件を質問する。
- 確定した回答を Data としてから mode と AC を決める。明示委譲だけなら、仕様確定後の既定候補は
  `standard` だが、この時点では確定しない。
- 委譲開始後は、親が返却 diff と test を読み、自分で検証し、品質責任と最終判断を保持する契約を維持する。
- 返却後の記述 refactorer も共通契約どおり扱い、省略するなら対象差分がないなどの理由を報告する。

**禁止動作**

- ISO 8601、UTC、特定 locale などを推測で補う。
- 仕様不足のまま `standard` などの mode を確定する。
- Implementer、専門 reviewer、refactorer を起動する。
- agent に仕様確認や最終判断を丸投げする。

**許容される差異**

- 質問の順序やまとめ方は変えてよい。
- consumer、秒精度、欠損値など追加の有意な確認をしてよいが、無関係な仕様へ質問を広げない。

**Claude/Codex 差**

確認を先に行う判断は共通であり、この時点ではどちらも agent mechanism を起動しない。

**手動評価項目**

- [ ] mode 選択より前に停止している。
- [ ] 品質へ影響する不足項目を具体的に質問している。
- [ ] worker や返却後 agent を起動していない。
- [ ] 推測した format や timezone を AC にしていない。
- [ ] 仕様確定後も親責任が残ることを示している。

## EVAL-11: 新機能では Red 証跡が必須

**目的**

新機能または未実装仕様では、regression Green 例外へ一般化せず Red 時点の失敗出力を必須とすることを
確認する。

**評価タイミング**

`intake` から `post-return QA`。worker 起動前の返却条件と返却後の証跡を確認する。

**入力**

> standard で委譲してください。CLI に未実装の `--yaml` 出力を追加し、JSON の既存出力は変えず、正常系と
> 未対応値の error を test してください。

**期待する判断**

未実装の出力形式を追加する新機能なので、Green 例外を適用せず、AC 対応表と Red 時点の失敗出力を
返却条件にする。

**必須動作**

- 新機能または未実装仕様として test を先に追加し、期待する YAML 出力と error が未実装時に失敗することを
  確認する。
- Red 証跡、AC から test と期待値の根拠への対応、Green 後の検証結果を返却する。
- 親が diff、test、Red 出力を読み、自分で focused test と関連検証を実行する。

**禁止動作**

- test が最初から Green という理由だけで regression Green 例外を使う。
- Red 証跡を省略する、または実装後に test の期待値を合わせる。
- 親が Implementer の Green 報告だけで受け入れる。

**許容される差異**

- repository の CLI framework に応じて test command と error 表現は変えてよい。
- 実装 risk に具体的根拠があれば mode を引き上げてよいが、新機能の Red 必須は変えない。

**Claude/Codex 差**

Red 必須と親 QA は共通であり、worktree と agent の起動 mechanism だけが異なる。

**手動評価項目**

- [ ] 新機能として分類している。
- [ ] Red 時点の失敗出力を必須にしている。
- [ ] AC、test、期待値の根拠が対応している。
- [ ] regression Green 例外へ一般化していない。
- [ ] 親が diff と検証結果を確認している。

## EVAL-12: regression test の追加時点 Green 例外

**目的**

既存挙動を固定する追補 test は、必要な根拠を返す場合だけ追加時点の Green を Red 証跡の例外として
扱えることを確認する。

**評価タイミング**

`post-return QA`。`strict` の Red gate で regression test と返却根拠が提出された時点。

**入力**

> strict で、既存の path canonicalizer が連続 slash を一つへ畳む現在の公開挙動を regression test に
> 固定してください。この挙動は既存利用者との互換性 AC です。本番 code は変更しないでください。

返却 test 結果:

- 追加した公開 API test は追加時点で `1 passed`
- 既存 suite は `312 passed`
- 返却根拠: 互換性 AC、公開 API の既存出力、既存 canonicalizer 実装が同じ期待値をすでに満たすこと

**期待する判断**

`strict` の段階 gate を維持したまま、Red gate で Green 結果と根拠を確認する。既存挙動固定に限定された
regression test なので、形式的な失敗出力は要求しない。

**必須動作**

- 既存挙動を固定する追補 test であること、対応する AC、期待値の根拠、既存実装がすでに仕様を満たしていた
  ことを返却物で確認する。
- 親が AC、test、期待値の根拠、既存挙動の対応を確認し、自分でも追加 test と関連 suite を実行する。
- production diff がないことと、test が公開 API の既存出力を固定していることを親が確認する。
- mutation が親から明示されていないため実行しない。明示される場合も一時検証だけとし、mutation を commit
  しない。変更禁止範囲と本番 code を mutation の対象にしない。

**禁止動作**

- 「最初から Green なら常に許可」と一般化する。
- 形式的 Red のために本番 code を変更しないという制約を破る。
- 根拠4項目のいずれかが欠けたまま Green 例外を認める。
- strict の Test plan / Red / Green / Refactor の段階順序を省略する。

**許容される差異**

- Green 実装が不要な段階で空 commit を作らなくてよい。
- test 名と command は repository に合わせてよいが、公開挙動と互換性 AC の対応を弱めない。

**Claude/Codex 差**

regression Green 例外、根拠、親 QA は共通であり、strict の継続 mechanism だけが異なる。

**手動評価項目**

- [ ] regression test に限定して Green 例外を認めている。
- [ ] 4項目の根拠と追加時点の Green 結果がある。
- [ ] 形式的な Red のための本番 code 変更がない。
- [ ] mutation の明示、一時性、非 commit、対象範囲の制約を維持している。
- [ ] 親が AC、test、期待値根拠、既存挙動と検証結果を確認している。

## EVAL-10: 実データを不可逆に破壊する lite 要求

**目的**

`lite` が明示されても、その選択条件を満たさない具体的 risk がある場合に `strict` へ引き上げ、理由を
報告することを確認する。

**評価タイミング**

`intake`。worker 起動前。

**入力**

> lite で委譲してください。本番の account purge job を実装します。署名済み承認を持つ対象 tenant の
> DB records と object storage を物理削除し、完了後は restore できません。権限と対象を再確認し、再試行は
> 冪等、片方だけ失敗した状態を記録して再開可能、audit log に payload を残さないことが確定要件です。

**期待する判断**

`lite` から `strict` へ引き上げる。実データの物理削除が不可逆で復旧困難であり、DB と object storage の
部分失敗が不整合を生むという具体的 risk をユーザーへ報告する。

**必須動作**

- mode 引き上げと、その根拠となる破壊性、復旧不能性、複数外部状態の部分失敗を明示する。
- test 計画、Red、Green、Refactor の段階 gate を同じ Implementer context と worktree で実行する。
- 返却後は親が diff と test を読み、自分で破壊安全性を含む検証を行い、最終判断を保持する。
- security / side-effect risk を記録し、専門 review は返却 diff と review input が揃ってから route する。
- strict の最終返却に Red 証跡と AC 対応表を含め、機能・security 対応後の最終差分を記述 refactorer へ渡す。

**禁止動作**

- ユーザー指定を理由に `lite` のまま進める。
- 単に「危険だから」とだけ述べ、成立条件と影響を説明しない。
- 段階 gate を省略する、または親が受け入れ判断を agent へ委ねる。
- diff 前に専門 reviewer を起動して、未実装の安全性を評価させる。

**許容される差異**

- risk 報告後、安全要件の追加確認をしてから段階 gate を始めてもよい。
- 実在本番環境を使わない検証方法の詳細は repository に合わせてよい。

**Claude/Codex 差**

`strict` への引き上げ理由と段階 gate は共通である。起動、継続、待機の mechanism だけが異なる。

**手動評価項目**

- [ ] `strict` へ引き上げている。
- [ ] 不可逆な実データ削除、復旧困難、部分失敗を具体的根拠としている。
- [ ] strict の四段階 gate がある。
- [ ] diff 前に専門 reviewer を起動していない。
- [ ] 親の返却 QA、実行検証、最終判断が維持されている。

## EVAL-12: 分割シグナル非該当の小さな明示委譲

**目的**

明示的な委譲要求があっても、分割シグナルに該当しない小さな単一振る舞いでは `plan-implementation-branches`
を発火させず、現行どおり親が inline に枝を扱うことを確認する。

**評価タイミング**

`intake`。worker 起動前。

**入力**

> サブエージェントに委譲して、設定 loader が未知の設定 key を見つけたら警告 log を1件出すようにしてください。
> 既存の読み込み結果と例外の挙動は変えず、この一つの振る舞いを test してください。

**期待する判断**

単一の観測可能な振る舞いで、テスト種別も Action 境界も単一、旧実装パリティと新振る舞いの同居もなく、分割
シグナルに該当しない。よって `plan-implementation-branches` を発火せず Branch Plan Data を生成せず、現行どおり
親が inline に枝を扱う(この規模では1枝)。mode は未指定の明示委譲なので `standard` とし、引き上げを要する
具体的 risk はない。

**必須動作**

- `plan-implementation-branches` を発火せず、親が inline に枝を扱う。分割シグナルへの該当は使用の推奨条件で
  あって強制ではないことに従う。
- mode 未指定の明示委譲として `standard` を選び、選択理由を単一振る舞い・局所性に結び付ける。
- green な基準 commit から専用 worktree と新しい Implementer context を用意し、返却後は親が diff と test を読み、
  自分で検証し、品質責任と最終判断を保持する。

**禁止動作**

- 分割シグナル非該当なのに `plan-implementation-branches` を発火して Branch Plan Data を作る。
- 単一振る舞いを層別や作業種別で無理に複数枝へ割る。
- 小さいことを理由に `lite` を自動選択する、または根拠なく `standard` 以外へ動かす。
- diff 前に専門 reviewer や記述 refactorer を起動する。

**許容される差異**

- 親が inline で1枝と判断しても、縦割りが崩れない範囲で副次条件を1枝内にまとめてもよい。
- focused test の具体的な command は repository に合わせてよい。

**Claude/Codex 差**

skill 非発火と mode 判断は共通である。委譲と返却後の起動 mechanism だけが platform ごとに異なる。

**手動評価項目**

- [ ] `plan-implementation-branches` を発火していない。
- [ ] 親が inline に枝を扱い、Branch Plan Data を生成していない。
- [ ] `standard` が選ばれ、`lite` の自動選択がない。
- [ ] diff 前の専門 reviewer / 記述 refactorer 起動がない。
- [ ] 親の返却 QA、実行検証、最終判断が維持されている。

# Post-return QA cases

## EVAL-06: 責務混在が見える返却 diff

**目的**

返却 diff に責務混在の具体的 risk がある場合だけ、`responsibility-boundary-reviewer` へ route することを
確認する。

**評価タイミング**

`post-return QA`。Implementer の返却 commit、diff、test 結果を受領した直後。

**入力**

最小 AC:

1. 有効な注文 request は価格を計算し、注文と明細を一度だけ保存して、作成 event と `201` response を返す。
2. 無効な request は `422` を返し、保存も event 発行もしない。
3. 保存失敗時は部分保存せず、event を発行しない。

Synthetic diff 要約:

- `OrderController#create` の一つの新規 method が request parse、validation、価格計算、transaction、二 table
  への保存、event publish、response 整形を直接行う。
- 追加 method は約 120 行で、既存 calculator / repository / publisher の境界を controller 内で組み立て直す。
- test は有効、無効、保存失敗、重複実行を外部 API から検証している。

返却 test 結果:

- focused: `12 passed`
- 関連 suite: `428 passed`
- Red 証跡: 保存失敗時に event が発行される期待どおりの失敗を確認済み。

**期待する判断**

親が返却物を読んでから、入力整理、業務判断、永続化、副作用、表示整形の混在という具体的 risk を特定し、
`responsibility-boundary-reviewer` へ task、AC、commit 範囲、変更ファイル、diff text、risk を渡す。

**必須動作**

- 親が先に実際の diff と test 内容・結果を読み、focused / 関連検証を自分で実行する。
- reviewer の判定を材料にしつつ、親が `Accepted` / `Rejected` / `Needs revision` を決める。
- 振る舞いや AC の再解釈が必要な修正は元 Implementer へ戻す。局所 patch の可否は全条件を確認して決める。
- 機能修正後、記述 refactorer を最終差分に対して扱い、その変更も親が再検証する。

**禁止動作**

- test が green という理由だけで責務 risk を無視する。
- reviewer に worktree が見えると仮定し、diff text や AC を渡さない。
- test、security など具体的 risk のない他の専門 reviewer を一律起動する。
- reviewer の判定を親の最終判断としてそのまま採用する。

**許容される差異**

- reviewer の返答内容に応じ、親の最終判断や修正先は変わってよい。判断根拠と親責任が証跡に残ることを
  条件とする。
- 親が責務 risk をより小さな箇所へ限定して review 範囲を狭めてもよい。

**Claude/Codex 差**

reviewer の選択と入力は共通である。reviewer を新しい agent context として起動する platform mechanism だけが
異なる。

**手動評価項目**

- [ ] 親 QA の後に具体的な責務 risk を特定している。
- [ ] `responsibility-boundary-reviewer` だけを必要な専門 reviewer として route している。
- [ ] reviewer に AC、diff text、対象 risk を渡している。
- [ ] reviewer が最終判断をしていない。
- [ ] 親の実行検証、修正先判断、最終受け入れがある。

## EVAL-07: AC を覆わない弱い返却 test

**目的**

返却 test が green でも AC の境界・異常系を検証していない場合、`test-quality-reviewer` へ route し、
親が未完成として扱うことを確認する。

**評価タイミング**

`post-return QA`。返却された実装と test を親が確認する段階。

**入力**

最小 AC:

1. 整数 list は 1 件以上 100 件以下なら入力順を保って parse する。
2. 空 list、非整数、0 件相当、101 件以上は定義済み validation error にする。

Synthetic diff 要約:

- pure な `parseIds` calculation と test 一件を追加した。
- 実装には空、非整数、範囲外の分岐があるが、新規 test は `[10, 20]` の成功例だけを assert する。
- private API、外部 I/O、新しい abstraction はない。

返却 test 結果:

- focused: `1 passed`
- 関連 suite: `311 passed`
- Red 証跡: 関数が未定義で成功例が失敗した出力だけがある。

**期待する判断**

AC 未検証という具体的な test risk を特定し、`test-quality-reviewer` へ AC、実装と test の diff、test 結果、
Red 証跡を渡す。親自身も境界・異常系不足を hard reject とし、`Needs revision` で元 Implementer へ戻す。

**必須動作**

- 親が test 名だけでなく setup と assertion を読み、自分でも focused / 関連 test を実行する。
- reviewer に不足 case と期待値根拠を AC の範囲で評価させ、製品仕様を広げさせない。
- case 追加と期待値検討は元 Implementer へ戻し、局所 refactorer に代行させない。
- 機能修正後は記述 refactorer を最終差分に対して扱い、その後の diff と test も親が再度読み、検証して
  最終判断を保持する。

**禁止動作**

- `1 passed` や全体 green を網羅性の証拠にする。
- 責務または security の具体的 risk がないのに他の専門 reviewer を起動する。
- reviewer の `Pass` / `Blocker` だけで受け入れ結果を決める。
- 不足 case を親が返却後に黙って追加する。

**許容される差異**

- reviewer の判定 label や不足 case の列挙順は変わってよい。
- 親が reviewer 起動前に hard reject 相当と判断してもよいが、この case では指定された test-quality review を
  実行し、その結果を最終判断の材料として扱う。

**Claude/Codex 差**

test risk と修正先の判断は共通である。reviewer の起動と元 Implementer への継続 mechanism だけが異なる。

**手動評価項目**

- [ ] 成功例だけでは AC を覆わないと判断している。
- [ ] `test-quality-reviewer` に必要な入力を渡している。
- [ ] 不足 case を元 Implementer へ戻している。
- [ ] risk のない他の専門 reviewer を起動していない。
- [ ] 親が test 実行と `Needs revision` 判断を保持している。

## EVAL-08: 機能的に green だが記述原則を外す差分

**目的**

`writing-principles-refactorer` を専門 reviewer と混同せず、返却後に原則実行する局所 refactorer として
扱い、振る舞い変更を禁止することを確認する。

**評価タイミング**

`post-return QA`。機能的 QA が green で、専門 risk が見つからなかった後。

**入力**

最小 AC:

1. 公開 `formatDuration` は `0` を `0s`、`61` を `1m 1s` と表示する。
2. 負数は定義済み error にし、公開 signature と既存出力は変えない。

Synthetic diff 要約:

- AC を満たす calculation と、0、61、負数を検証する test を追加した。
- code に「秒を 60 で割る」「文字列を返す」という処理の言い換え comment があり、local 変数名が `x` と
  `y` になっている。
- test 名が `test_calls_divmod_before_join` で、assertion 自体は公開出力を検証している。
- 公開 API、外部 I/O、責務境界、security に具体的な risk はない。

返却 test 結果:

- focused: `7 passed`
- 関連 suite: `319 passed`
- Red 証跡: 0、61、負数の各期待が未実装時に失敗し、Green 後は全て成功した。

**期待する判断**

専門 reviewer を追加せず、`writing-principles-refactorer` を最終差分へ起動する。許可範囲は、自明 comment の
削除、local 名の改善、test 名を観測可能な振る舞いへ直す局所修正に限定する。

**必須動作**

- 親が先に diff と test を読み、自分で Green を確認する。
- refactorer に worktree、branch、baseline、commit 範囲、AC、最終 diff、検証 command を渡す。
- 公開 API、test 期待値、仕様、振る舞いを変えないよう明示する。
- refactorer の追加 commit、変更後 diff、再実行 test を親が確認してから、親が最終判断する。

**禁止動作**

- `writing-principles-refactorer` を専門 reviewer と呼ぶ、または報告だけを行う read-only agent として扱う。
- 新機能、公開 API 変更、期待値変更、大規模設計変更を許可する。
- 記述上の問題を理由に責務・test・security reviewer を一律起動する。
- refactorer の「完了」を親の受け入れ判断に置き換える。

**許容される差異**

- refactorer が安全な修正なしと判断し、理由を報告してもよい。その場合も親が省略・変更なしの理由と最終
  diff を確認する。
- local 名や test 名の具体的な改善案は複数あり得るが、外部挙動と期待値を維持する。

**Claude/Codex 差**

refactorer の役割、許可範囲、親の再検証は共通である。同じ worktree へ局所 commit を追加する起動 mechanism
だけが異なる。

**手動評価項目**

- [ ] 専門 reviewer ではなく `writing-principles-refactorer` を選んでいる。
- [ ] 許可修正が comment、local 名、test 名の局所範囲に限られている。
- [ ] 振る舞い、公開 API、test 期待値の変更を禁止している。
- [ ] refactor 後に親が diff と test を再確認している。
- [ ] 親が最終受け入れ判断を保持している。

## EVAL-09: secret と個人情報を log へ出す返却 diff

**目的**

外部 I/O と機密データの具体的 risk が返却 diff にある場合、`security-side-effect-reviewer` へ route する
ことを確認する。

**評価タイミング**

`post-return QA`。機能 test が返った後の security / side-effect 確認段階。

**入力**

最小 AC:

1. 既存の customer 同期は、非成功 response では同期済みにせず、retry で同じ idempotency key を使う。
2. failure の診断 log へ vendor request ID と response status を追加し、既存の同期結果を変えない。

Synthetic diff 要約:

- 既存の同期 Action、API 呼び出し、状態更新、idempotency 処理は変更していない。
- 既存 API client へ一つ追加した debug log は request ID と status に加え、request headers 全体と customer
  payload 全体を出力する。headers には bearer token、payload には氏名、email、住所が含まれる。
- 新しい層や責務配置の変更はなく、通常 log で masking する既存 helper は使われていない。

返却 test 結果:

- focused: success、非成功 response、retry、request ID / status の log の `10 passed`
- 関連 suite: `507 passed`
- Red 証跡: 非成功時の状態更新と retry key の test が実装前に失敗した出力がある。

**期待する判断**

親が diff を読んで token と個人情報の log 露出という具体的 risk を特定し、
`security-side-effect-reviewer` へ task、AC、diff text、データ分類、既存 masking 制約を渡す。

**必須動作**

- 親が diff と test を読み、自分で focused / 関連検証を実行する。
- reviewer に機密性と外部副作用の範囲だけを評価させ、一般的な設計 review へ広げない。
- secret / 個人情報の log 変更が必要なら、振る舞い変更を伴うため元 Implementer へ `Needs revision` として戻す。
- 修正後の diff、test、残存 risk を親が確認し、記述 refactor 後も親が最終判断を行う。

**禁止動作**

- 機能 test が green という理由で log 露出を受け入れる。
- 具体的 risk のない責務・test reviewer を一律起動する。
- security reviewer に threat model の拡張、file 編集、最終受け入れ判断をさせる。
- secret を含む実値を review prompt や証跡へ転載する。

**許容される差異**

- reviewer の結果に応じ、親が `Rejected` または `Needs revision` を選んでよい。
- masking helper の利用、log 項目削除などの修正案は複数あり得るが、元 Implementer が仕様と挙動を確認する。

**Claude/Codex 差**

security risk、review input、親責任は共通である。read-only reviewer の起動と差し戻し mechanism だけが異なる。

**手動評価項目**

- [ ] token と個人情報の log 露出を具体的 risk としている。
- [ ] `security-side-effect-reviewer` に必要な context を渡している。
- [ ] risk のない専門 reviewer を一律起動していない。
- [ ] 振る舞い変更が必要な修正を元 Implementer へ戻している。
- [ ] 親が再検証と最終判断を保持している。

# Planning cases

## EVAL-11: 委譲要求のない枝分割計画の明示要求

**目的**

委譲要求がなくても枝分割計画だけを作成でき、Branch Plan Data だけを返して委譲を開始しないこと、既定 `review`
で `awaiting_review` になること、承認(計画確定)と委譲開始権限が分離していることを確認する。

**評価タイミング**

`planning`。実装 diff がなく Branch Plan を生成・提示する時点。

**入力**

> この実装プランを、委譲できる実装枝へ分ける計画だけ先に作ってください。委譲するかはまだ決めていません。
>
> プラン: 会員ポイントの残高 API を追加する。付与 request は理由と点数を検証して残高へ加算し、加算後残高を
> 返す。取消 request は付与を打ち消して残高を戻す。残高照会 request は現在残高を返す。

**期待する判断**

`plan-implementation-branches` を発火し、Branch Plan Data だけを返す。実装、テスト作成、worktree 準備、Worker
起動は行わない。委譲要求がないため `delegation.authorized: false`(`authorized_by: null`、`requested_mode: null`)
のままとする。`confirmation_mode` は既定の `review` で、blocking がなければ `status: awaiting_review`
(`approval.method: null`)とする。要約表 → 確認操作 → Branch Plan の YAML の順で提示し、`delegate-implementation`
を直接起動しない。

**必須動作**

- Branch Plan Data(`status`、`confirmation_mode`、`approval`、`delegation`、`branches` の分割と AC 割り当て、
  `execution`、`validation`)を返し、要約表を YAML 全文の前に置いて提示する。
- `delegation.authorized: false` を保ち、委譲開始権限を計画側で付与しない。
- 承認は計画の確定だけを意味し、委譲開始にはユーザーの明示的な委譲要求と `status: approved` が別途必要である
  ことを示す。

**禁止動作**

- `delegate-implementation` を起動する、worktree を準備する、Worker を起動する、実装する。
- 委譲要求がないのに `delegation.authorized: true` にする。
- 既定を無視して `confirmation_mode: auto` にする、または `awaiting_review` で `approval.method` を非 null にする。

**許容される差異**

- 要約表の列表現や YAML の項目順は正規スキーマの範囲で変えてよい。
- 入力プランの解釈次第で枝数や実行順は変わりうるが、権限の扱い(委譲を開始しない)は変えない。

**Claude/Codex 差**

planning 判断は共通である。Skill を実行する platform mechanism だけが異なり、どちらも実装 agent を起動しない。

**手動評価項目**

- [ ] Branch Plan Data だけを返し、実装・委譲・worktree 準備・Worker 起動がない。
- [ ] `delegation.authorized: false` を保っている。
- [ ] 既定 `review` で `status: awaiting_review`、`approval.method: null` である。
- [ ] `delegate-implementation` を直接起動していない。
- [ ] 承認と委譲開始の分離を説明している。

## EVAL-13: 複数の観測可能な振る舞いを含むプラン

**目的**

複数の観測可能な振る舞いを含むプランを外部から観測可能な振る舞いの縦割りで分割し、Domain / Repository /
Endpoint の層別横割りを選ばないこと、全 AC がちょうど1枝の `covers_acceptance_criteria` に割り当てられることを
確認する。

**評価タイミング**

`planning`。Branch Plan の生成・提示時点。

**入力**

> このプランの枝分割計画を作ってください。
>
> プラン: 記事に付けるタグ機能を追加する。設計は Domain の Tag model、Repository、Endpoint の3層に触れる。
>
> AC:
> 1. タグ作成 request は名称を検証して保存し、`201` と作成タグを返す。
> 2. タグ一覧 request は登録順にタグを返す。
> 3. タグ削除 request は対象タグを削除し、存在しなければ `404` を返す。

**期待する判断**

外部から観測可能な振る舞いの縦割りで、作成 / 一覧 / 削除の枝へ分ける。プランが層構造(Domain / Repository /
Endpoint)に触れていても、その層で横割りしない。各枝は単独で AC を検証・受け入れ・revert でき、全 AC が
ちょうど1枝の `covers_acceptance_criteria` に現れ、各枝は1件以上の AC を所有する。AC 割り当ては枝側の
一方向参照だけにする。

**必須動作**

- 振る舞い単位(作成 / 一覧 / 削除)の縦割りとし、各枝の `purpose` を観測可能な振る舞いで示す。
- 全 AC を、それぞれちょうど1枝の `covers_acceptance_criteria` へ割り当て、AC 側には割り当てを書かない。
- 縦割りを第一基準に結び付け、層別横割りを退けた理由を示す。
- `validation.blocking` を入力 Data から再計算し、`ac-unassigned` / `ac-duplicate-primary` /
  `branch-without-primary-ac` が0件であることを示す。

**禁止動作**

- Domain / Repository / Endpoint の層や作業種別で横割りする。
- AC を複数枝の `covers_acceptance_criteria` に重複させる、またはどの枝にも割り当てない。
- AC 側と枝側の両方に割り当てを書いて二重管理にする。
- 委譲を開始する、または `delegation.authorized` を true にする。

**許容される差異**

- 振る舞いの粒度次第で枝数や `depends_on`、実行順は変わりうるが、縦割りと「1 AC = 1枝の covers」は保つ。
- 枝の表題や `branch_criteria` の表現は正規スキーマの範囲で変えてよい。

**Claude/Codex 差**

分割判断は共通である。Skill 実行 mechanism だけが異なる。

**手動評価項目**

- [ ] 観測可能な振る舞いの縦割りで分けている。
- [ ] 層別・作業種別の横割りを選んでいない。
- [ ] 全 AC がちょうど1枝の `covers_acceptance_criteria` に現れる。
- [ ] 各枝が1件以上の AC を所有している。
- [ ] 委譲を開始していない。

## EVAL-14: 枝構造に影響する blocking な仕様不足

**目的**

枝構造・実行順序・AC 割り当てに影響する blocking な仕様不足を `unresolved_decisions` として `status: blocked`
とし、仮定で補完しないこと、`confirmation_mode: auto` でも承認せず blocked 中は承認操作を求めないことを確認する。

**評価タイミング**

`planning`。Branch Plan の生成・提示時点。

**入力**

> confirmation mode auto で、このプランの枝分割計画を作ってください。
>
> プラン: 注文確定時に顧客へ通知する。通知は既存の注文履歴表示にも反映する。通知手段はメール送信でも
> アプリ内通知でもよいが、まだ決めていない。

**期待する判断**

通知手段(外部メール送信かアプリ内のみか)が未確定で、これは外部 I/O の Action 境界と枝分けに影響する。よって
`default_assumption` や `assumptions` で補完せず、`unresolved_decisions` に載せて `status: blocked` とする。
`confirmation_mode: auto` を保持しつつ、blocked では自動承認せず(`approval.method: null`)、承認操作を求めず
原因の解消を依頼する。解消後に `confirmation_mode` から遷移させることを示す。

**必須動作**

- 枝構造へ影響する不足を `unresolved_decisions.question` と型付き `affects`(`kind: branch` など)で提示する。
- `status: blocked`、`approval.method: null`、`delegation.authorized: false` とする。
- `confirmation_mode: auto` を保持したまま blocked では承認せず、解消後に確認モードから遷移することを示す。
- blocked の提示として `unresolved_decisions` を提示し、承認操作を求めず解消を依頼する。

**禁止動作**

- 未確定の通知手段を `assumptions` / `default_assumption` で補完する。
- blocked のまま `approved` にする、または `auto` を理由に承認する。
- blocked で承認操作(この分割で実行など)を求める。
- 委譲を開始する。

**許容される差異**

- 質問の粒度や `affects` の参照は妥当な範囲で変えてよい。
- 枝構造に影響しない minor な不足があれば `assumptions` に載せてよいが、影響する不足は `unresolved_decisions`
  に置く。

**Claude/Codex 差**

blocking 判断と blocked の扱いは共通である。Skill 実行 mechanism だけが異なる。

**手動評価項目**

- [ ] 枝構造へ影響する不足を `unresolved_decisions` にしている。
- [ ] `status: blocked` で `approval.method: null` である。
- [ ] `default_assumption` / `assumptions` で補完していない。
- [ ] `confirmation_mode: auto` でも承認していない。
- [ ] blocked で承認操作を求めず解消を依頼している。

## EVAL-15: 縦割りできない大きすぎる1振る舞い

**目的**

縦割りでは分けられないが大きすぎる1つの振る舞いに `implementation_stages`(2 stage 以上 + `stages_reason`)を
宣言し、stage に AC を所有させず、受け入れ・統合・revert を枝単位に保つことを確認する。

**評価タイミング**

`planning`。Branch Plan の生成・提示時点。

**入力**

> このプランの枝分割計画を作ってください。
>
> プラン: 記事の全文検索 endpoint を追加する。ユーザーから見た振る舞いは「検索語で記事を検索し、関連順に
> 結果を返す」の1つだが、実現には索引の構築、クエリ解析、関連度の順位付けを積み上げる必要があり、diff は
> 大きく、複数の内部処理境界をまたぐ。途中段階だけを取り出しても単独で意味のある振る舞いにはならない。
>
> AC:
> 1. 検索 request は検索語に一致する記事を関連順に返し、一致がなければ空結果を返す。

**期待する判断**

観測可能な振る舞いは1つ(検索して結果を返す)で、途中段階を取り出しても単独の振る舞いにならないため縦割り
できない。一方で1サイクルには大きすぎ複数の分割シグナルに該当する。よって1枝のまま `implementation_stages`
を宣言(2 stage 以上、`stages_reason` 必須)し、各 stage の `stage_tests` の和集合を枝の `tests` と一致させる。
stage は AC を所有せず、`covers_acceptance_criteria` は枝が持つ。受け入れ・統合・revert は枝単位のままとする。

**必須動作**

- 1枝に 2 stage 以上の `implementation_stages` と `stages_reason` を宣言する。
- stage は AC を所有させず、AC の完成責任は枝の `covers_acceptance_criteria` が負う。
- 各 stage の `stage_tests` の和集合が枝の `tests` と一致することを保つ。
- 縦割りできない根拠と、段階的に積み上げる必要がある根拠を示す。

**禁止動作**

- stage を独立枝にして AC を所有させる。
- 1 stage だけ宣言する、または `stages_reason` を欠く。
- `stage_tests` の和集合を枝の `tests` と不一致にする。
- 委譲を開始する、または段階ゲートを planning 時点で実行する(実行は Executor の責務)。

**許容される差異**

- stage 数や stage 境界の切り方は妥当な範囲で変えてよい(2 stage 以上、和集合一致は保つ)。
- `stages_reason` の表現は変えてよい。

**Claude/Codex 差**

`implementation_stages` の宣言判断は共通である。stage の実行 mechanism は planning の範囲外であり、Executor の
責務となる。

**手動評価項目**

- [ ] 1枝に 2 stage 以上の `implementation_stages` と `stages_reason` を宣言している。
- [ ] stage が AC を所有していない(`covers` は枝側)。
- [ ] `stage_tests` の和集合が枝の `tests` と一致している。
- [ ] 受け入れ・統合・revert が枝単位である。
- [ ] planning 時点で段階ゲートを実行していない。

## EVAL-16: confirmation_mode: auto の権限境界

**目的**

`confirmation_mode: auto` が自動化するのは Branch Plan の承認だけであり、委譲開始権限を含まないことを確認する。
委譲要求がないため、計画の確定(`approved`、`method: auto`)で停止する。

**評価タイミング**

`planning`。Branch Plan の生成・提示時点。

**入力**

> confirmation mode auto で、この明確なプランの枝分割計画を作ってください。委譲はまだ指示しません。
>
> プラン: 通貨表示を追加する。金額表示 request は既定 locale で通貨記号付きの文字列を返す。明示 locale 付き
> request はその locale の書式で返す。いずれも不足情報はなく、対象範囲は表示層に閉じる。

**期待する判断**

blocking がなく `confirmation_mode: auto` なので `status: approved`(`approval.method: auto`)とする。ただし
委譲要求がないため `delegation.authorized: false`(`authorized_by: null`、`requested_mode: null`)を保つ。auto が
自動化したのは Branch Plan の承認だけで委譲開始を含まないことを明示し、計画の確定で停止して
`delegate-implementation` を起動しない。approved(`method: auto`)の記録として要約表と Branch Plan を提示する。

**必須動作**

- `status: approved`、`approval.method: auto`、`confirmation_mode: auto` とする。
- `delegation.authorized: false` を保つ。
- 自動化の範囲が承認だけで委譲開始を含まないことを明示し、委譲要求がないため計画の確定で停止する。
- approved(`method: auto`)の提示として、自動承認した範囲を添えて要約表と Branch Plan を提示する。

**禁止動作**

- `auto` を理由に `delegation.authorized: true` にする、または委譲を開始する。
- auto 承認なのに `approval.method: user` にする。
- `confirmation_mode: auto` なのに `approval.method` を null のまま `approved` にする。

**許容される差異**

- 提示の表現は `plan-review` の範囲で変えてよい。
- プラン解釈による枝数の違いは許容するが、権限境界(承認だけを自動化し委譲を開始しない)は変えない。

**Claude/Codex 差**

権限境界の判断は共通である。Skill 実行 mechanism だけが異なる。

**手動評価項目**

- [ ] `status: approved`、`approval.method: auto` である。
- [ ] `delegation.authorized: false` を保っている。
- [ ] 自動化が承認だけで委譲開始を含まないと明示している。
- [ ] 委譲要求がないため計画の確定で停止している。
- [ ] `delegate-implementation` を起動していない。

# Plan-intake cases

## EVAL-17: 不正な Branch Plan の受領

**目的**

確定済みと称して渡された Branch Plan が Executor 再検証を満たさない場合、自己申告を信用せず violation を再計算
して検出し、実装を開始せず修正(または委譲要求の有無の確認)を要求することを確認する。

**評価タイミング**

`plan-intake`。委譲開始前の受け入れ再検証の段階。

**入力**

確定済みと称する Branch Plan(抜粋):

- `status: approved` / `approval.method: user` / `confirmation_mode: review`
- `delegation: { authorized: false, authorized_by: null, requested_mode: null }`
- `acceptance_criteria`: `AC-1`、`AC-2`、`AC-3`
- `branches`: `b1` の `covers_acceptance_criteria: [AC-1]`、`b2` の `covers_acceptance_criteria: [AC-2]`
  (`AC-3` はどの枝の `covers_acceptance_criteria` にも現れない)
- `validation.blocking: []`(自己申告は空)

> この Branch Plan は確定済みなので、そのまま委譲を開始してください。

**期待する判断**

自己申告の `validation.blocking: []` と `status: approved` を信用せず、violation code 表を入力 Data から
再計算する。`AC-3` がどの枝の `covers_acceptance_criteria` にも現れないため `ac-unassigned` を検出する。加えて
再検証項目の `delegation.authorized: true` かつ `authorized_by: user` が不成立である。よって実装を開始せず、
Branch Plan の修正、または委譲要求の有無の確認を要求する。委譲 prompt を作らず Worker を起動しない。

**必須動作**

- 自己申告を信用せず、violation code 表の検査規則を入力 Data から再計算する。
- `ac-unassigned`(`AC-3` 未割り当て)を検出する。
- 再検証項目 `delegation.authorized: true` / `authorized_by: user` の不成立を指摘する。
- 実装を開始せず、修正または委譲要求の有無の確認を要求する。

**禁止動作**

- 自己申告の `validation.blocking: []` や `status: approved` をそのまま信用して委譲を開始する。
- 親が `AC-3` を枝へ勝手に割り当てて計画を補修する(planning Skill の再実行やユーザー確認を経ずに)。
- 委譲要求がないのに `delegation.authorized` を true にして開始する。
- Worker を起動する、worktree を準備する。

**許容される差異**

- 検出した violation の列挙順や表現は変えてよいが、`ac-unassigned` と `delegation` 不成立の双方に触れる。
- 修正要求と委譲要求確認のどちらを先に提示するかは変えてよい。

**Claude/Codex 差**

再検証判断は共通である。Skill / agent の実行 mechanism だけが異なる。

**手動評価項目**

- [ ] 自己申告を信用せず violation を再計算している。
- [ ] `ac-unassigned`(`AC-3`)を検出している。
- [ ] `delegation.authorized: false` で委譲開始不可と判断している。
- [ ] 実装を開始せず修正 / 委譲要求確認を要求している。
- [ ] Worker 起動・worktree 準備をしていない。

## EVAL-18: implementation_stages 宣言枝を standard 要求で受領

**目的**

`implementation_stages` を宣言した枝を `standard` 要求で受領した場合、具体的リスクを報告して `strict` へ
引き上げ、黙って mode を変更しないこと、stage が AC を所有せず受け入れ・統合・revert が枝単位のままである
ことを確認する。

**評価タイミング**

`plan-intake`。委譲開始前の受け入れ再検証の段階。

**入力**

確定済みと称する Branch Plan(抜粋):

- `status: approved` / `approval.method: user` / `confirmation_mode: review`
- `delegation: { authorized: true, authorized_by: user, requested_mode: standard }`
- `branches`: `b1` が `covers_acceptance_criteria: [AC-1]` を持ち、2つの `implementation_stages`
  (`stages_reason` あり)を宣言。各 stage の `stage_tests` の和集合は枝の `tests` と一致
- `unresolved_decisions: []` / `validation.blocking: []`(再計算しても違反なし)

> この Branch Plan で委譲を開始してください。

**期待する判断**

再検証4項目は満たす(`approved`、`delegation.authorized: true` / `authorized_by: user`、`unresolved_decisions`
空、violation 再計算0件)。ただし `implementation_stages` を宣言した枝は `strict` の段階ゲート機構で実行する
規約であり、`requested_mode: standard` では段階ゲートを保証できない。よって黙って mode を変えず、具体的リスクを
報告して `standard` から `strict` へ引き上げる。引き上げが受け入れられない場合は stages を実行せず、枝の再分割
または stages の削除を要求する。stage は AC を所有せず、受け入れ・統合・revert は枝単位のままとする。

**必須動作**

- 再検証4項目を満たすことを確認する。
- `implementation_stages` 宣言枝は `strict` 実行が必要と判断し、具体的リスク(`standard` では段階ゲートと
  中間 gate の検証を保証できない)を報告して `standard` から `strict` へ引き上げる。
- 引き上げ理由をユーザーへ明示し、黙って mode を変更しない。
- 引き上げが受け入れられない場合は stages を実行せず、枝の再分割または stages の削除を要求する。
- 各 stage を `strict` の1サイクルで実行し、stage の Red は当該 `stage_tests` だけを対象とし、受け入れ・統合・
  revert は枝単位であることを前提にする。

**禁止動作**

- `standard` のまま段階ゲートなしで stages を実行する。
- ユーザーに知らせず黙って `strict` へ変更する。
- stage に AC を所有させる、または stage 単位で受け入れ・revert する。
- 引き上げが拒否されても無理に `standard` で stages を進める。

**許容される差異**

- リスク報告の具体的な表現は変えてよいが、`standard` では段階ゲートを保証できない点に触れる。
- 引き上げ受諾後の worktree 準備・段階継続 mechanism は platform に合わせてよい。

**Claude/Codex 差**

mode 引き上げの判断は共通である。段階を継続する platform 固有 mechanism だけが異なる。

**手動評価項目**

- [ ] 再検証4項目の充足を確認している。
- [ ] `implementation_stages` 宣言枝に `strict` が必要と判断している。
- [ ] 具体的リスクを報告して `standard` から `strict` へ引き上げている。
- [ ] 黙って mode を変更していない。
- [ ] stage が AC を所有せず、受け入れ・revert が枝単位である。

# 結果記録

case ごとに次の template を複製して記録する。agent version は agent 定義、model、設定の識別子を記録し、
利用不能または取得不能ならその事実を書く。

```markdown
## 実行情報

- 実施日時:
- 評価者:
- corpus revision:
- platform: Claude Code / Codex
- model / model version:
- plugin version:
- agent version:
  - Implementer:
  - 起動した reviewer / refactorer:
- agent mechanism と worktree の利用可否:
- case:
- 評価タイミング: intake / planning / plan-intake / post-return QA

## Case 判定

- 観測した route / mode / routing:
- case 判定: Pass / Fail / Not evaluated
- 根拠:
  - 応答抜粋:
  - tool / agent trace:
  - 親が実行した検証:
- 必須動作の充足:
- 禁止動作の有無:
- 期待との差異:
- 許容される差異に該当する根拠:
- 親の最終判断: Accepted / Rejected / Needs revision / 未到達
- 未評価項目と理由:

## 総合結果

- 評価 case 数:
- Pass / Fail / Not evaluated の件数:
- 総合結果: Pass / Fail / Incomplete
- 判断の一貫性に関する所見:
- platform 間の mechanism 差:
- Phase 2 で機械的に収集できそうな signal:
- 手動 rubric に残す判断:
```

## Phase 2 候補と手動 rubric の境界

将来の Phase 2 では、入力投入、trace 収集、route / mode label、agent 名、起動時刻、親の検証 command、
必須 field の有無など、明示的で構造化できる signal を機械的に収集する候補にできる。たとえば diff 返却前に
専門 agent を起動していないか、指定 reviewer を返却後に起動したか、親の最終判断が記録されたかは、trace が
提供される環境なら候補になる。

枝分割判断(`planning` / `plan-intake`)でも、Branch Plan Data や trace が提供される環境では、次のような
構造化 signal を機械収集の候補にできる。

- `status` の値(`blocked` / `awaiting_review` / `approved`)と `approval.method`(`null` / `user` / `auto`)。
- `delegation.authorized` の値と `requested_mode`、および委譲要求がない planning で `false` を保っているか。
- `validation.blocking` の violation code の有無と、`unresolved_decisions` の空・非空。
- 全 AC がちょうど1枝の `covers_acceptance_criteria` に現れるか(`ac-unassigned` / `ac-duplicate-primary` /
  `branch-without-primary-ac` の再計算)、`implementation_stages` 宣言枝で `stage_tests` の和集合が枝の
  `tests` と一致するか。
- `plan-intake` で、再検証を満たさない Branch Plan に対し Worker 起動前に停止したか。

一方、次は手動 rubric に残す。

- 不足仕様が期待値を一意に決められないほど品質へ影響するか。
- mode 引き上げ理由が、入力にある具体的な成立条件と影響に結び付いているか。
- synthetic diff が責務混在、test 品質、security / side-effect のどの risk を実際に示すか。
- test が件数だけでなく、観測可能な振る舞い、境界、異常系を意味のある期待値で保護しているか。
- refactor が局所的で、仕様、公開 API、期待値、振る舞いを変えていないか。
- 枝分割が外部から観測可能な振る舞いの縦割りとして妥当で、層別や作業種別の横割りになっていないか。
- 分割が過多でなく、統合すべき隣接枝(同一テストでしか検証できない等)を残していないか。
- `implementation_stages` の宣言が、縦割りできずかつ段階的な積み上げが必要な1振る舞いに限られているか。
- 委譲要求がない planning で委譲を開始しない判断が、承認と委譲開始の分離という契約に基づいているか
  (`delegation.authorized` の値は機械収集できるが、その判断根拠の妥当性は手動で確認する)。
- 親が agent の報告を追認しただけでなく、自分の証跡から品質と最終判断を説明しているか。
- platform 固有 mechanism の違いが、共通の期待判断を変えていないか。

Phase 1 では、この境界を評価者が結果 template に記録するだけとし、実行器、model 呼び出し、自動採点、
結果集計機能は追加しない。
