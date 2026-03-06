# Web Builder + Builds Dashboard Task

## Scope
- Add a `web_builder` skill to create/edit/list generated websites.
- Add a Builds tab in the dashboard.
- Serve generated website files from `websites/<name>/`.
- Expose the new tools in the system prompt.

## Implementation Plan
1. Create `skills/web_builder.py` with `web_build`, `web_edit`, `web_list` (and optional `web_delete`) tool handlers.
2. Add dashboard navigation link to `/builds`.
3. Add `/builds` page to list generated projects.
4. Add `/builds/<name>/` and `/builds/<name>/<path:filename>` serving routes.
5. Update `config.py` prompt tool list with web-builder tools.
6. Validate with compile checks and route smoke tests.

## Status
- [x] Skill file implemented in `skills/web_builder.py`.
- [x] Builds tab and page implemented in `dashboard.py`.
- [x] Static serving routes implemented in `dashboard.py`.
- [x] Prompt/tool docs updated in `config.py`.
- [x] Added route hardening for build-name/path traversal checks.
- [x] Verified with `python -m py_compile` and Flask test-client smoke tests.
