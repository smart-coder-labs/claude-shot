import SwiftUI
import AppKit
import UniformTypeIdentifiers
import Carbon

struct Session: Codable, Identifiable {
    let sessionID: String
    let tty: String
    let pid: Int
    let started: String
    let tabTitle: String
    let tabID: String
    var id: String { sessionID }
    var label: String { "\(tabTitle.isEmpty ? "Sin título" : tabTitle) · \(tty) · PID \(pid)" }
    enum CodingKeys: String, CodingKey {
        case sessionID = "session_id", tty, pid, started
        case tabTitle = "tab_title", tabID = "tab_id"
    }
}

struct Reply: Decodable {
    let ok: Bool
    let error: String?
    let sessions: [Session]?
    let state: String?
    let operation: String?
    let imagePath: String?
    let imagePaths: [String]?
    enum CodingKeys: String, CodingKey {
        case ok, error, sessions, state, operation
        case imagePath = "image_path", imagePaths = "image_paths"
    }
}

final class Model: ObservableObject {
    static let shared = Model()
    @Published var sessions: [Session] = []
    @Published var selected = ""
    @Published var text = ""
    @Published var imagePath: String?
    @Published var imagePaths: [String] = []
    @Published var operation: String?
    @Published var busy = false
    @Published var status = "Selecciona una sesión local de Claude Code."
    @Published var hotKeyEnabled = false
    @Published var hotKeyStatus = "Registrando ⌘⌃7…"
    var openMainWindow: (() -> Void)?
    private var initialWindowHandled = false
    private var capturing = false
    private let root: URL?
    private var hotKey: EventHotKeyRef?
    private var batchHotKey: EventHotKeyRef?
    private var eventHandler: EventHandlerRef?

    init() {
        if let resource = Bundle.main.url(forResource: "repository-path", withExtension: "txt"),
           let path = try? String(contentsOf: resource, encoding: .utf8) {
            root = URL(fileURLWithPath: path.trimmingCharacters(in: .whitespacesAndNewlines), isDirectory: true)
        } else { root = nil }
    }

    var currentSession: Session? { sessions.first { $0.id == selected } }
    var canSend: Bool { !busy && operation != nil && !imagePaths.isEmpty && currentSession != nil }

    // Protocolo de una petición JSON por proceso. Sin shell ni interpolación de texto.
    private func request(_ payload: [String: Any], completion: @escaping (Reply?) -> Void) {
        guard let root = root, JSONSerialization.isValidJSONObject(payload),
              let data = try? JSONSerialization.data(withJSONObject: payload) else {
            busy = false
            status = "No se encontró el repositorio. Vuelve a construir la app."
            completion(nil)
            return
        }
        guard data.count <= 65536 else {
            busy = false
            status = "Texto demasiado largo. Usa una sola línea de hasta 8000 caracteres."
            completion(nil)
            return
        }
        busy = true
        DispatchQueue.global(qos: .userInitiated).async {
            let task = Process()
            task.executableURL = root.appendingPathComponent(".venv/bin/python")
            task.arguments = ["-B", root.appendingPathComponent("scripts/claude-shot.py").path, "desktop"]
            task.currentDirectoryURL = root
            var environment = ProcessInfo.processInfo.environment
            // Finder no hereda necesariamente el PATH de la terminal.
            environment["PATH"] = "/Applications/iTerm.app/Contents/Resources/utilities:/usr/bin:/bin:/usr/sbin:/sbin:" + (environment["PATH"] ?? "")
            task.environment = environment
            let input = Pipe(), output = Pipe()
            task.standardInput = input
            task.standardOutput = output
            // No volcar posibles datos de SDK o prompts a Console; el puente devuelve errores JSON.
            task.standardError = FileHandle.nullDevice
            do {
                try task.run()
                input.fileHandleForWriting.write(data)
                try? input.fileHandleForWriting.close()
                let bytes = output.fileHandleForReading.readDataToEndOfFile()
                task.waitUntilExit()
                let reply = try? JSONDecoder().decode(Reply.self, from: bytes)
                DispatchQueue.main.async {
                    self.busy = false
                    if reply == nil {
                        self.status = "El controlador terminó sin respuesta válida. Comprueba el panel; no reintentes a ciegas."
                    } else if let error = reply?.error { self.status = error }
                    completion(reply)
                }
            } catch {
                DispatchQueue.main.async {
                    self.busy = false
                    self.status = "No se pudo ejecutar el controlador. Revisa .venv y reconstruye la app."
                    completion(nil)
                }
            }
        }
    }

