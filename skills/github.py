import base64
import os
import requests

SKILL_INFO = {
    "name": "github",
    "description": "Interact with GitHub repos — create issues, list PRs, get repo info",
    "icon": "🐙",
    "version": "1.0",
    "requires_key": True,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "github_create_issue",
            "description": "Create a GitHub issue in a repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository in owner/repo format"},
                    "title": {"type": "string", "description": "Issue title"},
                    "body": {"type": "string", "description": "Issue body/description"},
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of label names to apply",
                    },
                },
                "required": ["repo", "title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_list_prs",
            "description": "List pull requests in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository in owner/repo format"},
                    "state": {
                        "type": "string",
                        "description": "PR state: open, closed, or all. Defaults to open.",
                    },
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_get_repo",
            "description": "Get repository info including stars, description, and latest commit",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository in owner/repo format"},
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_create_file",
            "description": "Create or update a file in a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository in owner/repo format"},
                    "path": {"type": "string", "description": "File path within the repository"},
                    "content": {"type": "string", "description": "File content (plain text)"},
                    "message": {"type": "string", "description": "Commit message"},
                    "branch": {
                        "type": "string",
                        "description": "Branch to commit to. Defaults to main.",
                    },
                },
                "required": ["repo", "path", "content", "message"],
            },
        },
    },
]

_BASE = "https://api.github.com"


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(url: str, params: dict = None):
    return requests.get(url, headers=_headers(), params=params, timeout=15)


def _post(url: str, payload: dict):
    return requests.post(url, headers=_headers(), json=payload, timeout=15)


def _put(url: str, payload: dict):
    return requests.put(url, headers=_headers(), json=payload, timeout=15)


def execute(tool_name: str, arguments: dict) -> str:
    try:
        if tool_name == "github_create_issue":
            return _create_issue(arguments)
        if tool_name == "github_list_prs":
            return _list_prs(arguments)
        if tool_name == "github_get_repo":
            return _get_repo(arguments)
        if tool_name == "github_create_file":
            return _create_file(arguments)
        return f"Unknown tool: {tool_name}"
    except requests.RequestException as e:
        return f"GitHub request error: {e}"
    except Exception as e:
        return f"Error: {e}"


def _create_issue(args: dict) -> str:
    repo = args.get("repo", "")
    title = args.get("title", "")
    if not repo or not title:
        return "Error: repo and title are required."
    payload = {"title": title}
    if args.get("body"):
        payload["body"] = args["body"]
    if args.get("labels"):
        payload["labels"] = args["labels"]
    resp = _post(f"{_BASE}/repos/{repo}/issues", payload)
    if resp.status_code == 201:
        data = resp.json()
        return f"Issue created: #{data['number']} — {data['title']}\n{data['html_url']}"
    return f"GitHub error {resp.status_code}: {resp.json().get('message', resp.text)}"


def _list_prs(args: dict) -> str:
    repo = args.get("repo", "")
    if not repo:
        return "Error: repo is required."
    state = args.get("state", "open")
    resp = _get(f"{_BASE}/repos/{repo}/pulls", params={"state": state, "per_page": 20})
    if resp.status_code != 200:
        return f"GitHub error {resp.status_code}: {resp.json().get('message', resp.text)}"
    prs = resp.json()
    if not prs:
        return f"No {state} pull requests found in {repo}."
    lines = [f"Pull requests ({state}) in {repo}:"]
    for pr in prs:
        lines.append(f"  #{pr['number']} [{pr['state']}] {pr['title']} — {pr['html_url']}")
    return "\n".join(lines)


def _get_repo(args: dict) -> str:
    repo = args.get("repo", "")
    if not repo:
        return "Error: repo is required."
    resp = _get(f"{_BASE}/repos/{repo}")
    if resp.status_code != 200:
        return f"GitHub error {resp.status_code}: {resp.json().get('message', resp.text)}"
    data = resp.json()

    # Fetch latest commit on default branch
    latest_commit = "N/A"
    branch = data.get("default_branch", "main")
    c_resp = _get(f"{_BASE}/repos/{repo}/commits/{branch}")
    if c_resp.status_code == 200:
        c = c_resp.json()
        sha = c.get("sha", "")[:7]
        msg = c.get("commit", {}).get("message", "").splitlines()[0]
        latest_commit = f"{sha} — {msg}"

    return (
        f"Repo: {data.get('full_name')}\n"
        f"Description: {data.get('description') or 'None'}\n"
        f"Stars: {data.get('stargazers_count', 0)}  Forks: {data.get('forks_count', 0)}\n"
        f"Language: {data.get('language') or 'N/A'}\n"
        f"Default branch: {branch}\n"
        f"Latest commit: {latest_commit}\n"
        f"URL: {data.get('html_url')}"
    )


def _create_file(args: dict) -> str:
    repo = args.get("repo", "")
    path = args.get("path", "")
    content = args.get("content", "")
    message = args.get("message", "")
    branch = args.get("branch", "main")
    if not all([repo, path, content, message]):
        return "Error: repo, path, content, and message are all required."

    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    payload = {"message": message, "content": encoded, "branch": branch}

    # Check if file exists to get its SHA (required for updates)
    existing = _get(f"{_BASE}/repos/{repo}/contents/{path}", params={"ref": branch})
    if existing.status_code == 200:
        payload["sha"] = existing.json().get("sha", "")

    resp = _put(f"{_BASE}/repos/{repo}/contents/{path}", payload)
    if resp.status_code in (200, 201):
        action = "updated" if resp.status_code == 200 else "created"
        data = resp.json()
        html_url = data.get("content", {}).get("html_url", "")
        return f"File {action}: {path} in {repo} on branch {branch}.\n{html_url}"
    return f"GitHub error {resp.status_code}: {resp.json().get('message', resp.text)}"
