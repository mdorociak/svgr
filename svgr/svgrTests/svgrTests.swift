import Testing
import Foundation
@testable import svgr

// LoginViewModel

@Suite("LoginViewModel")
@MainActor
struct LoginViewModelTests {
    
    init() {
        Keychain.clearAll()
    }
    
    @Test("getLoginUrl success → state becomes .loaded")
    func getLoginUrlSuccess() async {
        let mock = MockSteamService.successful()
        let viewModel = LoginViewModel(steamService: mock)
        
        await viewModel.getLoginUrl()
        
        #expect(viewModel.state.data == LoginResponse.preview)
    }
    
    @Test("getLoginUrl failure → state becomes .error")
    func getLoginUrlFailure() async {
        let mock = MockSteamService.failing()
        let viewModel = LoginViewModel(steamService: mock)
        
        await viewModel.getLoginUrl()
        
        #expect(viewModel.state.error != nil)
    }
    
    @Test("handleAuthCallback saves to keychain and sets authenticated")
    func handleAuthCallback() {
        let mock = MockSteamService.successful()
        let viewModel = LoginViewModel(steamService: mock)
        
        viewModel.handleAuthCallback(steamId: "76561198012345678")
        
        #expect(viewModel.isAuthenticated == true)
        #expect(viewModel.steamId == "76561198012345678")
    }
    
    @Test("logout clears keychain and unsets authenticated")
    func logout() {
        let mock = MockSteamService.successful()
        let viewModel = LoginViewModel(steamService: mock)
        viewModel.handleAuthCallback(steamId: "76561198012345678")
        
        viewModel.logout()
        
        #expect(viewModel.isAuthenticated == false)
        #expect(viewModel.steamId == nil)
        #expect(viewModel.state == .idle)
    }
}

// GamesViewModel

@Suite("GamesViewModel")
@MainActor
struct GamesViewModelTests {
    
    @Test("fetchGames success → state .loaded and cache populated")
    func fetchGamesSuccess() async {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.empty()
        let viewModel = GamesViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.fetchGames(steamId: "76561198012345678")
        
        #expect(viewModel.state == .loaded)
        #expect(cache.setOwnedGamesCallCount == 1)
        #expect(cache._owned.count == Game.previewList.count)
    }

    @Test("fetchGames failure with no prior data → state .error")
    func fetchGamesFailureNoCache() async {
        let steam = MockSteamService.failing()
        let cache = MockCacheService.empty()
        let viewModel = GamesViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.fetchGames(steamId: "76561198012345678")
        
        #expect(viewModel.state.error != nil)
    }

    @Test("fetchGames failure after prior success → stays .loaded")
    func fetchGamesFailureWithPriorSuccess() async {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.empty()
        let viewModel = GamesViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.fetchGames(steamId: "76561198012345678")
        #expect(viewModel.state == .loaded)
        
        steam.gamesResult = .failure(APIError.invalidResponse)
        await viewModel.fetchGames(steamId: "76561198012345678")
        
        #expect(viewModel.state == .loaded)
    }

    @Test("loadFromCache with games → state .loaded")
    func loadFromCachePopulated() {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.withSampleGames()
        let viewModel = GamesViewModel(steamService: steam, cacheService: cache)
        
        viewModel.loadFromCache()
        
        #expect(viewModel.state == .loaded)
    }

    @Test("loadFromCache with empty cache → state stays .idle")
    func loadFromCacheEmpty() {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.empty()
        let viewModel = GamesViewModel(steamService: steam, cacheService: cache)
        
        viewModel.loadFromCache()
        
        #expect(viewModel.state == .idle)
    }
}

// ProfileViewModel

@Suite("ProfileViewModel")
@MainActor
struct ProfileViewModelTests {
    
    @Test("fetchProfile success → state .loaded and cache populated")
    func fetchProfileSuccess() async {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.empty()
        let viewModel = ProfileViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.fetchProfile(steamId: Profile.preview.steamId)
        
        #expect(viewModel.state.data == Profile.preview)
        #expect(cache.saveProfileCallCount == 1)
    }
    
    @Test("fetchProfile failure with no cached data → state .error")
    func fetchProfileFailureNoCache() async {
        let steam = MockSteamService.failing()
        let cache = MockCacheService.empty()
        let viewModel = ProfileViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.fetchProfile(steamId: "76561198012345678")
        
        #expect(viewModel.state.error != nil)
    }
    
    @Test("fetchProfile failure with prior data → falls back")
    func fetchProfileFailureWithCache() async {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.empty()
        let viewModel = ProfileViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.fetchProfile(steamId: Profile.preview.steamId)
        let priorProfile = viewModel.state.data
        
        steam.profileResult = .failure(APIError.invalidResponse)
        await viewModel.fetchProfile(steamId: Profile.preview.steamId)
        
        #expect(viewModel.state.data == priorProfile)
    }
    
    @Test("loadFromCache with profile → state .loaded")
    func loadFromCachePopulated() {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.withSampleProfile()
        let viewModel = ProfileViewModel(steamService: steam, cacheService: cache)
        
        viewModel.loadFromCache(steamId: Profile.preview.steamId)
        
        #expect(viewModel.state.data == Profile.preview)
    }
    
    @Test("loadFromCache with empty cache → state stays .idle")
    func loadFromCacheEmpty() {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.empty()
        let viewModel = ProfileViewModel(steamService: steam, cacheService: cache)
        
        viewModel.loadFromCache(steamId: "76561198012345678")
        
        #expect(viewModel.state == .idle)
    }
}

// GameDetailsViewModel

@Suite("GameDetailsViewModel")
@MainActor
struct GameDetailsViewModelTests {
    
