
import Foundation

extension LoginResponseDTO {
    func toDomain() -> LoginResponse {
        LoginResponse(loginUrl: loginUrl)
    }
}


extension ProfileDTO {
    func toDomain() -> Profile {
        Profile(
            steamId: steamId,
            personaName: personaName,
            profileUrl: profileUrl,
            avatarSmall: avatar,
            avatarMedium: avatarMedium,
            avatarFull: avatarFull
        )
    }
}


extension GameDTO {
    func toDomain() -> Game {
        Game(
            appid: appid,
            name: name,
            imageUrl: buildIconUrl(),
            playtime: playtimeForever,
            playtime2weeks: playtime2weeks,
            score: nil
        )
    }
    
    private func buildIconUrl() -> String? {
        guard !imgIconUrl.isEmpty else { return nil }
        if imgIconUrl.hasPrefix("http") {
            return imgIconUrl
        }
        return "https://media.steampowered.com/steamcommunity/public/images/apps/\(appid)/\(imgIconUrl).jpg"
    }
}

extension GameDetailsDTO {
    func toDomain() -> GameDetails {
        GameDetails(
            appid: appid,
            name: name,
            headerImage: headerImage,
            shortDescription: shortDescription,
            developers: developers,
            publishers: publishers,
            releaseDate: releaseDate,
            price: priceOverview,
            isFree: isFree ?? false,
            genres: genres,
            categories: categories,
            reviews: reviews?.toDomain()
        )
    }
}

extension GameReviewsDTO {
    func toDomain() -> GameReviews {
        GameReviews(
            total: total,
            score: score,
            description: description
        )
    }
}


extension SearchResultDTO {
    func toDomain() -> Game {
        Game(
            appid: appid,
            name: name,
            imageUrl: logo,
            playtime: nil,
            playtime2weeks: nil,
            score: nil
        )
    }
}


extension RecommendedGameDTO {
    func toDomain() -> Game {
        Game(
            appid: appid,
            name: name,
            imageUrl: logo,
            playtime: nil,
            playtime2weeks: nil,
            score: score
        )
    }
}

extension PredictionResponseDTO {
    func toDomain() -> PredictionResult {
        PredictionResult(
            appid: appid,
            score: score
        )
    }
}

extension OwnershipEntry {
    func toDomain() -> Game? {
        guard let game else { return nil }
        return Game(
            appid: game.appid,
            name: game.name,
            imageUrl: game.imageUrl,
            playtime: game.ownershipEntry?.playtime,
            playtime2weeks: game.ownershipEntry?.playtime2Weeks,
            score: nil
        )
    }
}

extension WishlistEntry {
    func toDomain() -> Game? {
        guard let game else { return nil }
        return Game(
            appid: game.appid,
            name: game.name,
            imageUrl: game.imageUrl,
            playtime: nil,
            playtime2weeks: nil,
            score: nil
        )
    }
}

extension RecommendationEntry {
    func toDomain() -> Game? {
        guard let game else { return nil }
        return Game(
            appid: game.appid,
            name: game.name,
            imageUrl: game.imageUrl,
            playtime: nil,
            playtime2weeks: nil,
            score: score
        )
    }
}
