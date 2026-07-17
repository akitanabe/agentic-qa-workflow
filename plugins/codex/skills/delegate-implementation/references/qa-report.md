<!-- Generated from shared/. Do not edit directly. -->

# 永続 QA レポート

## 目次

- 位置づけと出力条件
- 保存先と slug
- 衝突と作成
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

親は全枝のQA、統合済みdiff review、最終検証、最終判断を終える。最終 gate 後に cleanup の実施可否と
結果を確定してから、sanitized Markdown Dataを完成させ、条件付き report を生成する。`Needs revision` などで
worktree を保持する場合も cleanup 状態と理由を記録する。親の最終判断時に1回だけ生成し、その後に
会話上の最終報告を行う。sanitize できない場合は生成しない。生成しなかった理由を会話上の最終報告へ含める。

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
構築後のtarget pathへ適用する。targetはreports直下の単一Markdown fileでなければならない。固定の
`.agentic-qa/reports/` prefixを除くfile name componentにpath separator を許可しない。`.` または `..` を
許可しない。絶対 path を許可しない。reports 直下以外を許可しない。

生成または削除の前にcanonical repository rootを確定する。`.agentic-qa` と `reports` の各既存 ancestor
componentをsymlink を追わない `lstat` 相当で検査し、symlink または directory 以外なら停止する。
componentまたはtargetがcanonical repository root 外へ解決される場合は停止する。この検査を生成と削除の
両方へ適用する。欠けているdirectoryを作成した場合も、reportを書き込む前に同じ検査を行う。

## 衝突と作成

既存 file を上書きしない。workflow 内では既存 report を更新しない。`<slug>.md` が既存の通常fileなら、
`<slug>-2.md`, `<slug>-3.md` の順に最初の空きを選ぶ。suffix 込みの stem は最大80文字とし、超える場合は
suffixを保持してbaseの末尾を切る。

出力先または候補が symlink、directory、非通常 file なら停止する。番号を飛ばして次の候補を探さない。

親は保存対象のsanitized Markdown Data を先に完成させる。その後、候補に対してsymlink を追わない
exclusive create 相当のActionを使い、Dataを1回だけ書く。競合時は書き込まず次の suffix を再選択する。
競合した候補を`lstat`相当で再確認し、既存の通常fileならsuffix選択を続けるが、symlink、directory、
非通常fileなら停止する。安全な create Action を保証できない場合は生成しない。

## Git 管理と保持

`agentic-qa-workflow` repository の template source と generated asset は tracked 配布物である。これと、
利用先 repository で生成する report instance を区別する。instanceは既定では untracked / unstaged /
uncommitted とする。`.gitignore` と `.git/info/exclude` を自動変更しないため、`git status` に `??` として
表示されてよい。既定では `git add`、stage、commit しない。

report instanceをGit管理するのは、ユーザーの明示的な要求または既存の repository policy がある場合だけとする。
その場合も既存の実装 commit へ黙って amend しない。

自動期限または自動 purge を行わない。明示的な削除または repository policy まで保持する。削除時は
ancestor検査を再実行し、対象がreports 配下であることを確認してから削除する。削除対象は通常fileに限る。
通常の削除 commitでは Git 履歴から機密情報を消去できないため、tracked reportへ機密情報が入った場合は
履歴修正が別途必要になる。

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
- 絶対 path と local checkout path

必要な証跡は次のDataへ縮約する。

- file は repository 相対 path
- worktree は論理 ID、branch、cleanup 状態
- checkout は論理 ID と commit
- Implementer は role 名
- command は sanitize 済み文字列、status、短い要約

branch と file が敏感なら省略または sanitize する。絶対 path と local checkout path を保存しない。

untrusted fieldは保存前に次の順で正規化する。

1. 改行 `\n` と control 文字を空白へ置換して単一行にし、連続する空白をまとめる。
2. 挿入先のMarkdown context に応じて metacharacter を escape する。
3. HTML、link、image を plain text として escape し、描画や遷移を発生させない。

境界例は次のとおり。

- `line 1\nline 2` は `line 1 line 2`。
- `<b>admin</b>` は `&lt;b&gt;admin&lt;/b&gt;`。
- `[label](https://example.invalid)` は plain text として escape する。
- `![alt](https://example.invalid/image.png)` は plain text として escape する。

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
- Logical checkout ID / commit:

## Implementation branches

| Logical worktree ID | Branch (sanitized or omitted) | Implementer role | Cleanup state / reason | Integration state | Decision |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  | `Accepted` / `Rejected` / `Needs revision` |

## Acceptance Criteria → test

| AC | Test | Expected basis | Result |
| --- | --- | --- | --- |
|  |  |  |  |

## Changed files

- <sanitized repository relative path or omitted>

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
