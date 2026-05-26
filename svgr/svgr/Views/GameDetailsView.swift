import SwiftUI

struct GameDetailsView: View {
    
    let game: Game
    let details: GameDetails
    
    let isOwned: Bool
    let isWishlisted: Bool
    let onToggleWishlist: () -> Void
    
    let predictionState: LoadingState<PredictionResult>
    let onFetchPrediction: () -> Void
    
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                
                headerImage
                
                VStack(alignment: .leading, spacing: 16) {
                    
                    titleSection
                    
                    if let desc = details.shortDescription {
                        Text(desc)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    
                    Divider()
                    
                    ownershipSection
                    
                    Divider()
                    
                    if let reviews = details.reviews {
                        ReviewsSection(reviews: reviews)
                        Divider()
                    }
                    
                    detailsSection
                    
                    if let genres = details.genres, !genres.isEmpty {
                        Divider()
                        TagCloud(title: "Genres", tags: genres)
                    }
                    
                    if let categories = details.categories, !categories.isEmpty {
                        Divider()
                        TagCloud(title: "Categories", tags: categories)
                    }
                }
                .padding(.horizontal)
            }
        }
    }
}

private extension GameDetailsView {
    
    var headerImage: some View {
        AsyncImage(url: URL(string: details.headerImage ?? "")) { image in
            image
                .resizable()
                .aspectRatio(contentMode: .fit)
        } placeholder: {
            Rectangle()
                .fill(Color.gray.opacity(0.3))
                .aspectRatio(16/9, contentMode: .fit)
        }
    }
    
    var titleSection: some View {
        HStack {
            Text(details.name)
                .font(.title2)
                .fontWeight(.bold)
            
            Spacer()
            
            if let price = details.price {
                Text(price)
                    .font(.headline)
                    .foregroundStyle(details.isFree ? .green : .primary)
            }
        }
    }
    
    @ViewBuilder
    var ownershipSection: some View {
        if isOwned {
            playtimeSection
        } else {
            WishlistButton(isWishlisted: isWishlisted, action: onToggleWishlist)
            
            if let score = game.scorePercentage {
                GameSection(title: "For You") {
                    PredictionResultView(score: score)
                }
            } else {
                PredictionSection(
                    state: predictionState,
                    fetchPrediction: onFetchPrediction
                )
            }
        }
    }
    
    var playtimeSection: some View {
        GameSection(title: "Your Playtime") {
            HStack(spacing: 16) {
                PlaytimeCard(label: "Last 2 Weeks", value: game.playtime2weeksFormatted)
                PlaytimeCard(label: "Total", value: game.playtimeFormatted)
            }
        }
    }
    
    var detailsSection: some View {
        GameSection(title: "Details") {
            if let developers = details.developers {
                InfoRow(label: "Developer", value: developers.joined(separator: ", "))
            }
            
            if let publishers = details.publishers {
                InfoRow(label: "Publisher", value: publishers.joined(separator: ", "))
            }
            
            if let releaseDate = details.releaseDate {
                InfoRow(label: "Release Date", value: releaseDate)
            }
            
            InfoRow(label: "App ID", value: "\(details.appid)")
        }
    }
}


private struct PlaytimeCard: View {
    
    let label: String
    let value: String
    
    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.title2)
                .fontWeight(.semibold)
            
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .card()
    }
}


#Preview("Owned (shows playtime)") {
    NavigationStack {
        GameDetailsView(
            game: .preview,
            details: .preview,
            isOwned: true,
            isWishlisted: false,
            onToggleWishlist: {},
            predictionState: .idle,
            onFetchPrediction: {}
        )
        .navigationTitle(Game.preview.name)
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview("Not owned, prediction idle") {
    NavigationStack {
        GameDetailsView(
            game: .previewSearchResult,
            details: .previewPaid,
            isOwned: false,
            isWishlisted: false,
            onToggleWishlist: {},
            predictionState: .idle,
            onFetchPrediction: {}
        )
        .navigationTitle(Game.previewSearchResult.name)
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview("Not owned, wishlisted") {
    NavigationStack {
        GameDetailsView(
            game: .previewSearchResult,
            details: .previewPaid,
            isOwned: false,
            isWishlisted: true,
            onToggleWishlist: {},
            predictionState: .idle,
            onFetchPrediction: {}
        )
        .navigationTitle(Game.previewSearchResult.name)
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview("Not owned, prediction loading") {
    NavigationStack {
        GameDetailsView(
            game: .previewSearchResult,
            details: .previewPaid,
            isOwned: false,
            isWishlisted: false,
            onToggleWishlist: {},
            predictionState: .loading,
            onFetchPrediction: {}
        )
        .navigationTitle(Game.previewSearchResult.name)
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview("Not owned, prediction loaded") {
    NavigationStack {
        GameDetailsView(
            game: .previewSearchResult,
            details: .previewPaid,
            isOwned: false,
            isWishlisted: false,
            onToggleWishlist: {},
            predictionState: .loaded(.preview),
            onFetchPrediction: {}
        )
        .navigationTitle(Game.previewSearchResult.name)
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview("Recommendation (pre-computed score)") {
    NavigationStack {
        GameDetailsView(
            game: .previewRecommendation,
            details: .previewPaid,
            isOwned: false,
            isWishlisted: false,
            onToggleWishlist: {},
            predictionState: .idle,
            onFetchPrediction: {}
        )
        .navigationTitle(Game.previewRecommendation.name)
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview("Sparse details") {
    NavigationStack {
        GameDetailsView(
            game: .previewSearchResult,
            details: .previewSparse,
            isOwned: false,
            isWishlisted: false,
            onToggleWishlist: {},
            predictionState: .idle,
            onFetchPrediction: {}
        )
        .navigationTitle("Mystery Game")
        .navigationBarTitleDisplayMode(.inline)
    }
}
