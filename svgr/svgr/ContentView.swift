
import SwiftUI

struct ContentView: View {
    
    let steamService: SteamService
    let cacheService: CacheService
    
    @State private var loginViewModel: LoginViewModel
    
    init(steamService: SteamService, cacheService: CacheService) {
        self.steamService = steamService
        self.cacheService = cacheService
        _loginViewModel = State(initialValue: LoginViewModel(steamService: steamService))
    }
    
    var body: some View {
        Group {
            if loginViewModel.isAuthenticated {
                AuthenticatedView(
                    steamService: steamService,
                    cacheService: cacheService,
                    loginViewModel: loginViewModel
                )
            } else {
                LoginScreen(viewModel: loginViewModel)
            }
        }
        .onChange(of: loginViewModel.isAuthenticated) { _, isAuthenticated in
            if !isAuthenticated {
                cacheService.clearAll()
            }
        }
    }
}
