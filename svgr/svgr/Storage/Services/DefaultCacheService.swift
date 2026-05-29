
import Foundation
import SwiftData
import os

@Observable
final class DefaultCacheService: CacheService {
    
    private let modelContainer: ModelContainer
    private var modelContext: ModelContext
    
    private var gameDetailsCache: [Int: GameDetails] = [:]
    
    init(modelContainer: ModelContainer) {
        self.modelContainer = modelContainer
        self.modelContext = modelContainer.mainContext
    }
    
    
    func ownedGames() -> [Game] {
        let descriptor = FetchDescriptor<OwnershipEntry>(
            sortBy: [SortDescriptor(\.playtime, order: .reverse)]
        )
        do {
            let entries = try modelContext.fetch(descriptor)
            return entries.compactMap { $0.toDomain() }
        } catch {
            Logger.cache.error("Failed to fetch owned games: \(error.localizedDescription, privacy: .public)")
            return []
        }
    }
    
    func wishlistedGames() -> [Game] {
        let descriptor = FetchDescriptor<WishlistEntry>(
            sortBy: [SortDescriptor(\.dateAdded, order: .reverse)]
        )
        do {
            let entries = try modelContext.fetch(descriptor)
            return entries.compactMap { $0.toDomain() }
        } catch {
            Logger.cache.error("Failed to fetch wishlisted games: \(error.localizedDescription, privacy: .public)")
            return []
        }
    }
    
    func recommendedGames() -> [Game] {
        let descriptor = FetchDescriptor<RecommendationEntry>(
            sortBy: [SortDescriptor(\.score, order: .reverse)]
        )
        do {
            let entries = try modelContext.fetch(descriptor)
            return entries.compactMap { $0.toDomain() }
        } catch {
            Logger.cache.error("Failed to fetch recommended games: \(error.localizedDescription, privacy: .public)")
            return []
        }
    }
    
    func recommendableOwnedGameIDs() -> [Int] {
        let descriptor = FetchDescriptor<OwnershipEntry>(
            predicate: #Predicate { $0.excludedFromRecommendations == false }
        )
        do {
            return try modelContext.fetch(descriptor).compactMap { $0.game?.appid }
        } catch {
            Logger.cache.error("Failed to fetch recommendable game IDs: \(error.localizedDescription, privacy: .public)")
            return []
        }
    }
    
    func isOwned(_ appid: Int) -> Bool {
        let descriptor = FetchDescriptor<OwnershipEntry>(
            predicate: #Predicate { $0.game?.appid == appid }
        )
        do {
            return try modelContext.fetchCount(descriptor) > 0
        } catch {
            Logger.cache.error("Failed to check ownership for appid \(appid): \(error.localizedDescription, privacy: .public)")
            return false
        }
    }
    
    func isWishlisted(_ appid: Int) -> Bool {
        let descriptor = FetchDescriptor<WishlistEntry>(
            predicate: #Predicate { $0.game?.appid == appid }
        )
        do {
            return try modelContext.fetchCount(descriptor) > 0
        } catch {
            Logger.cache.error("Failed to check wishlist for appid \(appid): \(error.localizedDescription, privacy: .public)")
            return false
        }
    }
    
    
    func setOwnedGames(_ games: [Game]) {
        do {
            let incomingAppids = Set(games.map(\.appid))
            
            let existingOwnership = try modelContext.fetch(FetchDescriptor<OwnershipEntry>())
            var ownershipByAppid: [Int: OwnershipEntry] = [:]
            for entry in existingOwnership {
                if let appid = entry.game?.appid {
                    ownershipByAppid[appid] = entry
                }
            }
            
            for entry in existingOwnership {
                if let appid = entry.game?.appid, !incomingAppids.contains(appid) {
                    modelContext.delete(entry)
                }
            }
            
            for game in games {
                let entity = upsertGameEntity(from: game)
                if let existing = ownershipByAppid[game.appid] {
                    existing.playtime = game.playtime ?? 0
                    existing.playtime2Weeks = game.playtime2weeks
                    existing.lastUpdated = Date()
                } else {
                    let entry = OwnershipEntry(
                        game: entity,
                        playtime: game.playtime ?? 0,
                        playtime2Weeks: game.playtime2weeks
                    )
                    modelContext.insert(entry)
                }
            }
            
            try modelContext.save()
        } catch {
            Logger.cache.error("Failed to set owned games: \(error.localizedDescription, privacy: .public)")
        }
    }
    
    func setExcludedFromRecommendations(_ appid: Int, excluded: Bool) {
        let descriptor = FetchDescriptor<OwnershipEntry>(
            predicate: #Predicate { $0.game?.appid == appid }
        )
        do {
            guard let entry = try modelContext.fetch(descriptor).first else { return }
            entry.excludedFromRecommendations = excluded
            try modelContext.save()
        } catch {
            Logger.cache.error("Failed to set exclusion for appid \(appid): \(error.localizedDescription, privacy: .public)")
        }
    }
    
