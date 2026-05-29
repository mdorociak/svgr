
import Foundation
import SwiftData

@Model
final class OwnershipEntry {
    var game: GameEntity?
    var excludedFromRecommendations: Bool = false
    
    var playtime: Int
    var playtime2Weeks: Int?
    var lastUpdated: Date
        
    init(game: GameEntity, playtime: Int, playtime2Weeks: Int? = nil) {
        self.game = game
        self.playtime = playtime
        self.playtime2Weeks = playtime2Weeks
        self.lastUpdated = Date()
    }
    
    func update(playtime: Int, playtime2Weeks: Int?) {
        self.playtime = playtime
        self.playtime2Weeks = playtime2Weeks
        self.lastUpdated = Date()
    }
}
