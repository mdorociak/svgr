import Foundation

final class DefaultSteamService: SteamService, Sendable {

    private let baseURL: String
    
    init(baseURL: String = APIConstants.baseURL) {
        self.baseURL = baseURL
    }
    
    func getLoginUrl() async throws -> LoginResponse {
        let dto: LoginResponseDTO = try await post(endpoint: APIConstants.Endpoints.steamLogin)
        return dto.toDomain()
    }
    
    func getProfile(steamId: String) async throws -> Profile {
        let dto: ProfileDTO = try await get(endpoint: APIConstants.Endpoints.profile(steamID: steamId))
        return dto.toDomain()
    }
    
    func getGames(steamId: String) async throws -> [Game] {
        let dto: GamesResponseDTO = try await get(endpoint: APIConstants.Endpoints.gameList(steamID: steamId))
        return dto.games.map { $0.toDomain() }
    }
    
    func getGameDetails(appId: Int) async throws -> GameDetails {
        let dto: GameDetailsDTO = try await get(endpoint: APIConstants.Endpoints.gameDetails(appid: appId))
        return dto.toDomain()
    }
    
    func searchGames(for term: String, page: Int = 1) async throws -> [Game] {
        let dto: SearchResponseDTO = try await get(endpoint: APIConstants.Endpoints.searchGames(term: term, page: page))
        return dto.results.map { $0.toDomain() }
    }
   
    func getRecommendations(ownedGames: [Int: Int], topK: Int = 20) async throws -> [Game] {
        let body = RecommendationRequestDTO(ownedGames: ownedGames, topK: topK)
        let dto: RecommendationResponseDTO = try await post(
            endpoint: APIConstants.Endpoints.recommendations,
            body: body
        )
        return dto.recommendations.map { $0.toDomain() }
    }
    
    func predictGame(ownedGamesIDs: [Int], targetGameID: Int) async throws -> PredictionResult {
        let body = PredictionRequestDTO(ownedGameIDs: ownedGamesIDs, targetGameID: targetGameID)
        let dto: PredictionResponseDTO = try await post(
            endpoint: APIConstants.Endpoints.predict,
            body: body
        )
        return dto.toDomain()
    }
    
    
    private func get<T: Decodable>(endpoint: String) async throws -> T {
        let url = try buildURL(endpoint: endpoint)
        return try await performRequest(URLRequest(url: url))
    }
    
    private func post<T: Decodable, Body: Encodable>(endpoint: String, body: Body) async throws -> T {
        var request = try makePostRequest(endpoint: endpoint)
        request.httpBody = try JSONEncoder().encode(body)
        return try await performRequest(request)
    }
    
    private func post<T: Decodable>(endpoint: String) async throws -> T {
        let request = try makePostRequest(endpoint: endpoint)
        return try await performRequest(request)
    }
    
    private func makePostRequest(endpoint: String) throws -> URLRequest {
        let url = try buildURL(endpoint: endpoint)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        return request
    }
    
    private func buildURL(endpoint: String) throws -> URL {
        guard let url = URL(string: baseURL + endpoint) else {
            throw APIError.invalidURL
        }
        return url
    }
    
    private func performRequest<T: Decodable>(_ request: URLRequest) async throws -> T {
        let data: Data
        let response: URLResponse
        
        do {
            (data, response) = try await URLSession.shared.data(for: request)
        } catch {
            throw APIError.networkError(error)
        }
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.invalidResponse
        }
        
        do {
            let decoder = JSONDecoder()
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }
}

