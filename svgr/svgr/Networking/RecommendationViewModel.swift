import Foundation

@Observable
class RecommendationViewModel {
    
    private let steamService: SteamService
    private let cacheService: CacheService
    
    var state: FetchState = .idle
    
    init(steamService: SteamService, cacheService: CacheService) {
        self.steamService = steamService
        self.cacheService = cacheService
    }
    
    func loadFromCache() {
        if !cacheService.recommendedGames().isEmpty {
            state = .loaded
        }
    }
    
    func refreshRecommendations() async {
        let ownedGames = cacheService.recommendableOwnedGames()
        
        guard !ownedGames.isEmpty else {
            state = .error("No games selected to base recommendations on.")
            return
        }
        
        let wasLoaded = (state == .loaded)
        state = .loading
        
        do {
            let games = try await steamService.getRecommendations(
                ownedGames: ownedGames,
                topK: 20
            )
            cacheService.setRecommendations(games)
            state = .loaded
        } catch {
            if wasLoaded {
                state = .loaded
            } else {
                state = .error(error.localizedDescription)
            }
        }
    }
}
