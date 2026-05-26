
import Foundation
import SwiftData

@Model
final class RecommendationEntry {
    var score: Double
    var dateFetched: Date
    
    var game: GameEntity?
    
    init(game: GameEntity, score: Double, dateFetched: Date = Date()) {
        self.game = game
        self.score = score
        self.dateFetched = dateFetched
    }
}
