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
        # Fetch latest from origin
        subprocess.run(["git", "fetch", "origin"], capture_output=True, cwd=cwd)
        # Check if current branch has commits behind origin/main
        result = subprocess.run(
            ["git", "log", "HEAD..origin/main", "--oneline"],
            capture_output=True, text=True, cwd=cwd
        )
        new_commits = result.stdout.strip()
        if new_commits:
            return True, new_commits

        # Also check if we're on main branch
        current_branch = get_current_branch()
        if current_branch != "main":
            return True, f"On branch '{current_branch}' instead of main. Switching to main for update."

        return False, "Up to date"
    except Exception as e:
        return False, str(e)


def get_current_branch():
    """Get current git branch name"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__)
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def do_update():
    """
    Pull latest code, install new dependencies.
    Returns (success, message)
    """
    cwd = os.path.dirname(__file__)
    try:
        # Check current branch and switch to main if needed
        current_branch = get_current_branch()
        if current_branch != "main":
            # Stash changes on current branch
            subprocess.run(
                ["git", "stash", "push", "-u", "-m", "auto-update-stash"],
                capture_output=True, cwd=cwd
            )
            # Switch to main branch
            checkout = subprocess.run(
                ["git", "checkout", "main"],
                capture_output=True, text=True, cwd=cwd
            )
            if checkout.returncode != 0:
                return False, f"Failed to switch to main branch:\n{checkout.stderr}"

        # Reset to clean state before pull
        subprocess.run(
            ["git", "reset", "--hard", "origin/main"],
            capture_output=True, cwd=cwd
        )

        # Pull latest from main
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
