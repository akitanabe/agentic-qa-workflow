# Workflow Decision Corpus

この corpus は、`delegate-implementation` workflow の判断を代表入力に対して人間が一貫して評価するための
Phase 1 データである。正本は `shared/skill/delegate-implementation/SKILL.md` と、その `references/`、
関連する `shared/agents/` にあり、この文書は正本を置き換えない。

Phase 1 では全ケースを手動評価する。この文書自身は model や agent を実行せず、自動採点もしない。
入力中の repository、diff、test 結果、外部サービス、本番データは評価用の架空データであり、実在する
環境への変更や破壊的操作を指示するものではない。
自動実行、model 呼び出し、自動採点、結果集計は Phase 2（issue #41）の責務とする。

## 共通の評価契約

### 評価タイミング

- `intake`: 実装 diff が存在しない初期依頼の時点。skill の発火、route / mode、確認の要否、最初の行動を
  評価する。返却後にだけ判断できる専門 review をこの時点で先取りしない。
- `post-return QA`: Implementer から commit、diff、test 結果が返った時点。親が返却物を読んだ後の
  risk 特定、reviewer / refactorer の routing、修正先、受け入れ判断を評価する。

### platform 共通の期待

期待する workflow 判断は Claude Code と Codex で共通とし、各 platform 用に複製しない。差が許されるのは
agent の起動、同一枝の継続、worktree の準備、待機などの実行 mechanism だけである。

- Claude Code では、新しい Implementer を worktree 隔離した `Agent` として起動し、同一枝の段階 gate や
  差し戻しだけを同じ context へ継続する。
- Codex では、親が専用 worktree を準備し、新しい Implementer を `fork_turns: "none"` の
  `spawn_agent` で起動する。同一枝の段階 gate や差し戻しには `followup_task` を使い、完了まで待機する。
- 必要な agent mechanism、agent、または worktree 隔離が利用できない場合、委譲や review を実行したふりを
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
4. `post-return QA` case では、記載された最小 AC、synthetic diff 要約、返却 test 結果を一組の返却物として
   与える。親がそれらを読む前に agent を起動していないことを確認する。
5. 応答文だけでなく、利用できる場合は tool / agent の起動順、親が実行した検証、最終判断までを証跡として
   保存する。実行 mechanism が利用不能なら、その報告と停止位置を保存する。
6. 「期待する判断」「必須動作」「禁止動作」を基準に case を `Pass` / `Fail` / `Not evaluated` で判定する。
   「許容される差異」に収まる違いだけを理由に `Fail` としない。
7. 一つでも `Fail` があれば総合結果は `Fail`、`Fail` がなく `Not evaluated` があれば `Incomplete`、全て
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
- 評価タイミング: intake / post-return QA

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

一方、次は手動 rubric に残す。

- 不足仕様が期待値を一意に決められないほど品質へ影響するか。
- mode 引き上げ理由が、入力にある具体的な成立条件と影響に結び付いているか。
- synthetic diff が責務混在、test 品質、security / side-effect のどの risk を実際に示すか。
- test が件数だけでなく、観測可能な振る舞い、境界、異常系を意味のある期待値で保護しているか。
- refactor が局所的で、仕様、公開 API、期待値、振る舞いを変えていないか。
- 親が agent の報告を追認しただけでなく、自分の証跡から品質と最終判断を説明しているか。
- platform 固有 mechanism の違いが、共通の期待判断を変えていないか。

Phase 1 では、この境界を評価者が結果 template に記録するだけとし、実行器、model 呼び出し、自動採点、
結果集計機能は追加しない。
