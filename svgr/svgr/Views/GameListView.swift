
import Foundation
import SwiftUI
import SwiftData

struct GameListView: View {
    
    let source: GameListSource    
    let steamService: SteamService
    let cacheService: CacheService
    
    var body: some View {
        switch source {
        case .owned:
            OwnedGamesList(steamService: steamService, cacheService: cacheService)
        case .wishlisted:
            WishlistedGamesList(steamService: steamService, cacheService: cacheService)
        case .recommended:
            RecommendedGamesList(steamService: steamService, cacheService: cacheService)
        case .search(let results):
            StaticGamesList(
                games: results,
                emptyState: ("No Results", "magnifyingglass", "No games found"),
                steamService: steamService,
                cacheService: cacheService
            )
        }
    }
}

private struct OwnedGamesList: View {
    
    @Query(sort: \OwnershipEntry.playtime, order: .reverse) private var entries: [OwnershipEntry]
    let steamService: SteamService
    let cacheService: CacheService
    
    var body: some View {
        let games = entries.compactMap { $0.toDomain() }
        StaticGamesList(
            games: games,
            emptyState: ("No Games", "gamecontroller", "Your owned games will appear here"),
            steamService: steamService,
            cacheService: cacheService
        )
    }
}


private struct WishlistedGamesList: View {
    
    @Query(sort: \WishlistEntry.dateAdded, order: .reverse) private var entries: [WishlistEntry]
    let steamService: SteamService
    let cacheService: CacheService
    
    var body: some View {
        let games = entries.compactMap { $0.toDomain() }
        StaticGamesList(
            games: games,
            emptyState: ("No Wishlisted Games", "heart", "Games you add to your wishlist will appear here"),
            steamService: steamService,
            cacheService: cacheService
        )
    }
}

private struct RecommendedGamesList: View {
    
    @Query(sort: \RecommendationEntry.score, order: .reverse) private var entries: [RecommendationEntry]
    let steamService: SteamService
    let cacheService: CacheService
    
    var body: some View {
        let games = entries.compactMap { $0.toDomain() }
        StaticGamesList(
            games: games,
            emptyState: ("No Recommendations", "star", "Tap refresh to get personalized recommendations"),
            steamService: steamService,
            cacheService: cacheService
        )
    }
}


private struct StaticGamesList: View {
    
    let games: [Game]
    let emptyState: (title: String, icon: String, description: String)
    
    let steamService: SteamService
    let cacheService: CacheService
    
    var body: some View {
        Group {
            if games.isEmpty {
                ContentUnavailableView(
                    emptyState.title,
                    systemImage: emptyState.icon,
                    description: Text(emptyState.description)
                )
            } else {
                List(games) { game in
                    NavigationLink(value: game) {
                        GameRow(game: game)
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationDestination(for: Game.self) { game in
            GameDetailsScreen(
                game: game,
                steamService: steamService,
                cacheService: cacheService
            )
        }
    }
}
