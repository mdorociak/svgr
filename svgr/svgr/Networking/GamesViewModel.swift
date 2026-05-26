
import Foundation

@Observable
class GamesViewModel {
    
    private let steamService: SteamService
    private let cacheService: CacheService
    
    var state: FetchState = .idle
    
    init(steamService: SteamService, cacheService: CacheService) {
        self.steamService = steamService
        self.cacheService = cacheService
    }
    
    func fetchGames(steamId: String) async {
        let wasLoaded = (state == .loaded)
        state = .loading
        
        do {
            let games = try await steamService.getGames(steamId: steamId)
            cacheService.setOwnedGames(games)
            state = .loaded
        } catch {
            if wasLoaded {
                state = .loaded
            } else {
                state = .error(error.localizedDescription)
            }
        }
    }
    
    func loadFromCache() {
        let games = cacheService.ownedGames()
        if !games.isEmpty {
            state = .loaded
        }
    }
}
