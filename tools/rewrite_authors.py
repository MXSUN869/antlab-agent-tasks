"""重写仓库中所有提交的作者/提交者身份，且不经过 shell。

为什么需要专门做这个
--------------------
在本机（DSH 的 Windows 沙箱）里，常规办法**都不工作**：

    git rebase --root --exec 'git commit --amend --no-edit --reset-author'
    git filter-branch --env-filter '...'

两者都会启动 `sh.exe`，而沙箱禁止创建命名管道，实测报错：

    sh.exe: *** fatal error - couldn't create signal pipe, Win32 error 5

因此本脚本在 Python 里直接设置 `GIT_AUTHOR_*` / `GIT_COMMITTER_*` 环境变量，
用 `git commit-tree` 逐个重建提交。姓名与邮箱通过环境变量传递，
不经过任何 shell，中文不会乱码。

保留什么
--------
- 每棵树（tree）完全不变 → 所有文件内容与 blob 哈希不变；
- 每条提交信息逐字不变；
- **原有的作者时间与提交时间不变**（只改姓名与邮箱，不改时间线）；
- 父链顺序不变。

用法
----
    # 预演（只报告，不改动）
    python tools/rewrite_authors.py

    # 用 git config 里的身份改写全部提交
    python tools/rewrite_authors.py --apply

    # 或显式指定（例如改用 GitHub 的 noreply 地址）
    python tools/rewrite_authors.py --apply \
        --name "你的名字" --email "你的用户名@users.noreply.github.com"

改写后可自行核验：

    git log --format="%h %an <%ae> %ad" --date=short
    git diff --stat <改写前的HEAD> HEAD      # 应为空
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def git(args, env=None, binary=False):
    result = subprocess.run(["git"] + args, cwd=REPO, capture_output=True, env=env)
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode("utf-8", "replace"))
        raise SystemExit("git " + " ".join(args) + " 失败")
    return result.stdout if binary else result.stdout.decode("utf-8", "replace")


def config(key):
    result = subprocess.run(["git", "config", key], cwd=REPO, capture_output=True)
    return result.stdout.decode("utf-8", "replace").strip()


def parse_dates(raw):
    """从原始提交对象里取出 author / committer 的时间戳与区号。"""
    author_date = committer_date = None
    for line in raw.split(b"\n"):
        if line.startswith(b"author ") and author_date is None:
            parts = line.decode("utf-8", "replace").rsplit(">", 1)
            author_date = parts[1].strip() if len(parts) == 2 else None
        elif line.startswith(b"committer ") and committer_date is None:
            parts = line.decode("utf-8", "replace").rsplit(">", 1)
            committer_date = parts[1].strip() if len(parts) == 2 else None
    return author_date, committer_date


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="实际重写；缺省只预演")
    parser.add_argument("--name", default=None, help="新的作者姓名；缺省用 git config user.name")
    parser.add_argument("--email", default=None, help="新的作者邮箱；缺省用 git config user.email")
    args = parser.parse_args()

    name = args.name or config("user.name")
    email = args.email or config("user.email")
    if not name or not email:
        raise SystemExit("未指定姓名/邮箱，且 git config 里也没有；请用 --name/--email 指定")

    commits = git(["rev-list", "--reverse", "HEAD"]).split()
    print(f"共 {len(commits)} 个提交；目标身份：{name} <{email}>")

    if not args.apply:
        print("预演模式：未改动任何内容。加 --apply 生效。")
        print("将保留：每棵树、每条提交信息、原有的作者时间与提交时间。")
        return

    old_head = git(["rev-parse", "HEAD"]).strip()
    print(f"重写前的 HEAD：{old_head}")
    current = config("user.name") + " <" + config("user.email") + ">"
    print(f"（当前 git config 身份：{current}）")

    tmpdir = tempfile.mkdtemp(prefix="rewrite-authors-")
    parent = None
    for index, commit in enumerate(commits, 1):
        raw = git(["cat-file", "commit", commit], binary=True)
        tree = git(["rev-parse", commit + "^{tree}"]).strip()
        message = raw.split(b"\n\n", 1)[1] if b"\n\n" in raw else b""
        author_date, committer_date = parse_dates(raw)

        msg_path = os.path.join(tmpdir, f"msg-{index}.txt")
        with open(msg_path, "wb") as handle:
            handle.write(message)

        env = dict(os.environ)
        env.update({
            "GIT_AUTHOR_NAME": name,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name,
            "GIT_COMMITTER_EMAIL": email,
        })
        if author_date:
            env["GIT_AUTHOR_DATE"] = author_date
        if committer_date:
            env["GIT_COMMITTER_DATE"] = committer_date

        create = ["commit-tree", tree]
        if parent:
            create += ["-p", parent]
        create += ["-F", msg_path]
        new_commit = git(create, env=env).strip()

        subject = message.decode("utf-8", "replace").splitlines()[0] if message else ""
        print(f"  [{index}/{len(commits)}] {commit[:7]} -> {new_commit[:7]}  {subject}")
        parent = new_commit

    git(["reset", "--hard", parent])
    print()
    print("完成。新的 HEAD：", git(["rev-parse", "HEAD"]).strip())
    print("如需回退：git reset --hard", old_head)


if __name__ == "__main__":
    main()
