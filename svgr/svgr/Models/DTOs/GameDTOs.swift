import Foundation

struct GameDTO: Codable {
    let appid: Int
    let name: String
    let playtimeForever: Int
    let playtime2weeks: Int?
    let imgIconUrl: String
    let imgLogoUrl: String
    
    enum CodingKeys: String, CodingKey {
        case appid
        case name
        case playtimeForever = "playtime_forever"
        case playtime2weeks = "playtime_2weeks"
        case imgIconUrl = "img_icon_url"
        case imgLogoUrl = "img_logo_url"
    }
}

struct GamesResponseDTO: Codable {
    let steamId: String
    let gameCount: Int
    let games: [GameDTO]
    
    enum CodingKeys: String, CodingKey {
        case steamId = "steam_id"
        case gameCount = "game_count"
        case games
    }
}

struct GameDetailsDTO: Codable {
    let appid: Int
    let name: String
    let headerImage: String?
    let shortDescription: String?
    let developers: [String]?
    let publishers: [String]?
    let releaseDate: String?
    let priceOverview: String?
    let isFree: Bool?
    let genres: [String]?
    let categories: [String]?
    let reviews: GameReviewsDTO?
    
    enum CodingKeys: String, CodingKey {
        case appid
        case name
        case headerImage = "header_image"
        case shortDescription = "short_description"
        case developers
        case publishers
        case releaseDate = "release_date"
        case priceOverview = "price_overview"
        case isFree = "is_free"
        case genres
        case categories
        case reviews
    }
}

struct GameReviewsDTO: Codable {
    let total: Int
    let score: Int
    let description: String
}

struct SearchResultDTO: Codable {
    let appid: Int
    let name: String
    let logo: String?
    let price: String?
}

struct SearchResponseDTO: Codable {
    let results: [SearchResultDTO]
}

struct RecommendationResponseDTO: Codable {
    let recommendations: [RecommendedGameDTO]
}

struct RecommendedGameDTO: Codable {
    let appid: Int
    let score: Double
    let name: String
    let logo: String?
}

struct PredictionResponseDTO: Codable {
    let appid: Int
    let score: Double
}
