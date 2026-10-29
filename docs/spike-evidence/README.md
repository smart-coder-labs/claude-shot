# Public spike evidence

The checked-in PNGs and expected color orders are synthetic fixtures created for P1, not desktop screenshots. They contain no private screen content. Real README screenshots live in `.github/assets/` with their own provenance notes.

Runtime receipts, message text containing local paths, and downloaded copies of third-party documentation remain ignored on the development Mac. They are not needed to run the prototype or tests and are not redistributed as project source.

Official references consulted:

- https://code.claude.com/docs/en/common-workflows.md
- https://code.claude.com/docs/en/hooks.md
- https://code.claude.com/docs/en/interactive-mode.md
- https://code.claude.com/docs/en/cli-reference.md
- https://code.claude.com/docs/en/settings.md
- https://iterm2.com/python-api/session.html
- https://iterm2.com/python-api/keyboard.html
- https://github.com/gnachman/iTerm2/blob/master/it2cli/Sources/it2core/Commands/SessionCommand.swift
- https://github.com/gnachman/iTerm2/blob/master/sources/API/iTermAPIHelper.m

To reproduce a documentation lookup, use `curl -fLsS --max-time 25 URL` and record the version/date. The web references change independently of installed versions; documentation alone does not prove runtime behavior. Consult `../spike-results.md` for real experiments, accepted scope, and remaining limitations.
