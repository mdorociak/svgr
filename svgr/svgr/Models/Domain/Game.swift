import Foundation

struct Game: Identifiable, Hashable {
    let appid: Int
    let name: String
    let imageUrl: String?
    let playtime: Int?
    let playtime2weeks: Int?
    let score: Double?
    
    var id: Int { appid }
    
    var playtimeFormatted: String {
        Self.formatMinutes(playtime)
    }
    
    var playtime2weeksFormatted: String {
        Self.formatMinutes(playtime2weeks)
    }
    
    var scorePercentage: Int? {
        guard let score = score else { return nil }
        return Int(score * 100)
    }
    
    static func formatMinutes(_ minutes: Int?) -> String {
        guard let minutes = minutes else { return "0m" }
        let hours = minutes / 60
        let mins = minutes % 60
        if hours > 0 {
            return "\(hours)h \(mins)m"
        }
        return "\(mins)m"
    }
}

struct GameDetails: Identifiable, Equatable {
    let appid: Int
    let name: String
    let headerImage: String?
    let shortDescription: String?
    let developers: [String]?
    let publishers: [String]?
    let releaseDate: String?
    let price: String?
    let isFree: Bool
    let genres: [String]?
    let categories: [String]?
    let reviews: GameReviews?
    
    var id: Int { appid }
}

struct GameReviews: Equatable {
    let total: Int
    let score: Int
    let description: String
}

struct PredictionResult: Equatable {
    let appid: Int
    let score: Double
    
    var scorePercentage: Int {
        Int(score * 100)
    }
}
