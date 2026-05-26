
#if DEBUG

import Foundation
import SwiftData
import SwiftUI

@MainActor
enum PreviewModelContainer {
    
    static func empty() -> ModelContainer {
        try! makeContainer()
    }
    
    static func withOwnedGames() -> ModelContainer {
        let container = try! makeContainer()
        let context = container.mainContext
        
        for game in Game.previewList {
            let entity = GameEntity.preview(from: game)
            context.insert(entity)
            let ownership = OwnershipEntry.preview(from: game, gameEntity: entity)
            context.insert(ownership)
        }
        
        try? context.save()
        return container
    }
    
    static func withWishlistedGames() -> ModelContainer {
        let container = try! makeContainer()
        let context = container.mainContext
        
        let now = Date()
        let games = [
            Game.previewSearchResult,
            Game.previewRecommendation,
            Game.previewLongName
        ]
        
        for (offset, game) in games.enumerated() {
            let entity = GameEntity.preview(from: game)
            context.insert(entity)
            let entry = WishlistEntry.preview(
                from: entity,
                dateAdded: now.addingTimeInterval(TimeInterval(-offset * 86400))
            )
            context.insert(entry)
        }
        
        try? context.save()
        return container
    }
    
    static func withRecommendations() -> ModelContainer {
        let container = try! makeContainer()
        let context = container.mainContext
        
        for game in Game.previewRecommendations {
            let entity = GameEntity.preview(from: game)
            context.insert(entity)
            let entry = RecommendationEntry.preview(from: entity, score: game.score ?? 0)
            context.insert(entry)
        }
        try? context.save()
        return container
    }
    
    static func withMixedRelationships() -> ModelContainer {
        let container = try! makeContainer()
        let context = container.mainContext
        
        let ownedEntity = GameEntity.preview(from: .preview)
        context.insert(ownedEntity)
        context.insert(OwnershipEntry.preview(from: .preview, gameEntity: ownedEntity))
        
        let wishlistedEntity = GameEntity.preview(from: .previewSearchResult)
        context.insert(wishlistedEntity)
        context.insert(WishlistEntry.preview(from: wishlistedEntity))
        
        try? context.save()
        return container
    }
    
    static func withFullSession() -> ModelContainer {
        let container = withOwnedGames()
        container.mainContext.insert(ProfileEntity.preview(from: .preview))
        try? container.mainContext.save()
        return container
    }
    
    
    private static func makeContainer() throws -> ModelContainer {
        let config = ModelConfiguration(isStoredInMemoryOnly: true)
        return try ModelContainer(
            for: GameEntity.self,
            OwnershipEntry.self,
            WishlistEntry.self,
            RecommendationEntry.self,
            ProfileEntity.self,
            configurations: config
        )
    }
}

extension View {
    func previewModelContainer(_ container: ModelContainer) -> some View {
        self.modelContainer(container)
    }
}

#endif
