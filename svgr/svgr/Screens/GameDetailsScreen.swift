
import SwiftUI
import SwiftData

struct GameDetailsScreen: View {
    
    @State private var viewModel: GameDetailsViewModel
    let game: Game
    let cacheService: CacheService
    
    init(game: Game, steamService: SteamService, cacheService: CacheService) {
        self.game = game
        self.cacheService = cacheService
        self.viewModel = GameDetailsViewModel(steamService: steamService, cacheService: cacheService)
    }
    
    var body: some View {
        Group {
            switch viewModel.detailsState {
            case .idle:
                Color.clear
            
            case .loading:
                ProgressView("Loading details...")
                
            case .loaded(let details):
                GameDetailsContent(
                    game: game,
                    details: details,
                    cacheService: cacheService,
                    predictionState: viewModel.predictionState,
                    onFetchPrediction: {
                        Task { await viewModel.fetchPrediction(appid: game.appid) }
                    }
                )
                
            case .error(let message):
                ContentUnavailableView(
                    "Error",
                    systemImage: "exclamationmark.triangle",
                    description: Text(message)
                )
            }
        }
        .navigationTitle(game.name)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await viewModel.fetchGameDetails(appid: game.appid)
        }
    }
}


private struct GameDetailsContent: View {
    
    let game: Game
    let details: GameDetails
    let cacheService: CacheService
    let predictionState: LoadingState<PredictionResult>
    let onFetchPrediction: () -> Void
    
    @Query private var ownership: [OwnershipEntry]
    @Query private var wishlist: [WishlistEntry]
    
    init(
        game: Game,
        details: GameDetails,
        cacheService: CacheService,
        predictionState: LoadingState<PredictionResult>,
        onFetchPrediction: @escaping () -> Void
    ) {
        self.game = game
        self.details = details
        self.cacheService = cacheService
        self.predictionState = predictionState
        self.onFetchPrediction = onFetchPrediction
        
        let appid = game.appid
        _ownership = Query(filter: #Predicate<OwnershipEntry> { $0.game?.appid == appid })
        _wishlist = Query(filter: #Predicate<WishlistEntry> { $0.game?.appid == appid })
    }
    
    var body: some View {
        GameDetailsView(
            game: game,
            details: details,
            isOwned: !ownership.isEmpty,
            isWishlisted: !wishlist.isEmpty,
            onToggleWishlist: { cacheService.toggleWishlist(game) },
            predictionState: predictionState,
            onFetchPrediction: onFetchPrediction
        )
    }
}

#Preview("Loaded — owned game (shows playtime)") {
    NavigationStack {
        GameDetailsScreen(
            game: .preview,                            // Team Fortress 2, appid 440
            steamService: MockSteamService.successful(),
            cacheService: MockCacheService.empty()
        )
    }
    .previewModelContainer(PreviewModelContainer.withMixedRelationships())
}

#Preview("Loaded — wishlisted game (shows wishlist button filled)") {
    NavigationStack {
        GameDetailsScreen(
            game: .previewSearchResult,                // Baldur's Gate 3, appid 1086940
            steamService: MockSteamService.successful(),
            cacheService: MockCacheService.empty(),
        )
    }
    .previewModelContainer(PreviewModelContainer.withMixedRelationships())
}

#Preview("Loaded — unowned game (idle prediction)") {
    NavigationStack {
        GameDetailsScreen(
            game: .previewRecommendation,              // Age of Empires II, appid 813780
            steamService: MockSteamService.successful(),
            cacheService: MockCacheService.withSampleGames()
        )
    }
    .previewModelContainer(PreviewModelContainer.withOwnedGames())
}

#Preview("Error loading details") {
    NavigationStack {
        GameDetailsScreen(
            game: .previewSearchResult,
            steamService: MockSteamService.failing(),
            cacheService: MockCacheService.empty()
        )
    }
    .previewModelContainer(PreviewModelContainer.empty())
}
