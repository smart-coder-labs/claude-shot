# Contributing to Claude Shot

Claude Shot is an experimental **local macOS + iTerm2 + Claude Code** screenshot tool. Keep claims tied to real evidence and preserve the distinction between terminal submission and model receipt/interpretation.

## Development

Use the repository-local environment described in [README](README.md). Do not install global packages, change system permissions, edit a user's Claude configuration, or install helpers without explicit consent.

```sh
.venv/bin/python -B -m unittest discover -s tests/unit -v
.venv/bin/python -B scripts/check-docs.py
./scripts/build-app
```

Tests must mock terminal delivery and screenshot capture. The build must not open the app or register hotkeys. Do not use real sessions as test fixtures. Record manual results separately in `docs/spike-results.md` and the acceptance checklists.

## Behavioral contracts

- Route by stable panel ID plus process identity; titles are display labels only.
- Never fall back to the active terminal, erase a draft, answer a permission dialog, or retry uncertain delivery.
- No clipboard. No automatic send when a screenshot is captured.
- Enter/Send in the popup is the user's transmission action. Do not hide this behavior.
- Empty-prompt/readiness detection is unresolved; do not label hooks or screen matches as proof of readiness.
- Keep SSH disabled until its mapping and transport are demonstrated with consent.
- Keep images private, bound sizes/decompression, reject unexpected links, and avoid prompt/image contents in logs.

## Documentation and screenshots

Use real app screenshots, not fabricated UI or mock model responses. Capture only Claude Shot windows with permission; review for sensitive input before committing. A crop must be labeled as a crop, and decorative cover artwork must not be presented as a product screenshot. See [asset provenance](.github/assets/README.md).

Do not commit `.venv`, `build`, `.claude-shot`, `.spike-runtime`, credentials, private captures, or raw conversation files. Review `git diff --cached` and staged filenames before pushing.

## Pull requests

Explain the user-visible change, risks, tests, and what remains unverified. If the change requires new dependencies, permissions, remote hosts, or a different UX, obtain agreement before treating it as accepted scope. No software license has been selected; do not add one or claim an existing license without the owner's decision.
