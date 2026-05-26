#if DEBUG

import Foundation
import SwiftData

extension Game {
    static let preview = Game(
        appid: 440,
        name: "Team Fortress 2",
        imageUrl: "https://media.steampowered.com/steamcommunity/public/images/apps/440/e3f595a92552da3d664ad00277fad2107345f743.jpg",
        playtime: 4823,
        playtime2weeks: 184,
        score: nil
    )
    
    static let previewLowPlaytime = Game(
        appid: 105600,
        name: "Terraria",
        imageUrl: "https://media.steampowered.com/steamcommunity/public/images/apps/105600/858961e95da27db662bb4vfjwd.jpg",
        playtime: 23,
        playtime2weeks: nil,
        score: nil
    )
    
    static let previewSearchResult = Game(
        appid: 1086940,
        name: "Baldur's Gate 3",
        imageUrl: "https://cdn.cloudflare.steamstatic.com/steam/apps/1086940/header.jpg",
        playtime: nil,
        playtime2weeks: nil,
        score: nil
    )
    
    static let previewRecommendation = Game(
        appid: 813780,
        name: "Age of Empires II: Definitive Edition",
        imageUrl: "https://cdn.cloudflare.steamstatic.com/steam/apps/813780/header.jpg",
        playtime: nil,
        playtime2weeks: nil,
        score: 0.87
    )
    
    static let previewRecommendations: [Game] = [
        .previewRecommendation,
        Game(
            appid: 105600,
            name: "Terraria",
            imageUrl: "https://cdn.cloudflare.steamstatic.com/steam/apps/105600/header.jpg",
            playtime: nil,
            playtime2weeks: nil,
            score: 0.72
        ),
        Game(
            appid: 1086940,
            name: "Baldur's Gate 3",
            imageUrl: "https://cdn.cloudflare.steamstatic.com/steam/apps/1086940/header.jpg",
            playtime: nil,
            playtime2weeks: nil,
            score: 0.65)
    ]
    
    static let previewLongName = Game(
        appid: 1245620,
        name: "ELDEN RING — Shadow of the Erdtree Edition with Bonus Content",
        imageUrl: nil,
        playtime: 12450,
        playtime2weeks: 2340,
        score: nil
    )
    
    static let previewList: [Game] = [
        .preview,
        .previewLowPlaytime,
        .previewLongName
    ]
}


extension GameDetails {
    static let preview = GameDetails(
        appid: 440,
        name: "Team Fortress 2",
        headerImage: "https://cdn.cloudflare.steamstatic.com/steam/apps/440/header.jpg",
        shortDescription: "Nine distinct classes provide a broad range of tactical abilities and personalities. Constantly updated with new game modes, maps, equipment and, most importantly, hats!",
        developers: ["Valve"],
        publishers: ["Valve"],
        releaseDate: "Oct 10, 2007",
        price: "Free",
        isFree: true,
        genres: ["Action", "Free to Play"],
        categories: ["Multi-player", "Cross-Platform Multiplayer", "Steam Achievements", "Steam Trading Cards", "Steam Workshop"],
        reviews: .preview
    )
    
    static let previewSparse = GameDetails(
        appid: 999999,
        name: "Mystery Game",
        headerImage: nil,
        shortDescription: nil,
        developers: nil,
        publishers: nil,
        releaseDate: nil,
        price: nil,
        isFree: false,
        genres: nil,
        categories: nil,
        reviews: nil
    )
    
    static let previewPaid = GameDetails(
        appid: 1086940,
        name: "Baldur's Gate 3",
        headerImage: "https://cdn.cloudflare.steamstatic.com/steam/apps/1086940/header.jpg",
        shortDescription: "Gather your party and return to the Forgotten Realms in a tale of fellowship and betrayal, sacrifice and survival, and the lure of absolute power.",
        developers: ["Larian Studios"],
        publishers: ["Larian Studios"],
        releaseDate: "Aug 3, 2023",
        price: "$59.99",
        isFree: false,
        genres: ["Adventure", "RPG", "Strategy"],
        categories: ["Single-player", "Multi-player", "Co-op", "Online Co-op", "Steam Achievements"],
        reviews: .previewMixed
    )
}

extension GameReviews {
    static let preview = GameReviews(
        total: 891234,
        score: 9,
        description: "Overwhelmingly Positive"
    )
    
    static let previewMixed = GameReviews(
        total: 2456,
        score: 5,
        description: "Mixed"
    )
}

extension Profile {
    static let preview = Profile(
        steamId: "76561198012345678",
        personaName: "ExamplePlayer",
        profileUrl: "https://steamcommunity.com/id/exampleplayer/",
        avatarSmall: "https://avatars.steamstatic.com/abcd1234_thumb.jpg",
        avatarMedium: "https://avatars.steamstatic.com/abcd1234_medium.jpg",
        avatarFull: "https://avatars.steamstatic.com/abcd1234_full.jpg"
    )
}

extension PredictionResult {
    static let preview = PredictionResult(
        appid: 813780,
        score: 0.87
    )
    
    static let previewLow = PredictionResult(
        appid: 999999,
        score: 0.23
    )
}

extension LoginResponse {
    static let preview = LoginResponse(
        loginUrl: "https://steamcommunity.com/openid/login?openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&openid.mode=checkid_setup"
    )
}

extension GameEntity {
    static func preview(from game: Game) -> GameEntity {
        GameEntity(appid: game.appid, name: game.name, imageUrl: game.imageUrl)
    }
}

extension OwnershipEntry {
    static func preview(from game: Game, gameEntity: GameEntity) -> OwnershipEntry {
        OwnershipEntry(
            game: gameEntity,
            playtime: game.playtime ?? 0,
            playtime2Weeks: game.playtime2weeks
        )
    }
}

extension WishlistEntry {
    static func preview(from gameEntity: GameEntity, dateAdded: Date = Date()) -> WishlistEntry {
        WishlistEntry(game: gameEntity, dateAdded: dateAdded)
    }
}

extension RecommendationEntry {
    static func preview(from gameEntity: GameEntity, score: Double, dateFetched: Date = Date()) -> RecommendationEntry {
        RecommendationEntry(game: gameEntity, score: score, dateFetched: dateFetched)
    }
}

extension ProfileEntity {
    static func preview(from profile: Profile) -> ProfileEntity {
        ProfileEntity(from: profile)
    }
}
#endif
