
import Foundation
import os

extension Logger {
    static let cache = Logger(subsystem: subsystem, category: "cache")
    
    private static let subsystem = Bundle.main.bundleIdentifier ?? "com.svgr.app"
}
