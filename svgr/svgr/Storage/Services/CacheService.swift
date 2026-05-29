
import Foundation

protocol CacheService {
    
    func ownedGames() -> [Game]
    func wishlistedGames() -> [Game]
    func recommendedGames() -> [Game]
    func recommendableOwnedGameIDs() -> [Int]
    
    func isOwned(_ appid: Int) -> Bool
    func isWishlisted(_ appid: Int) -> Bool
    
    func setOwnedGames(_ games: [Game])
    func setRecommendations(_ games: [Game])
    func setExcludedFromRecommendations(_ appid: Int, excluded: Bool)
    
    func addToWishlist(_ game: Game)
    func removeFromWishlist(_ appid: Int)
    func toggleWishlist(_ game: Game)
    
    func saveProfile(_ profile: Profile)
    func loadProfile(steamId: String) -> Profile?
    
    func cachedGameDetails(for appid: Int) -> GameDetails?
    func cacheGameDetails(_ details: GameDetails)
    
    func clearAll()
}
