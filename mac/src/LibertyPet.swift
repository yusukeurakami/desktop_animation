import AppKit

let rootURL = URL(fileURLWithPath: CommandLine.arguments[0])
    .deletingLastPathComponent()
    .deletingLastPathComponent()
let framesURL = rootURL.appendingPathComponent("assets/frames", isDirectory: true)

final class PetView: NSImageView {
    var dragStart: NSPoint?
    var didDrag = false
    var onClick: (() -> Void)?
    var onDoubleClick: (() -> Void)?
    var onClose: (() -> Void)?

    override var acceptsFirstResponder: Bool { true }

    override func mouseDown(with event: NSEvent) {
        if event.clickCount >= 2 {
            onDoubleClick?()
            return
        }
        dragStart = event.locationInWindow
        didDrag = false
    }

    override func mouseDragged(with event: NSEvent) {
        guard let window, let dragStart else { return }
        didDrag = true
        let mouse = NSEvent.mouseLocation
        window.setFrameOrigin(NSPoint(x: mouse.x - dragStart.x, y: mouse.y - dragStart.y))
    }

    override func mouseUp(with event: NSEvent) {
        if !didDrag && event.clickCount == 1 {
            onClick?()
        }
        dragStart = nil
        didDrag = false
    }

    override func rightMouseDown(with event: NSEvent) {
        onClose?()
    }

    override func keyDown(with event: NSEvent) {
        if event.charactersIgnoringModifiers == "q" || event.keyCode == 53 {
            onClose?()
        } else {
            super.keyDown(with: event)
        }
    }
}

final class LibertyPetApp: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var view: PetView!
    var frames: [String: [NSImage]] = [:]
    var state = "idle"
    var direction = 1
    var frameIndex = 0
    var stateTicks = 0
    var timer: Timer?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        loadFrames()
        createWindow()
        chooseNextState()
        timer = Timer.scheduledTimer(withTimeInterval: 0.095, repeats: true) { [weak self] _ in
            self?.tick()
        }
    }

    func loadFrames() {
        let states = ["idle", "idle_left", "run", "run_left", "eat", "eat_left", "pet", "pet_left", "sleep", "sleep_left"]
        for state in states {
            let folder = framesURL.appendingPathComponent(state, isDirectory: true)
            let urls = (try? FileManager.default.contentsOfDirectory(
                at: folder,
                includingPropertiesForKeys: nil
            ))?.filter { $0.pathExtension.lowercased() == "png" }.sorted { $0.lastPathComponent < $1.lastPathComponent } ?? []

            let images = urls.compactMap { NSImage(contentsOf: $0) }
            if images.isEmpty {
                fatalError("No frames found for \(state) at \(folder.path)")
            }
            frames[state] = images
        }
    }

    func createWindow() {
        guard let first = frames["idle"]?.first else {
            fatalError("Missing idle frame")
        }
        let size = first.size
        let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1280, height: 800)
        let startX = screen.midX - size.width / 2
        let startY = screen.minY + 24

        window = NSWindow(
            contentRect: NSRect(x: startX, y: startY, width: size.width, height: size.height),
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = false
        window.level = .floating
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        window.ignoresMouseEvents = false

        view = PetView(frame: NSRect(origin: .zero, size: size))
        view.imageScaling = .scaleNone
        view.imageAlignment = .alignCenter
        view.image = first
        view.wantsLayer = true
        view.layer?.backgroundColor = NSColor.clear.cgColor
        view.onClick = { [weak self] in self?.setState("pet", ticks: 26) }
        view.onDoubleClick = { [weak self] in self?.setState("eat", ticks: 34) }
        view.onClose = { NSApp.terminate(nil) }
        window.contentView = view
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: false)
    }

    func stateName() -> String {
        switch state {
        case "run":
            return direction < 0 ? "run_left" : "run"
        case "eat":
            return direction < 0 ? "eat_left" : "eat"
        case "sleep":
            return direction < 0 ? "sleep_left" : "sleep"
        case "pet":
            return direction < 0 ? "pet_left" : "pet"
        default:
            return direction < 0 ? "idle_left" : "idle"
        }
    }

    func setState(_ next: String, ticks: Int? = nil) {
        state = next
        frameIndex = 0
        if let ticks {
            stateTicks = ticks
            return
        }
        switch next {
        case "run":
            stateTicks = Int.random(in: 55...120)
        case "eat":
            stateTicks = Int.random(in: 30...46)
        case "sleep":
            stateTicks = Int.random(in: 45...80)
        case "pet":
            stateTicks = Int.random(in: 20...32)
        default:
            stateTicks = Int.random(in: 15...35)
        }
    }

    func chooseNextState() {
        let roll = Double.random(in: 0..<1)
        if roll < 0.58 {
            setState("run")
        } else if roll < 0.82 {
            setState("idle")
        } else if roll < 0.95 {
            setState("eat")
        } else {
            setState("sleep")
        }
    }

    func moveIfNeeded() {
        guard state == "run", let screen = window.screen?.visibleFrame ?? NSScreen.main?.visibleFrame else {
            return
        }
        var frame = window.frame
        frame.origin.x += CGFloat(direction * 7)
        frame.origin.y += CGFloat([-1, 0, 0, 1].randomElement() ?? 0)
        frame.origin.y = min(max(screen.minY + 6, frame.origin.y), screen.maxY - frame.height - 6)

        let leftEdge = screen.minX - frame.width / 3
        let rightEdge = screen.maxX - frame.width + frame.width / 3
        if frame.origin.x <= leftEdge {
            frame.origin.x = leftEdge
            direction = 1
        } else if frame.origin.x >= rightEdge {
            frame.origin.x = rightEdge
            direction = -1
        }
        window.setFrameOrigin(frame.origin)
    }

    func tick() {
        let key = stateName()
        guard let images = frames[key], !images.isEmpty else {
            return
        }
        view.image = images[frameIndex % images.count]
        frameIndex += 1
        moveIfNeeded()
        stateTicks -= 1
        if stateTicks <= 0 {
            chooseNextState()
        }
    }
}

let app = NSApplication.shared
let delegate = LibertyPetApp()
app.delegate = delegate
app.run()
