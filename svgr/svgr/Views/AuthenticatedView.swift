
import SwiftUI

struct AuthenticatedView: View {
    
    let steamService: SteamService
    let cacheService: CacheService
    
    let loginViewModel: LoginViewModel
    
    @State private var gamesViewModel: GamesViewModel
    @State private var profileViewModel: ProfileViewModel
    @State private var recommendationViewModel: RecommendationViewModel
    
    init(
        steamService: SteamService,
        cacheService: CacheService,
        loginViewModel: LoginViewModel
    ) {
        self.steamService = steamService
        self.cacheService = cacheService
        self.loginViewModel = loginViewModel
        _gamesViewModel = State(initialValue: GamesViewModel(steamService: steamService, cacheService: cacheService))
        _profileViewModel = State(initialValue: ProfileViewModel(steamService: steamService, cacheService: cacheService))
        _recommendationViewModel = State(initialValue: RecommendationViewModel(steamService: steamService, cacheService: cacheService))
    }
    
    var body: some View {
        MainTabView(
            loginViewModel: loginViewModel,
            gamesViewModel: gamesViewModel,
            recommendationViewModel: recommendationViewModel,
            profileViewModel: profileViewModel,
            steamService: steamService,
            cacheService: cacheService
        )
    }
}
