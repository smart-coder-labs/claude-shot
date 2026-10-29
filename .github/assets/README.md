# README artwork and real screenshots

| File | Provenance |
| --- | --- |
| `claude-shot-banner.svg` | Original decorative cover artwork, not a screenshot or simulated UI. |
| `claude-shot-popup.png` | Real Claude Shot app-window capture, taken with the user's permission via macOS `screencapture -x -o -l <window-id>`. It shows the existing popup after a local send; no new message was sent to create it. |
| `session-selector-detail.png` | Crop of that same screenshot, not another application state. |
| `social-preview.png` | Decorative social card containing the real popup screenshot. Ready for manual selection as a GitHub social preview. |

Only the Claude Shot window was captured. No desktop, terminal conversation, permissions panel, or secret input is included. The visible tab title is from the synthetic-image experiment. The original image was reviewed and re-encoded before publication to avoid carrying incidental capture-file metadata. The app interface is currently Spanish.

These images are evidence of visible UI only, not proof that every GUI/permission/hotkey scenario works. Native capture/direct-hotkey flow still has its own acceptance checklist.

## Reproduce safely

With the user's permission, show the app popup from its menu. Do not send test messages just to create screenshots.

```sh
# Use the app PID only; the helper outputs IDs for Claude Shot windows, not other apps.
swiftc -module-cache-path "$PWD/build/module-cache" scripts/list-app-windows.swift -o build/list-app-windows
build/list-app-windows <ClaudeShot-PID>

# Review the target ID; capture only the named app window.
screencapture -x -o -l <window-id> .github/assets/claude-shot-popup.png

# Render original artwork/details from that reviewed real screenshot.
swiftc -module-cache-path "$PWD/build/module-cache" scripts/render-readme-assets.swift -o build/render-readme-assets
build/render-readme-assets "$PWD"
```

Do not substitute a full-desktop capture. If the popup contains private text, cancel publication and obtain a clean app state first. Never manufacture a model reply or claim a fabricated screenshot is a real one.
