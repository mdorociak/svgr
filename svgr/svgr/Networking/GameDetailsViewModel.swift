
import Foundation

@Observable
class GameDetailsViewModel {
    
    private let steamService: SteamService
    private let cacheService: CacheService
    
    var detailsState: LoadingState<GameDetails> = .idle
    var predictionState: LoadingState<PredictionResult> = .idle
    
    init(steamService: SteamService, cacheService: CacheService) {
        self.steamService = steamService
        self.cacheService = cacheService
    }
    
    func fetchGameDetails(appid: Int) async {
        if let cached = cacheService.cachedGameDetails(for: appid) {
            detailsState = .loaded(cached)
            return
        }
        
        detailsState = .loading
        
        do {
            let details = try await steamService.getGameDetails(appId: appid)
            cacheService.cacheGameDetails(details)
            detailsState = .loaded(details)
        } catch {
            detailsState = .error(error.localizedDescription)
        }
    }
    
    func fetchPrediction(appid: Int) async {
        let ownedIds = cacheService.recommendableOwnedGameIDs()
        
        guard !ownedIds.isEmpty else {
            predictionState = .error("No owned games to compare to.")
            return
        }
        
        predictionState = .loading
        
        do {
            let result = try await steamService.predictGame(ownedGamesIds: ownedIds, targetGameId: appid)
            predictionState = .loaded(result)
        } catch {
            predictionState = .error("Unable to predict.")
        }
    }
}
