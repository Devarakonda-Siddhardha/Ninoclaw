"""
Self-update module for Ninoclaw
Pulls latest code from GitHub and restarts the bot
"""
import subprocess
import sys
import os


def get_current_version():
    """Get current git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__)
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def check_for_updates():
    """Check if there are new commits on origin/main. Returns (has_updates, log)"""
    try:
        cwd = os.path.dirname(__file__)
        subprocess.run(["git", "fetch", "origin"], capture_output=True, cwd=cwd)
        result = subprocess.run(
            ["git", "log", "HEAD..origin/main", "--oneline"],
            capture_output=True, text=True, cwd=cwd
        )
        new_commits = result.stdout.strip()
        return bool(new_commits), new_commits
    except Exception as e:
        return False, str(e)


def do_update():
    """
    Pull latest code, install new dependencies.
    Returns (success, message)
    """
    cwd = os.path.dirname(__file__)
    try:
        # Git pull
        pull = subprocess.run(
            ["git", "pull", "origin", "main"],
            capture_output=True, text=True, cwd=cwd
        )
        if pull.returncode != 0:
            return False, f"git pull failed:\n{pull.stderr}"

        pull_output = pull.stdout.strip()

        # Install any new dependencies
        req_file = os.path.join(cwd, "requirements.txt")
        if os.path.exists(req_file):
            pip = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", req_file, "-q"],
                capture_output=True, text=True
            )
            if pip.returncode != 0:
                return False, f"pip install failed:\n{pip.stderr}"

        return True, pull_output

    except Exception as e:
        return False, str(e)


def restart():
    """Restart the current process"""
    os.execv(sys.executable, [sys.executable] + sys.argv)
