# GitHub discoverability and publication

## Implemented

- English README with a descriptive banner, feature/limits tables, quick start, real screenshot, Mermaid architecture, accessible image descriptions, and a Spanish guide.
- Natural search terms: macOS screenshot tool, Claude Code, iTerm2, screen capture, menu bar app, SwiftUI. No fabricated capabilities, keyword stuffing, or promise of search ranking.
- Repository description and 12 GitHub topics applied through the official API and verified. Desired values: `.github/repository-metadata.json`.
- CI workflow for simulated tests, documentation/asset checks, and native build verification. The badge reports GitHub's real workflow status, not a hard-coded passing claim.
- Issue form and contribution guide, with privacy constraints for screenshots and runtime data.
- Real app PNG, derived selector crop, original SVG banner, and a social card in `.github/assets/`, each with provenance notes.

## Reproducible updates

```sh
python3 -B scripts/update-github-metadata.py          # Preview only
python3 -B scripts/update-github-metadata.py --apply  # Explicit remote change
python3 -B scripts/check-docs.py                     # Local links/images only
```

The metadata updater uses a supplied GH_TOKEN/GITHUB_TOKEN or the already-configured non-interactive Git credential helper. It does not print/save tokens or put them in process arguments; HTTPS certificate verification stays enabled. No GitHub CLI installation or system configuration change is required.

## GitHub social preview

`social-preview.png` is ready to select in repository Settings → General → Social preview. The file is published in the repository, **but the repository's custom social-preview setting is not configured by the API updater**. GitHub's supported repository REST API does not expose that upload setting. Do not claim that committing an image automatically installs it as the repository's Open Graph image.

## Boundaries

There is no dedicated website, Pages deployment, sitemap, or custom domain. Adding SEO meta tags to a Markdown README would not configure GitHub's page metadata. Search indexing and ranking are controlled by the hosting/search services and cannot be guaranteed.

A software license has not been selected by the owner. Do not add a license badge, claim MIT, or describe the code as legally open source without that decision. This does not prevent publishing the authorized source changes, but reuse rights remain unspecified.

Manual GUI permission/multi-monitor checks, unattended-readiness guarantees, and SSH feasibility remain separate product work, not documentation or SEO tasks. See the explicit acceptance checklists and spike gate instead of treating publication as technical validation.
