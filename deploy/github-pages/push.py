"""Interactive local validation, commit and push. Run from any directory."""
from pathlib import Path
import datetime
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def git(*args, capture=False, check=True):
    return subprocess.run(
        ['git', *args], cwd=ROOT, check=check,
        stdout=subprocess.PIPE if capture else None,
        encoding='utf-8', errors='replace',
    )


def main():
    if not shutil.which('git'):
        raise RuntimeError('未找到 Git，请先安装 Git for Windows 并重新打开脚本。')
    python = ROOT / '.venv/Scripts/python.exe'
    if not python.is_file():
        raise RuntimeError('缺少 .venv，请按 README.md 安装 Python 环境和依赖。')
    print('正在构建并检查笔记……', flush=True)
    subprocess.run([str(python), str(ROOT / 'website/check.py')], cwd=ROOT, check=True)

    if not (ROOT / '.git').exists():
        git('init', '-b', 'main')
    branch = git('symbolic-ref', '--short', 'HEAD', capture=True).stdout.strip()
    if branch != 'main':
        raise RuntimeError(f'当前分支是 {branch}；Pages 工作流使用 main。请先手动确认分支配置。')
    if any((ROOT / '.git' / marker).exists() for marker in
           ('MERGE_HEAD', 'rebase-merge', 'rebase-apply', 'CHERRY_PICK_HEAD', 'REVERT_HEAD')):
        raise RuntimeError('Git 存在未完成的合并或变基等操作，请先手动完成。')
    if git('ls-files', '-u', capture=True).stdout.strip():
        raise RuntimeError('存在未解决的冲突，请先手动解决。')

    workflow = ROOT / '.github/workflows/pages.yml'
    if not workflow.exists():
        workflow.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'deploy/github-pages/pages.yml', workflow)
        print('已添加 GitHub Pages 工作流。')

    remote = git('remote', 'get-url', 'origin', capture=True, check=False)
    if remote.returncode:
        address = input('首次使用，请输入已创建的 GitHub 仓库地址（HTTPS 或 SSH）：').strip()
        if not (address.startswith('https://github.com/') or address.startswith('git@github.com:')):
            raise RuntimeError('请输入 https://github.com/用户名/仓库.git 或 git@github.com:用户名/仓库.git。')
        git('remote', 'add', 'origin', address)
    print('推送目标：', git('remote', 'get-url', '--push', 'origin', capture=True).stdout.strip())
    print('\n待提交的文件（包括新增、修改与删除；遵循 .gitignore）：', flush=True)
    git('-c', 'core.quotepath=false', 'status', '--short', '--untracked-files=all')
    print('\n将提交全部未忽略的变更并推送 main。content/ 内的文章和附件会用于公开站点。')
    if input('按 Enter 继续；输入 q 后回车取消：').strip().lower() == 'q':
        print('已取消，未暂存、提交或推送。')
        return

    if git('status', '--porcelain', capture=True).stdout.strip():
        for field, label in [('user.name', 'Git 作者姓名'), ('user.email', 'Git 作者邮箱')]:
            if git('config', '--get', field, capture=True, check=False).returncode:
                value = input(f'请输入{label}（仅配置此仓库）：').strip()
                if not value:
                    raise RuntimeError('作者信息不能为空。')
                git('config', '--local', field, value)
        message = input('提交说明（直接回车使用日期）：').strip()
        message = message or f'Update notes {datetime.datetime.now():%Y-%m-%d %H:%M}'
        git('add', '--all')
        diff = git('diff', '--cached', '--quiet', check=False)
        if diff.returncode == 1:
            git('commit', '-m', message)
        elif diff.returncode != 0:
            raise RuntimeError('无法检查暂存区，已停止。')
    else:
        print('没有文件变更，将尝试推送已有提交。')
    git('push', '-u', 'origin', 'main')
    print('\n推送成功。请在 GitHub Actions 查看部署结果；推送成功不代表 Pages 已部署成功。')
    print('首次部署请在仓库 Settings → Pages → Source 选择 GitHub Actions。')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError) as exc:
        print(f'\n操作失败：{exc}', file=sys.stderr)
        print('请根据上方错误处理后重试。脚本不会强制推送或自动拉取、合并；已完成的本地提交会保留。', file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print('\n已中止。')
        sys.exit(1)
