#if DEBUG

import Foundation

final class MockCacheService: CacheService, @unchecked Sendable {
        
    var _owned: [Int: Game] = [:]
    var _wishlisted: [(game: Game, dateAdded: Date)] = []
    var _recommendations: [Game] = []
    var _profiles: [String: Profile] = [:]
    var _details: [Int: GameDetails] = [:]
    var _excluded: Set<Int> = []
    
    var setOwnedGamesCallCount = 0
    var setRecommendationsCallCount = 0
    var saveProfileCallCount = 0
    var clearAllCallCount = 0
    
    
    func ownedGames() -> [Game] {
        Array(_owned.values).sorted { $0.name < $1.name }
    }
    
    func recommendableOwnedGameIDs() -> [Int] {
        _owned.keys.filter { !_excluded.contains($0) }
    }
    
    func wishlistedGames() -> [Game] {
        _wishlisted
            .sorted { $0.dateAdded > $1.dateAdded }
            .map(\.game)
    }
    
    func recommendedGames() -> [Game] {
        _recommendations.sorted {
            ($0.score ?? 0) > ($1.score ?? 0)
        }
    }
    
    func isOwned(_ appid: Int) -> Bool {
        _owned[appid] != nil
    }
    
    func isWishlisted(_ appid: Int) -> Bool {
        _wishlisted.contains { $0.game.appid == appid }
    }
    
    
    func setOwnedGames(_ games: [Game]) {
        setOwnedGamesCallCount += 1
        _owned = Dictionary(uniqueKeysWithValues: games.map { ($0.appid, $0) })
    }
    
    func setExcludedFromRecommendations(_ appid: Int, excluded: Bool) {
        if excluded {
            _excluded.insert(appid)
        } else {
            _excluded.remove(appid)
        }
    }
    
    func setRecommendations(_ games: [Game]) {
        setRecommendationsCallCount += 1
        _recommendations = games
    }
    
    func addToWishlist(_ game: Game) {
        guard !isWishlisted(game.appid) else { return }
        _wishlisted.append((game: game, dateAdded: Date()))
    }
    
    func removeFromWishlist(_ appid: Int) {
        _wishlisted.removeAll { $0.game.appid == appid }
    }
    
    func toggleWishlist(_ game: Game) {
        if isWishlisted(game.appid) {
            removeFromWishlist(game.appid)
        } else {
            addToWishlist(game)
        }
    }
        
    func saveProfile(_ profile: Profile) {
        saveProfileCallCount += 1
        _profiles[profile.steamId] = profile
    }
    
    func loadProfile(steamId: String) -> Profile? {
        _profiles[steamId]
    }
    
    
    func cachedGameDetails(for appid: Int) -> GameDetails? {
        _details[appid]
    }
    
    func cacheGameDetails(_ details: GameDetails) {
        _details[details.appid] = details
    }
        
    func clearAll() {
        clearAllCallCount += 1
        _owned.removeAll()
        _wishlisted.removeAll()
        _recommendations.removeAll()
        _profiles.removeAll()
        _details.removeAll()
        _excluded.removeAll()
    }
}


extension MockCacheService {
    static func empty() -> MockCacheService { MockCacheService() }
    
    static func withSampleGames() -> MockCacheService {
        let mock = MockCacheService()
        mock.setOwnedGames(Game.previewList)
        mock.setOwnedGamesCallCount = 0
        return mock
    }
    
    static func withSampleProfile() -> MockCacheService {
        let mock = MockCacheService()
        mock.saveProfile(.preview)
        mock.saveProfileCallCount = 0
        return mock
    }
    
    static func withSampleRecommendations() -> MockCacheService {
        let mock = MockCacheService()
        mock.setRecommendations(Game.previewRecommendations)
        mock.setRecommendationsCallCount = 0
        return mock
    }
    
    static func withSampleData() -> MockCacheService {
        let mock = MockCacheService()
        mock.setOwnedGames(Game.previewList)
        mock.saveProfile(.preview)
        mock.setOwnedGamesCallCount = 0
        mock.saveProfileCallCount = 0
        return mock
    }
}

#endif
