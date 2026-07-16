<!-- Generated from shared/. Do not edit directly. -->

# 永続 QA レポート

## 目次

- 位置づけと出力条件
- 保存先と slug
- 衝突と更新
- Git 管理と保持
- 保存内容の最小化
- 標準 template

## 位置づけと出力条件

会話上の最終報告は常に行う。永続 QA レポートは任意の追加成果物であり、会話上の最終報告を
置き換えない。対象は `lite` / `standard` / `strict` の委譲 workflow で、`direct` は対象外とする。

永続 QA レポートは既定では生成しない。次のいずれかが要求した場合だけ出力対象にする。

- ユーザーの明示的な要求
- repository instruction
- Acceptance Criteria

1トップレベル workflow run につき1 report とする。複数の実装枝は同じ report へ列挙し、枝ごとに
`Accepted`、`Rejected`、`Needs revision` を記録できるようにする。未実行の検証と未統合の状態を
隠さない。最終判断は親だけが行う。

親は全枝のQA、統合済みdiff review、最終検証を終え、内容をsanitizeできることを確認してから、
親の最終判断時に1回だけ生成する。sanitize できない場合は生成しない。生成しなかった理由を
会話上の最終報告へ含める。

## 保存先と slug

保存先は repository root 相対の `.agentic-qa/reports/<slug>.md` に固定する。slugのbaseは、機密でない
task ID または title を候補にして、次の順で正規化する。

1. Unicode NFKC で正規化する。
2. 前後の空白を除去する。
3. ASCII lowercase へ変換する。
4. 非 `[a-z0-9]` の連続を `-` へ変換する。
5. 連続する `-` と前後の `-` を除去する。
6. base は最大64文字になるよう末尾を切る。

baseが空なら branch を候補にして同じ手順を繰り返す。なお空なら `delegated-implementation` を使う。
機密な入力名は使わず fallback へ進む。Windows 予約名には `qa-` prefix を付ける。予約名は
`con`, `prn`, `aux`, `nul`, `com1`〜`com9`, `lpt1`〜`lpt9` とする。

境界例は次のとおり。

- `ＡＢＣ １２３` は `abc-123`。
- title が `日本語`、branch が `Feature QA` なら `feature-qa`。
- title と branch が `日本語` なら `delegated-implementation`。
- `CON` は `qa-con`。

raw task ID、title、branch に含まれるseparatorはslugの正規化対象にできる。path制約は、正規化したslugから
構築後のtarget pathと、既存reportを更新するためユーザーが明示したpathへ適用する。targetはreports直下の
単一Markdown fileでなければならない。固定の`.agentic-qa/reports/` prefixを除くfile name componentに
path separator を許可しない。`.` または `..` を許可しない。絶対 path を許可しない。
reports 直下以外を許可しない。

## 衝突と更新

既存 file を上書きしない。`<slug>.md` が既存の通常fileなら、`<slug>-2.md`, `<slug>-3.md` の順に
最初の空きを選ぶ。suffix 込みの stem は最大80文字とし、超える場合はsuffixを保持してbaseの末尾を切る。

既存 report の更新はユーザーが対象 path を明示した場合だけ許可し、同じ保存先・path制約を再確認する。
出力先または候補が symlink、directory、非通常 file なら停止する。番号を飛ばして次の候補を探さない。

## Git 管理と保持

`agentic-qa-workflow` repository の template source と generated asset は tracked 配布物である。これと、
利用先 repository で生成する report instance を区別する。instanceは既定では untracked / unstaged /
uncommitted とする。`.gitignore` と `.git/info/exclude` を自動変更しないため、`git status` に `??` として
表示されてよい。既定では `git add`、stage、commit しない。

report instanceをGit管理するのは、ユーザーの明示的な要求または既存の repository policy がある場合だけとする。
その場合も既存の実装 commit へ黙って amend しない。

自動期限または自動 purge を行わない。明示的な削除または repository policy まで保持する。削除時は
対象がreports 配下であることを確認してから削除する。通常の削除 commit では Git 履歴から機密情報を
消去できないため、tracked reportへ機密情報が入った場合は履歴修正が別途必要になる。

reportは親の統合 checkout へ保存し、削除予定の worker worktree へ保存しない。

## 保存内容の最小化

次の機密情報と生の証跡を保存しない。

- 会話全文
- prompt
- reviewer の生出力
- command の全 log
- token
- password
- cookie
- Authorization
- private key
- `.env`
- credential 付き URL
- 機密 query
- 個人情報

これらの機密情報と生の証跡を保存しない。必要な証跡は次のDataへ縮約する。

- file は repository 相対 path
- worktree は論理 ID、branch、cleanup 状態
- Implementer は role 名
- command は sanitize 済み文字列、status、短い要約

保存直前に親が report 全体を確認する。安全に縮約できない内容が残る場合は、部分的な保存で済ませず
reportを生成しない。

## 標準 template

次のtemplateを1つのtop-level workflow runへ使用する。fieldへはsanitize済みのDataだけを記入する。

```markdown
# Delegated Implementation QA Report

## Task

- Sanitized task ID / title:
- Mode: `lite` / `standard` / `strict`
- Base commit:
- Integration checkout / commit:

## Implementation branches

| Logical worktree ID | Branch | Implementer role | Cleanup state | Integration state | Decision |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  | `Accepted` / `Rejected` / `Needs revision` |

## Acceptance Criteria → test

| AC | Test | Expected basis | Result |
| --- | --- | --- | --- |
|  |  |  |  |

## Changed files

- <repository relative path>

## Verification

| Sanitized command | Status | Short summary | Reason when not run |
| --- | --- | --- | --- |
|  | `Pass` / `Fail` / `Not run` |  |  |

`Not run` は理由必須。

## Red / Green / Refactor

- Red evidence:
- Green evidence:
- Refactor and re-verification:

## Responsibility boundaries

- Review status:
- Findings or reason not run:

## Test quality

- Review status:
- Findings or reason not run:

## Writing principles

- Review/refactor status:
- Findings or reason not run:

## Security / side effects

- Review status:
- Findings or reason not run:

## Integrated diff review

- Result:
- Follow-up:

## Residual risks

- Risk:
- Mitigation or owner:

## Parent decision

- Verdict: `Accepted` / `Rejected` / `Needs revision`
- 判断理由:

## Next action

- Action:
```

reviewer を起動しなかった場合も理由を記録する。対象 risk がないことは有効な理由である。
最終判断は親だけが記入する。
