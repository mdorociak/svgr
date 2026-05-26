
import Foundation

@Observable
class ProfileViewModel {
    
    private let steamService: SteamService
    private let cacheService: CacheService
    
    var state: LoadingState<Profile> = .idle

    init(steamService: SteamService, cacheService: CacheService) {
        self.steamService = steamService
        self.cacheService = cacheService
    }
    
    func loadFromCache(steamId: String) {
        if let cachedProfile = cacheService.loadProfile(steamId: steamId) {
            state = .loaded(cachedProfile)
        }
    }
    
    func fetchProfile(steamId: String) async {
        let previousData = state.data
        state = .loading
        
        do {
            let profile = try await steamService.getProfile(steamId: steamId)
            cacheService.saveProfile(profile)
            state = .loaded(profile)
        } catch {
            if let cached = previousData {
                state = .loaded(cached)
            } else {
                state = .error(error.localizedDescription)
            }
        }
    }
    
    func syncData(steamId: String, gamesViewModel: GamesViewModel) async {
        async let games: () = gamesViewModel.fetchGames(steamId: steamId)
        async let profile: () = fetchProfile(steamId: steamId)
        _ = await (games, profile)
    }
}
