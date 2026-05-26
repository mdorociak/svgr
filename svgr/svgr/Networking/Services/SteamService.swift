
import Foundation

protocol SteamService: Sendable {
    func getLoginUrl() async throws -> LoginResponse
    func getProfile(steamId: String) async throws -> Profile
    func getGames(steamId: String) async throws -> [Game]
    func getGameDetails(appId: Int) async throws -> GameDetails
    func searchGames(for term: String, page: Int) async throws -> [Game]
    func getRecommendations(ownedGamesIds: [Int], topK: Int) async throws -> [Game]
    func predictGame(ownedGamesIds:[Int], targetGameId: Int) async throws -> PredictionResult
}
