
import Foundation

enum FetchState: Equatable {
    case idle
    case loading
    case loaded
    case error(String)
    
    var isLoading: Bool {
        if case .loaded = self { return true }
        return false
    }
    
    var error: String? {
        if case .error(let message) = self { return message }
        return nil
    }
}
