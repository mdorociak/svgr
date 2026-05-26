
import Foundation

enum APIConstants {
    
    static let baseURL = "http://localhost:8000"
    
    enum Endpoints {
        static let steamLogin = "/auth/steam/login"
        static let steamCallback = "/auth/steam/callback"
        
        static func profile(steamID: String) -> String {
            return "/api/profile/\(steamID)"
        }
        
        static func gameList(steamID: String) -> String {
            return "/api/games/\(steamID)"
        }
        
        static func gameDetails(appid: Int) -> String {
            return "/api/game/\(appid)"
        }
        
        static func searchGames(term: String, page: Int) -> String {
            let encodedTerm = term.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? term
            return "/api/search?term=\(encodedTerm)&page=\(page)"
        }
        
        static let recommendations = "/api/recommendations"
        static let predict = "/api/recommendations/predict"
    }
}
