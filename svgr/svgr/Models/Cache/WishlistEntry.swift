
import Foundation
import SwiftData

@Model
final class WishlistEntry {
    var dateAdded: Date
    
    var game: GameEntity?
    
    init(game: GameEntity, dateAdded: Date = Date()) {
        self.game = game
        self.dateAdded = dateAdded
    }
}