    func refresh() {
        guard !busy else { return }
        request(["action": "sessions"]) { reply in
            guard let reply = reply, reply.ok else { return }
            let previous = self.currentSession
            self.sessions = reply.sessions ?? []
            if !self.sessions.contains(where: { $0.id == self.selected }) { self.selected = "" }
            if self.operation != nil, let previous = previous,
               let current = self.currentSession,
               (previous.pid != current.pid || previous.tty != current.tty || previous.started != current.started) {
                self.selected = "" // Reinicio de proceso: exigir selección explícita, nunca sustituir destino.
            }
            if self.sessions.count == 1 && self.operation == nil { self.selected = self.sessions[0].id }
            self.status = self.sessions.isEmpty ? "Sin Claude local. Ábrelo en iTerm2 y pulsa Actualizar." :
                (self.operation == nil ? "⌘⌃7 captura una región." : "Enter envía · Esc descarta · Claude listo y prompt vacío")
        }
    }

    func capture() {
        guard !busy else { return }
        if operation != nil {
            status = "Captura pendiente · ⌘⌃⇧7 añade al lote · Enter envía"
            showWindow()
            return
        }
        addCapture()
    }

    func addCapture() {
        if busy {
            if !capturing { showWindow() }
            return
        }
        if imagePaths.count >= 6 {
            status = "Máximo 6 capturas. Quita una o envía el lote."
            showWindow()
            return
        }
        busy = true
        capturing = true
        status = "Selecciona una región; Esc cancela."
        NSApplication.shared.hide(nil)
        // Dejar que la ventana desaparezca antes de mostrar el selector nativo.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
            self.prepare(["action": "capture"])
        }
    }

    func pickImage() {
        guard !busy, imagePaths.count < 6 else { showWindow(); return }
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.png]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        if panel.runModal() == .OK, let url = panel.url {
            prepare(["action": "prepare", "path": url.path])
        }
    }

    private func prepare(_ payload: [String: Any]) {
        var payload = payload
        if let op = operation { payload["operation"] = op }
        request(payload) { reply in
            self.capturing = false
            guard let reply = reply, reply.ok else {
                if reply == nil { self.clearPrepared() }
                else if let state = reply?.state, state != "preparing" { self.clearPrepared() }
                else if let paths = reply?.imagePaths { self.imagePaths = paths; self.imagePath = paths.last }
                self.showWindow()
                return
            }
            if reply.state == "cancelled" {
                self.status = "Captura cancelada; no se envió nada."
                return
            }
            guard let op = reply.operation, let paths = reply.imagePaths, !paths.isEmpty else {
                self.status = "No se pudo preparar la captura. No se enviará."
                self.showWindow()
                return
            }
            if self.operation != op { self.text = "" }
            self.operation = op
            self.imagePaths = paths
            self.imagePath = paths.last
            if reply.state == "capture_cancelled" {
                self.status = "Selección cancelada; se conservan \(paths.count) capturas."
                self.showWindow()
                return
            }
            self.status = "Enter envía · Esc descarta · Claude listo y prompt vacío"
            self.showWindow()
            self.refresh()
        }
    }

    func submit() {
        guard canSend, let target = currentSession, let op = operation,
              let encoded = try? JSONEncoder().encode(target),
              let targetJSON = try? JSONSerialization.jsonObject(with: encoded) else { return }
        if text.unicodeScalars.count > 8000 || text.unicodeScalars.contains(where: {
            $0.value < 32 || (127...159).contains($0.value) || $0.value == 0x2028 || $0.value == 0x2029
        }) {
            status = "Usa texto de una sola línea, hasta 8000 caracteres y sin controles."
            return
        }
        status = "Enviando a \(target.tabTitle)… No escribas en ese panel."
        request(["action": "send", "operation": op, "target": targetJSON, "text": text]) { reply in
            if let reply = reply, reply.ok, reply.state == "submitted" {
                self.clearPrepared()
                self.text = ""
                self.status = "Enviado a iTerm2. Comprueba la respuesta de Claude."
                NSApplication.shared.hide(nil)
            } else if reply == nil || reply?.state != "preparing" {
                // No permitir reenviar una operación intentada o de resultado desconocido.
                self.clearPrepared()
                self.status = "Entrega no confirmada (\(reply?.state ?? "unknown")). Comprueba el panel; no reintentes a ciegas. Operación: \(op)"
            }
        }
    }

    private func clearPrepared() { operation = nil; imagePaths = []; imagePath = nil }

    func removeImage(_ index: Int) {
        guard !busy, let op = operation else { return }
        request(["action": "remove", "operation": op, "index": index]) { reply in
            guard let reply = reply, reply.ok else {
                if reply == nil { self.clearPrepared() }
                else if let state = reply?.state, state != "preparing" { self.clearPrepared() }
                else if let paths = reply?.imagePaths { self.imagePaths = paths; self.imagePath = paths.last }
                return
            }
            if reply.state == "cancelled" {
                self.clearPrepared()
                self.text = ""
                self.status = "Lote descartado; ⌘⌃7 inicia otro."
            } else if let paths = reply.imagePaths {
                self.imagePaths = paths
                self.imagePath = paths.last
                self.status = "Enter envía el lote · Esc descarta todo"
            }
        }
    }

    private func discardOperation(_ op: String, completion: (() -> Void)? = nil) {
        request(["action": "cancel", "operation": op]) { reply in
            if reply?.ok == true {
                self.clearPrepared()
                self.status = "Imagen descartada; terminal intacta."
            }
            completion?()
        }
    }

    func discard() {
        guard !busy, let op = operation else { return }
        discardOperation(op)
    }

    func dismissPopup() {
        guard !busy else { return }
        if let op = operation {
            discardOperation(op) {
                if self.operation == nil { NSApplication.shared.hide(nil) }
            }
        } else {
            NSApplication.shared.hide(nil)
        }
    }

    func windowAppeared() {
        if !initialWindowHandled {
            initialWindowHandled = true
            if operation == nil { NSApplication.shared.hide(nil) }
        }
        refresh()
    }

    func revealImage() {
        if let path = imagePath { NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: path)]) }
    }

    func showWindow() {
        // SwiftUI puede destruir la ventana al cerrarla: recrearla por ID de escena,
        // no depender únicamente de encontrar una NSWindow por su título.
        openMainWindow?()
        NSApplication.shared.unhide(nil)
        NSApplication.shared.activate(ignoringOtherApps: true)
        DispatchQueue.main.async {
            if let window = NSApplication.shared.windows.first(where: { $0.title == "Claude Shot" }) {
                window.level = .floating
                window.center()
                window.makeKeyAndOrderFront(nil)
            }
        }
    }

    func quitDecision() -> NSApplication.TerminateReply {
        if busy {
            status = "Hay una operación en curso. Espera a que termine antes de salir."
            showWindow()
            return .terminateCancel
        }
        if let op = operation {
            discardOperation(op) {
                let canQuit = self.operation == nil
                NSApplication.shared.reply(toApplicationShouldTerminate: canQuit)
                if !canQuit { self.showWindow() }
            }
            return .terminateLater
        }
        return .terminateNow
    }

    private func recordHotKey(_ event: String, code: OSStatus) {
        // Diagnóstico mínimo en el repositorio: no captura teclas ni contenido.
        guard let root = root else { return }
        let directory = root.appendingPathComponent(".claude-shot", isDirectory: true)
        do {
            let manager = FileManager.default
            if !manager.fileExists(atPath: directory.path) {
                try manager.createDirectory(at: directory, withIntermediateDirectories: false,
                                            attributes: [.posixPermissions: 0o700])
            }
            let attrs = try manager.attributesOfItem(atPath: directory.path)
            guard attrs[.type] as? FileAttributeType == .typeDirectory,
                  let permissions = attrs[.posixPermissions] as? NSNumber,
                  permissions.intValue & 0o077 == 0,
                  (attrs[.ownerAccountID] as? NSNumber)?.uint32Value == getuid() else { return }
            let data = try JSONSerialization.data(withJSONObject: [
                "event": event, "code": Int(code), "pid": Int(ProcessInfo.processInfo.processIdentifier)
            ])
            let file = directory.appendingPathComponent("hotkey-status.json")
            try data.write(to: file, options: .atomic)
            try manager.setAttributes([.posixPermissions: 0o600], ofItemAtPath: file.path)
        } catch { /* Un fallo de diagnóstico no cambia el registro del atajo. */ }
    }

    func hotKeyPressed(batch: Bool) {
        recordHotKey(batch ? "batch_pressed" : "pressed", code: noErr)
        if batch { addCapture() } else { capture() }
    }

    // Activado al arrancar por petición del usuario, sin preferencias del sistema.
    func toggleHotKey() {
        if hotKey != nil || batchHotKey != nil {
            func unregister(_ ref: inout EventHotKeyRef?) -> OSStatus {
                guard let key = ref else { return noErr }
                let result = UnregisterEventHotKey(key)
                if result == noErr { ref = nil }
                return result
            }
            let singleResult = unregister(&hotKey)
            let batchResult = unregister(&batchHotKey)
            hotKeyEnabled = hotKey != nil || batchHotKey != nil
            hotKeyStatus = hotKeyEnabled ? "Algún atajo sigue activo; reintenta desactivar." : "Atajos desactivados hasta el próximo arranque."
            recordHotKey(hotKeyEnabled ? "disable_failed" : "disabled", code: singleResult != noErr ? singleResult : batchResult)
        } else {
            enableHotKey()
        }
    }

    func enableHotKey() {
        guard !hotKeyEnabled else { return }
        if eventHandler == nil {
            var type = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
            let result = InstallEventHandler(GetApplicationEventTarget(), { _, event, _ in
                guard let event = event else { return OSStatus(eventNotHandledErr) }
                var identifier = EventHotKeyID()
                let result = GetEventParameter(event, EventParamName(kEventParamDirectObject),
                    EventParamType(typeEventHotKeyID), nil, MemoryLayout<EventHotKeyID>.size, nil, &identifier)
                guard result == noErr, identifier.signature == 0x43534854,
                      identifier.id == 1 || identifier.id == 2 else { return OSStatus(eventNotHandledErr) }
                let batch = identifier.id == 2
                DispatchQueue.main.async { Model.shared.hotKeyPressed(batch: batch) }
                return noErr
            }, 1, &type, nil, &eventHandler)
            guard result == noErr else {
                hotKeyStatus = "No se pudo instalar el manejador de ⌘⌃7 (código \(result))."
                recordHotKey("handler_failed", code: result)
                return
            }
        }
        let result = RegisterEventHotKey(UInt32(kVK_ANSI_7), UInt32(cmdKey | controlKey),
                                        EventHotKeyID(signature: 0x43534854, id: 1),
                                        GetApplicationEventTarget(), 0, &hotKey)
        var statusCode = result
        if result == noErr {
            statusCode = RegisterEventHotKey(UInt32(kVK_ANSI_7), UInt32(cmdKey | controlKey | shiftKey),
                EventHotKeyID(signature: 0x43534854, id: 2), GetApplicationEventTarget(), 0, &batchHotKey)
            if statusCode != noErr, let key = hotKey {
                if UnregisterEventHotKey(key) == noErr { hotKey = nil }
            }
        }
        hotKeyEnabled = hotKey != nil || batchHotKey != nil
        let complete = result == noErr && statusCode == noErr
        recordHotKey(complete ? "registered" : "registration_failed", code: statusCode)
        hotKeyStatus = complete ? "⌘⌃7 individual · ⌘⌃⇧7 lote · Enter envía y cierra" :
            "No se pudieron activar ambos atajos (código \(statusCode)); desactiva y reintenta desde el menú."
    }
}

