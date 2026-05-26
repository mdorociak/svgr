
import Foundation
import SwiftData

@Model
class GameEntity {
    @Attribute(.unique) var appid: Int
    var name: String
    var imageUrl: String?
    var lastUpdated: Date
    
    @Relationship(deleteRule: .cascade, inverse: \OwnershipEntry.game)
    var ownershipEntry: OwnershipEntry?
    
    @Relationship(deleteRule: .cascade, inverse: \WishlistEntry.game)
    var wishlistEntry: WishlistEntry?
    
    @Relationship(deleteRule: .cascade, inverse: \RecommendationEntry.game)
    var recommendationEntry: RecommendationEntry?
    
    
    init(appid: Int, name: String, imageUrl: String? = nil) {
        self.appid = appid
        self.name = name
        self.imageUrl = imageUrl
        self.lastUpdated = Date()
    }
    
    convenience init(from game: Game) {
        self.init(
            appid: game.appid,
            name: game.name,
            imageUrl: game.imageUrl
        )
    }
    
    func update(from game: Game) {
        name = game.name
        imageUrl = game.imageUrl
        lastUpdated = Date()
    }
}
