
import Foundation
import SwiftUI

@Observable
final class LoginViewModel {
        
    private let steamService: SteamService
    
    var state: LoadingState<LoginResponse> = .idle
    var isAuthenticated: Bool = false
    var authError: String?
    
    var steamId: String? {
        Keychain.get(.steamId)
    }
    
    init(steamService: SteamService) {
        self.steamService = steamService
        self.isAuthenticated = Keychain.get(.steamId) != nil
    }
    
    func getLoginUrl() async {
        state = .loading
        
        do {
            let response = try await steamService.getLoginUrl()
            state = .loaded(response)
        } catch {
            state = .error(error.localizedDescription)
        }
    }
    
    func handleAuthCallback(steamId: String) {
        let saved = Keychain.save(steamId, for: .steamId)
        
        if saved {
            isAuthenticated = true
            authError = nil
        } else {
            Keychain.clearAll()
            authError = "Failed to save credentials securely. Please try again."
        }
    }
    
    func logout() {
        Keychain.clearAll()
        isAuthenticated = false
        state = .idle
    }
}
