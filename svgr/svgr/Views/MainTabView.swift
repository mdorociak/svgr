
import SwiftUI

struct MainTabView: View {
    
    let loginViewModel: LoginViewModel
    let gamesViewModel: GamesViewModel
    let recommendationViewModel: RecommendationViewModel
    let profileViewModel: ProfileViewModel
    
    let steamService: SteamService
    let cacheService: CacheService
    
    var body: some View {
        TabView {
            Tab("Games", systemImage: "gamecontroller.fill") {
                GamesListScreen(viewModel: gamesViewModel,
                                steamService: steamService,
                                cacheService: cacheService
                )
            }
            Tab("For You", systemImage: "star.fill") {
                RecommendationScreen(viewModel: recommendationViewModel,
                                     steamService: steamService,
                                     cacheService: cacheService
                )
            }
            Tab("Wishlist", systemImage: "heart.fill") {
                WishlistScreen(steamService: steamService,
                               cacheService: cacheService
                )
            }
            Tab("Profile", systemImage: "person.fill") {
                ProfileScreen(
                    viewModel: profileViewModel,
                    loginViewModel: loginViewModel,
                    gamesViewModel: gamesViewModel)
            }
            Tab(role: .search) {
                SearchScreen(steamService: steamService,
                             cacheService: cacheService)
            }
        }
        .task {
            guard let steamId = loginViewModel.steamId else { return }
            
            gamesViewModel.loadFromCache()
            profileViewModel.loadFromCache(steamId: steamId)
            recommendationViewModel.loadFromCache()
            
            if gamesViewModel.state == .idle || profileViewModel.state.data  == nil {
                async let games: () = gamesViewModel.fetchGames(steamId: steamId)
                async let profile: () = profileViewModel.fetchProfile(steamId: steamId)
                _ = await (games, profile)
            }
        } 
    }
}