    func setRecommendations(_ games: [Game]) {
        do {
            let incomingAppids = Set(games.map(\.appid))
            
            let existing = try modelContext.fetch(FetchDescriptor<RecommendationEntry>())
            var entryByAppid: [Int: RecommendationEntry] = [:]
            for entry in existing {
                if let appid = entry.game?.appid {
                    entryByAppid[appid] = entry
                }
            }
            
            for entry in existing {
                if let appid = entry.game?.appid, !incomingAppids.contains(appid) {
                    modelContext.delete(entry)
                }
            }
            
            for game in games {
                let entity = upsertGameEntity(from: game)
                if let existing = entryByAppid[game.appid] {
                    existing.score = game.score ?? 0
                    existing.dateFetched = Date()
                } else {
                    let entry = RecommendationEntry(
                        game: entity,
                        score: game.score ?? 0
                    )
                    modelContext.insert(entry)
                }
            }
            
            try modelContext.save()
        } catch {
            Logger.cache.error("Failed to set recommendations: \(error.localizedDescription, privacy: .public)")
        }
    }
    
    func addToWishlist(_ game: Game) {
        guard !isWishlisted(game.appid) else { return }
        do {
            let entity = upsertGameEntity(from: game)
            let entry = WishlistEntry(game: entity)
            modelContext.insert(entry)
            try modelContext.save()
        } catch {
            Logger.cache.error("Failed to add appid \(game.appid) to wishlist: \(error.localizedDescription, privacy: .public)")
        }
    }
    
    func removeFromWishlist(_ appid: Int) {
        let descriptor = FetchDescriptor<WishlistEntry>(
            predicate: #Predicate { $0.game?.appid == appid }
        )
        do {
            let entries = try modelContext.fetch(descriptor)
            for entry in entries {
                modelContext.delete(entry)
            }
            try modelContext.save()
        } catch {
            Logger.cache.error("Failed to remove appid \(appid) from wishlist: \(error.localizedDescription, privacy: .public)")
        }
    }
    
    func toggleWishlist(_ game: Game) {
        if isWishlisted(game.appid) {
            removeFromWishlist(game.appid)
        } else {
            addToWishlist(game)
        }
    }
    
    
    func saveProfile(_ profile: Profile) {
        let steamId = profile.steamId
        let descriptor = FetchDescriptor<ProfileEntity>(
            predicate: #Predicate { $0.steamId == steamId }
        )
        do {
            if let existing = try modelContext.fetch(descriptor).first {
                existing.update(from: profile)
            } else {
                modelContext.insert(ProfileEntity(from: profile))
            }
            try modelContext.save()
        } catch {
            Logger.cache.error("Failed to save profile for steamId \(steamId, privacy: .public): \(error.localizedDescription, privacy: .public)")
        }
    }
    
    func loadProfile(steamId: String) -> Profile? {
        let descriptor = FetchDescriptor<ProfileEntity>(
            predicate: #Predicate { $0.steamId == steamId }
        )
        do {
            return try modelContext.fetch(descriptor).first?.toDomain()
        } catch {
            Logger.cache.error("Failed to load profile for steamId \(steamId, privacy: .public): \(error.localizedDescription, privacy: .public)")
            return nil
        }
    }
    
    
    func cachedGameDetails(for appid: Int) -> GameDetails? {
        gameDetailsCache[appid]
    }
    
    func cacheGameDetails(_ details: GameDetails) {
        gameDetailsCache[details.appid] = details
    }
    
    
    func clearAll() {
        do {
            try modelContext.delete(model: WishlistEntry.self)
            try modelContext.delete(model: OwnershipEntry.self)
            try modelContext.delete(model: RecommendationEntry.self)
            try modelContext.delete(model: GameEntity.self)
            try modelContext.delete(model: ProfileEntity.self)
            try modelContext.save()
        } catch {
            Logger.cache.error("Failed to clear all cache: \(error.localizedDescription, privacy: .public)")
        }
        
        gameDetailsCache.removeAll()
    }
    

    private func upsertGameEntity(from game: Game) -> GameEntity {
        let appid = game.appid
        let descriptor = FetchDescriptor<GameEntity>(
            predicate: #Predicate { $0.appid == appid }
        )
        do {
            if let existing = try modelContext.fetch(descriptor).first {
                existing.update(from: game)
                return existing
            }
        } catch {
            Logger.cache.error("Failed to lookup GameEntity for appid \(appid): \(error.localizedDescription, privacy: .public)")
        }
        let new = GameEntity(from: game)
        modelContext.insert(new)
        return new
    }
}
