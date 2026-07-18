<!-- Generated from shared/. Do not edit directly. -->

# ユーザー確認

生成した Branch Plan をユーザーへ提示し、確認を得る手順を定める。この Skill は計画の確定までを
担い、委譲は開始しない。確認はあくまで Branch Plan の承認であり、委譲開始権限とは独立している。

## 目次

- 提示の順序
- 要約表
- 確認操作
- blocked の提示
- assumptions と confirmation_mode

## 提示の順序

`status` に応じて提示内容を変える。

- `awaiting_review`: 要約表 → 確認操作 → Branch Plan の YAML 全文の順で提示する。要約表は
  YAML 全文の前に必ず置き、全文を読まなくても分割の妥当性を判断できるようにする。
- `blocked`: 先に `unresolved_decisions` と `validation.blocking` を提示し、解消を依頼する。
  この状態では承認操作を求めない。
- `approved`(`method: auto`): 自動承認した記録として要約表と Branch Plan を提示し、承認が
  自動化された範囲(委譲開始は含まない)を明示する。

## 要約表

YAML 全文の前に、次の列を持つ要約表を表示する。

| 実行順 | 枝 | 主責務 | テスト | 依存 |
| --- | --- | --- | --- | --- |

- 実行順は `execution.order` の順序に一致させる。
- 主責務は枝の `purpose`(外部から観測可能な振る舞い)を短く示す。
- テストは枝の `tests` の種別を示す。
- 依存は `depends_on` を示す。

`shared_foundation.required: true` の場合は、親が委譲前に実装する共有土台として表の前に明示する。

## 確認操作

ユーザーへ次の3種の操作を提示する。

- この分割で実行 — 提示した分割を承認する。
- 分割を修正 — 枝の分け方、順序、AC 割り当てなどの修正を求める。修正後に再生成する。
- 分割せず1枝で実行 — 分割を統合して1枝にまとめる。

ユーザーが分割の統合を指示した場合は `override` に `merge_branches: true` とユーザーが示した理由を
記録し、Branch Plan を再生成する。「分割を修正」の指示は、枝構造・実行順序・AC 割り当てへ
反映して validation を再実行してから再提示する。

承認は Branch Plan の確定だけを意味する。委譲開始は、ユーザーの明示的な委譲要求だけを根拠に
親エージェントが `delegation` を設定した後に、`delegate-implementation` 側で行う。

## blocked の提示

`status: blocked` では承認を求めず、原因の解消を依頼する。

- `unresolved_decisions` は `question` と `affects` を対応付けて提示し、確定が必要な判断を
  ユーザーへ示す。仮定で進めず、確定を待つ。
- `validation.blocking` は `code`、`path`、`message` を提示し、修正に必要な情報を示す。

原因が解消したら全 validation を再実行し、`confirmation_mode` から `awaiting_review` または
`approved`(`method: auto`)へ遷移させて改めて提示する。

## assumptions と confirmation_mode

- `assumptions` に置いた minor な仮定は、承認を求める前に一覧で明示する。枝構造・実行順序・
  AC 割り当てに影響しない仮定に限り、影響する不足は `unresolved_decisions` として提示する。
- `confirmation_mode: auto` は Branch Plan の承認だけを自動化する。ユーザーが明示した場合のみ
  使い、委譲開始権限は含まない。委譲開始には別途ユーザーの明示的な委譲要求が必要である。
- 既定の確認モードは `review` とする。
