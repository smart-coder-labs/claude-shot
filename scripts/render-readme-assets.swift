// Genera arte de portada y detalles a partir de una captura REAL, nunca UI ficticia.
// Uso: swift render-readme-assets.swift <repo>. No toma capturas ni controla apps.
import AppKit
import Foundation
let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let directory = root.appendingPathComponent(".github/assets", isDirectory: true)
let source = directory.appendingPathComponent("claude-shot-popup.png")
guard let screenshot = NSImage(contentsOf: source) else { fatalError("Falta la captura real del popup") }
func save(_ image: NSImage, to url: URL) throws {
    guard let tiff = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff),
          let png = bitmap.representation(using: .png, properties: [:]) else { fatalError("PNG no disponible") }
    try png.write(to: url, options: .atomic)
}
// Re-encode para no publicar metadatos del archivo de captura original.
try save(screenshot, to: source)
func text(_ value: String, x: CGFloat, y: CGFloat, size: CGFloat, weight: NSFont.Weight = .regular, color: NSColor) {
    (value as NSString).draw(at: NSPoint(x: x, y: y), withAttributes: [.font: NSFont.systemFont(ofSize: size, weight: weight), .foregroundColor: color])
}
let card = NSImage(size: NSSize(width: 1280, height: 640))
card.lockFocus()
NSColor(calibratedRed: 0.035, green: 0.065, blue: 0.10, alpha: 1).setFill()
NSBezierPath(rect: NSRect(x: 0, y: 0, width: 1280, height: 640)).fill()
let mint = NSColor(calibratedRed: 0.45, green: 0.94, blue: 0.78, alpha: 1)
text("CLAUDE SHOT", x: 72, y: 506, size: 58, weight: .bold, color: .white)
text("Screenshots → Claude Code", x: 75, y: 445, size: 32, weight: .medium, color: mint)
text("Native macOS · iTerm2 · No clipboard", x: 75, y: 390, size: 24, color: .lightGray)
text("⌘ ⌃ 7  →  Capture  →  Choose session  →  Enter", x: 75, y: 76, size: 26, weight: .medium, color: mint)
screenshot.draw(in: NSRect(x: 75, y: 160, width: 795, height: 217.5))
text("Real app screenshot · Local prototype", x: 75, y: 128, size: 17, color: .gray)
card.unlockFocus()
try save(card, to: directory.appendingPathComponent("social-preview.png"))
// Detalle del selector de sesión de la misma captura, recorte sin alterar el contenido.
let detail = NSImage(size: NSSize(width: 500, height: 30))
detail.lockFocus()
screenshot.draw(in: NSRect(x: 0, y: 0, width: 500, height: 30),
                from: NSRect(x: 15, y: 70, width: 500, height: 30), operation: .copy, fraction: 1)
detail.unlockFocus()
try save(detail, to: directory.appendingPathComponent("session-selector-detail.png"))