    @Test("fetchGameDetails success → state .loaded and cache populated")
    func fetchGameDetailsSuccess() async {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.empty()
        let viewModel = GameDetailsViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.fetchGameDetails(appid: GameDetails.preview.appid)
        
        #expect(viewModel.detailsState.data == GameDetails.preview)
        #expect(cache.cachedGameDetails(for: GameDetails.preview.appid) != nil)
    }
    
    @Test("fetchGameDetails cache hit → uses cache, skips service")
    func fetchGameDetailsCacheHit() async {
        let steam = MockSteamService.successful()
        steam.gameDetailsResult = .success(.previewPaid)
        let cache = MockCacheService.empty()
        cache.cacheGameDetails(.preview)
        let viewModel = GameDetailsViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.fetchGameDetails(appid: GameDetails.preview.appid)
        
        #expect(viewModel.detailsState.data == GameDetails.preview)
    }
    
    @Test("fetchGameDetails failure → state .error")
    func fetchGameDetailsFailure() async {
        let steam = MockSteamService.failing()
        let cache = MockCacheService.empty()
        let viewModel = GameDetailsViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.fetchGameDetails(appid: 12345)
        
        #expect(viewModel.detailsState.error != nil)
    }
    
    @Test("fetchPrediction success → state .loaded")
    func fetchPredictionSuccess() async {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.withSampleGames()
        let viewModel = GameDetailsViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.fetchPrediction(appid: GameDetails.preview.appid)
        
        #expect(viewModel.predictionState.data == PredictionResult.preview)
    }
    
    @Test("fetchPrediction with no owned games → state .error, no service call")
    func fetchPredictionNoOwnedGames() async {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.empty()
        let viewModel = GameDetailsViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.fetchPrediction(appid: GameDetails.preview.appid)
        
        #expect(viewModel.predictionState.error == "No owned games to compare to.")
    }
    
    @Test("fetchPrediction failure → state .error")
    func fetchPredictionFailure() async {
        let steam = MockSteamService.failing()
        let cache = MockCacheService.withSampleGames()
        let viewModel = GameDetailsViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.fetchPrediction(appid: GameDetails.preview.appid)
        
        #expect(viewModel.predictionState.error == "Unable to predict.")
    }
}

// RecommendationViewModel

@Suite("RecommendationViewModel")
@MainActor
struct RecommendationViewModelTests {
    
    @Test("refreshRecommendations success → state .loaded and cache populated")
    func refreshSuccess() async {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.withSampleGames()
        let viewModel = RecommendationViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.refreshRecommendations()
        
        #expect(viewModel.state == .loaded)
        #expect(cache.setRecommendationsCallCount == 1)
        #expect(cache._recommendations.count == Game.previewRecommendations.count)
    }
    
    @Test("refreshRecommendations with no owned games → state .error, no service call")
    func refreshNoOwnedGames() async {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.empty()
        let viewModel = RecommendationViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.refreshRecommendations()
        
        #expect(viewModel.state.error == "No owned games to base recommendations on.")
        #expect(cache.setRecommendationsCallCount == 0)
    }
    
    @Test("refreshRecommendations failure with no prior data → state .error")
    func refreshFailureNoPrior() async {
        let steam = MockSteamService.failing()
        let cache = MockCacheService.withSampleGames()
        let viewModel = RecommendationViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.refreshRecommendations()
        
        #expect(viewModel.state.error != nil)
    }
    
    @Test("refreshRecommendations failure after prior success → stays .loaded")
    func refreshFailureWithPriorSuccess() async {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.withSampleGames()
        let viewModel = RecommendationViewModel(steamService: steam, cacheService: cache)
        
        await viewModel.refreshRecommendations()
        #expect(viewModel.state == .loaded)
        
        steam.recommendationsResult = .failure(APIError.invalidResponse)
        await viewModel.refreshRecommendations()
        
        #expect(viewModel.state == .loaded)
    }
    
    @Test("loadFromCache with persisted recs → state .loaded")
    func loadFromCachePopulated() {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.withSampleRecommendations()
        let viewModel = RecommendationViewModel(steamService: steam, cacheService: cache)
        
        viewModel.loadFromCache()
        
        #expect(viewModel.state == .loaded)
    }
    
    @Test("loadFromCache with empty cache → state stays .idle")
    func loadFromCacheEmpty() {
        let steam = MockSteamService.successful()
        let cache = MockCacheService.empty()
        let viewModel = RecommendationViewModel(steamService: steam, cacheService: cache)
        
        viewModel.loadFromCache()
        
        #expect(viewModel.state == .idle)
    }
}

// SearchGamesViewModel

@Suite("SearchGamesViewModel")
@MainActor
struct SearchGamesViewModelTests {
    
    @Test("fetch with empty string → state .idle, no service call")
    func fetchEmpty() async {
        let steam = MockSteamService.successful()
        let viewModel = SearchGamesViewModel(steamService: steam)
        
        await viewModel.fetch(for: "")
        
        #expect(viewModel.state == .idle)
    }
    
    @Test("fetch success → state .loaded")
    func fetchSuccess() async {
        let steam = MockSteamService.successful()
        let viewModel = SearchGamesViewModel(steamService: steam)
        
        await viewModel.fetch(for: "stardew")
        
        #expect(viewModel.state.data == [Game.previewSearchResult])
    }
    
    @Test("fetch failure → state .error")
    func fetchFailure() async {
        let steam = MockSteamService.failing()
        let viewModel = SearchGamesViewModel(steamService: steam)
        
        await viewModel.fetch(for: "stardew")
        
        #expect(viewModel.state.error != nil)
    }
}
