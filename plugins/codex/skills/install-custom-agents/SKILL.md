---
name: install-custom-agents
description: >-
  agentic-qa-workflow の Codex custom agent を user scope または repository scope に
  インストール、バージョン確認、更新する。ユーザーが custom agent の導入、再インストール、
  バージョン確認、更新、上書きを明示的に依頼した場合、または delegate-implementation が
  必要な custom agent の不足を検出した場合に使う。既存ファイルを確認なしで上書きしない。
---

# Custom agent のインストール

plugin に同梱された `install/install-agents.sh` を唯一のインストール処理として使う。
TOML を個別にコピーしない。

## 手順

1. 利用可能な custom agent の一覧を先に確認する。
2. 対象 scope を確定する。personal install は `--user`、repository install は
   `--repo <repo-path>` を使う。曖昧な場合はユーザーに確認する。
3. 次の確認コマンドを実行する。この操作ではファイルを変更しない。

   ```bash
   "$PLUGIN_DIR"/install/install-agents.sh --check --user
   # または
   "$PLUGIN_DIR"/install/install-agents.sh --check --repo <repo-path>
   ```

4. 未インストールなら、同じ scope で `--check` を外して実行する。
5. 既存版と同梱版が同一で内容も一致する場合は、変更せず最新であると報告する。
6. バージョンまたは内容が異なる場合は、installed version、bundled version、対象 directory を
   ユーザーへ提示し、上書きしてよいか明示的に確認する。ユーザーが更新や上書きを依頼済みでも、
   この確認を省略しない。
7. 承認された場合だけ、同じ scope へ `--force` を付けて実行する。

   ```bash
   "$PLUGIN_DIR"/install/install-agents.sh --force --user
   # または
   "$PLUGIN_DIR"/install/install-agents.sh --force --repo <repo-path>
   ```

8. 完了後は Codex の再起動を依頼し、この session では委譲計画や実装へ進まない。再起動後に
   custom agent の一覧を再確認する。

`--check` が終了コード `3` を返すのは、未インストールまたは更新候補があることを示す。
エラーとして扱わず、表示された状態に従って上記手順を続ける。
