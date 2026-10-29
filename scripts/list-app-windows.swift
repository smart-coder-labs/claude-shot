// Solo enumera IDs de ventanas de Claude Shot; no lee otras ventanas ni captura.
import Foundation
import CoreGraphics
let pid = CommandLine.arguments.count > 1 ? Int32(CommandLine.arguments[1]) : nil
let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
for window in windows {
    guard let owner = window[kCGWindowOwnerPID as String] as? NSNumber,
          owner.int32Value == pid,
          window[kCGWindowName as String] as? String == "Claude Shot",
          let number = window[kCGWindowNumber as String] as? Int else { continue }
    print(number)
}