struct ContentView: View {
    @ObservedObject var model = Model.shared
    @FocusState private var textFocused: Bool
    @Environment(\.openWindow) private var openWindow
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Picker("Sesión de Claude", selection: $model.selected) {
                    Text("Selecciona Claude…").tag("")
                    ForEach(model.sessions) { session in Text(session.label).tag(session.id) }
                }.labelsHidden().disabled(model.busy)
                Button(action: model.refresh) { Image(systemName: "arrow.clockwise") }
                    .buttonStyle(.borderless).help("Actualizar sesiones").disabled(model.busy)
            }
            if !model.imagePaths.isEmpty {
                HStack(spacing: 6) {
                    Text("\(model.imagePaths.count)/6 capturas").font(.caption).foregroundStyle(.secondary)
                    ForEach(Array(model.imagePaths.indices), id: \.self) { index in
                        Button("\(index + 1) ×") { model.removeImage(index) }
                            .buttonStyle(.borderless).help("Quitar captura \(index + 1)").disabled(model.busy)
                    }
                    Spacer()
                    Button(action: model.addCapture) { Image(systemName: "plus") }
                        .buttonStyle(.borderless).help("Añadir al lote · ⌘⌃⇧7")
                        .disabled(model.busy || model.imagePaths.count >= 6)
                }
            }
            HStack(spacing: 8) {
                TextField("Texto opcional — Enter envía el lote", text: $model.text)
                    .textFieldStyle(.roundedBorder).focused($textFocused)
                    .onSubmit { model.submit() }.disabled(model.busy || model.operation == nil)
                Button(action: model.submit) { Image(systemName: "paperplane.fill") }
                    .buttonStyle(.borderless).help("Enviar").disabled(!model.canSend)
            }
            HStack(spacing: 6) {
                if model.busy { ProgressView().controlSize(.mini) }
                Text(model.status)
                    .font(.caption).foregroundStyle(.secondary).lineLimit(2)
            }
            if !model.hotKeyEnabled {
                Text(model.hotKeyStatus).font(.caption).foregroundStyle(.secondary).lineLimit(2)
            }
        }
        .padding(16).frame(width: 530)
        .onAppear {
            model.openMainWindow = { openWindow(id: "main") }
            model.windowAppeared()
            textFocused = model.operation != nil
        }
        .onChange(of: model.operation) { _, value in if value != nil { textFocused = true } }
        .onChange(of: model.busy) { _, value in
            if !value && model.operation != nil { textFocused = true }
        }
        .onExitCommand { model.dismissPopup() }
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    private var statusItem: NSStatusItem?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApplication.shared.setActivationPolicy(.accessory)
        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        item.button?.image = NSImage(systemSymbolName: "viewfinder", accessibilityDescription: "Claude Shot")
        item.button?.toolTip = "Claude Shot · ⌘⌃7 captura"
        let menu = NSMenu()
        menu.delegate = self
        item.menu = menu
        statusItem = item
        Model.shared.enableHotKey()
    }

    func menuNeedsUpdate(_ menu: NSMenu) {
        let model = Model.shared
        menu.removeAllItems()
        func add(_ title: String, _ action: Selector, enabled: Bool = true) {
            let item = NSMenuItem(title: title, action: action, keyEquivalent: "")
            item.target = self
            item.isEnabled = enabled
            menu.addItem(item)
        }
        menu.autoenablesItems = false
        add("Capturar región  ⌘⌃7", #selector(captureRegion), enabled: !model.busy)
        add("Añadir al lote  ⌘⌃⇧7", #selector(captureBatch), enabled: !model.busy && model.imagePaths.count < 6)
        add("Mostrar popup", #selector(showPopup))
        add("Elegir PNG…", #selector(choosePNG), enabled: !model.busy && model.imagePaths.count < 6)
        add("Ver captura en Finder", #selector(revealCapture), enabled: model.operation != nil)
        menu.addItem(.separator())
        let status = NSMenuItem(title: model.hotKeyStatus, action: nil, keyEquivalent: "")
        status.isEnabled = false
        menu.addItem(status)
        add(model.hotKeyEnabled ? "Desactivar atajos" : "Reintentar activar atajos", #selector(toggleShortcut))
        menu.addItem(.separator())
        let quit = NSMenuItem(title: "Salir de Claude Shot", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "")
        quit.target = NSApplication.shared
        menu.addItem(quit)
    }

    @objc private func captureRegion() { Model.shared.capture() }
    @objc private func captureBatch() { Model.shared.addCapture() }
    @objc private func showPopup() { Model.shared.showWindow() }
    @objc private func choosePNG() { Model.shared.pickImage() }
    @objc private func revealCapture() { Model.shared.revealImage() }
    @objc private func toggleShortcut() { Model.shared.toggleHotKey() }
    func applicationWillTerminate(_ notification: Notification) {
        if Model.shared.hotKeyEnabled { Model.shared.toggleHotKey() }
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        false // Mantener el atajo mientras la app siga ejecutándose.
    }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        Model.shared.quitDecision()
    }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        Model.shared.showWindow()
        return true
    }
}

@main
struct ClaudeShotApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var delegate
    @ObservedObject var model = Model.shared
    var body: some Scene {
        Window("Claude Shot", id: "main") { ContentView() }
            .defaultSize(width: 530, height: 150)
            .windowStyle(.hiddenTitleBar)
            .windowResizability(.contentSize)
            .commands {
                CommandGroup(after: .appInfo) {
                    Button(model.hotKeyEnabled ? "Desactivar atajos globales" : "Activar atajos globales") {
                        model.toggleHotKey()
                    }
                }
            }
    }
}
