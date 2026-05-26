#if DEBUG

import Foundation

final class MockSteamService: SteamService, @unchecked Sendable {
    
    var loginUrlResult: Result<LoginResponse, Error> = .success(.preview)
    var profileResult: Result<Profile, Error> = .success(.preview)
    var gamesResult: Result<[Game], Error> = .success(Game.previewList)
    var gameDetailsResult: Result<GameDetails, Error> = .success(.preview)
    var searchGamesResult: Result<[Game], Error> = .success([Game.previewSearchResult])
    var recommendationsResult: Result<[Game], Error> = .success(Game.previewRecommendations)
    var predictGameResult: Result<PredictionResult, Error> = .success(.preview)
    
    var artificialDelay: Duration = .zero
    
    
    func getLoginUrl() async throws -> LoginResponse {
        try await delay()
        return try loginUrlResult.get()
    }
    
    func getProfile(steamId: String) async throws -> Profile {
        try await delay()
        return try profileResult.get()
    }
    
    func getGames(steamId: String) async throws -> [Game] {
        try await delay()
        return try gamesResult.get()
    }
    
    func getGameDetails(appId: Int) async throws -> GameDetails {
        try await delay()
        return try gameDetailsResult.get()
    }
    
    func searchGames(for term: String, page: Int) async throws -> [Game] {
        try await delay()
        return try searchGamesResult.get()
    }
    
    func getRecommendations(ownedGamesIds: [Int], topK: Int) async throws -> [Game] {
        try await delay()
        return try recommendationsResult.get()
    }
    
    func predictGame(ownedGamesIds: [Int], targetGameId: Int) async throws -> PredictionResult {
        try await delay()
        return try predictGameResult.get()
    }
        
    private func delay() async throws {
        if artificialDelay > .zero {
            try await Task.sleep(for: artificialDelay)
        }
    }
}


extension MockSteamService {
    static func successful() -> MockSteamService {
        MockSteamService()
    }
    
    static func failing(error: Error = APIError.invalidResponse) -> MockSteamService {
        let mock = MockSteamService()
        mock.loginUrlResult = .failure(error)
        mock.profileResult = .failure(error)
        mock.gamesResult = .failure(error)
        mock.gameDetailsResult = .failure(error)
        mock.searchGamesResult = .failure(error)
        mock.recommendationsResult = .failure(error)
        mock.predictGameResult = .failure(error)
        return mock
    }
    
    static func loading() -> MockSteamService {
        let mock = MockSteamService()
        mock.artificialDelay = .seconds(3600)
        return mock
    }
    
    static func empty() -> MockSteamService {
        let mock = MockSteamService()
        mock.gamesResult = .success([])
        mock.searchGamesResult = .success([])
        mock.recommendationsResult = .success([])
        return mock
    }
}

#endif
