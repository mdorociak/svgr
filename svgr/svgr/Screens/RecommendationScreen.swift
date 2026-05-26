
import SwiftUI

struct RecommendationScreen: View {
    
    let viewModel: RecommendationViewModel
    let steamService: SteamService
    let cacheService: CacheService

    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.state {
                case .idle, .loaded:
                    GameListView(
                        source: .recommended,
                        steamService: steamService,
                        cacheService: cacheService
                    )
                case .loading:
                    ProgressView("Generating recommendations...")
                case .error(let message):
                    ContentUnavailableView(
                        "Error",
                        systemImage: "exclamationmark.triangle",
                        description: Text(message)
                    )
                }
            }
            .navigationTitle("For You")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task {
                            await viewModel.refreshRecommendations()
                        }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }
        }
    }
}


#Preview("Loaded with persisted recommendations") {
    let cache = MockCacheService.withSampleRecommendations()
    let steam = MockSteamService.successful()
    let vm = RecommendationViewModel(steamService: steam, cacheService: cache)
    vm.state = .loaded
    
    return RecommendationScreen(
        viewModel: vm,
        steamService: steam,
        cacheService: cache
    )
    .previewModelContainer(PreviewModelContainer.withRecommendations())
}

#Preview("Empty (never refreshed)") {
    RecommendationScreen(
        viewModel: RecommendationViewModel(
            steamService: MockSteamService.successful(),
            cacheService: MockCacheService.empty()
        ),
        steamService: MockSteamService.successful(),
        cacheService: MockCacheService.empty()
    )
    .previewModelContainer(PreviewModelContainer.empty())
}

#Preview("Error") {
    let cache = MockCacheService.withSampleGames()
    let steam = MockSteamService.failing()
    
    return RecommendationScreen(
        viewModel: RecommendationViewModel(steamService: steam, cacheService: cache),
        steamService: steam,
        cacheService: cache
    )
    .previewModelContainer(PreviewModelContainer.withOwnedGames())
}
