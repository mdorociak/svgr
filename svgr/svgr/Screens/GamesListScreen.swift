
import SwiftUI

struct GamesListScreen: View {
    
    let viewModel: GamesViewModel
    let steamService: SteamService
    var cacheService: CacheService
    
    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.state {
                case .idle, .loaded:
                    GameListView(
                        source: .owned,
                        steamService: steamService,
                        cacheService: cacheService
                    )
                case .loading:
                    ProgressView("Loading games...")
                case .error(let message):
                    ContentUnavailableView(
                        "Error",
                        systemImage: "exclamationmark.triangle",
                        description: Text(message)
                    )
                }
            }
            .navigationTitle("My Games")
            .onAppear {
                if case .idle = viewModel.state {
                    viewModel.loadFromCache()
                }
            }
        }
    }
}

#Preview("Loaded with games") {
    GamesListScreen(
        viewModel: {
            let vm = GamesViewModel(
                steamService: MockSteamService.successful(),
                cacheService: MockCacheService.withSampleGames()
            )
            vm.state = .loaded
            return vm
        }(),
        steamService: MockSteamService.successful(),
        cacheService: MockCacheService.withSampleGames()
    )
    .previewModelContainer(PreviewModelContainer.withOwnedGames())
}

#Preview("Empty cache") {
    GamesListScreen(
        viewModel: GamesViewModel(
            steamService: MockSteamService.successful(),
            cacheService: MockCacheService.empty()
        ),
        steamService: MockSteamService.successful(),
        cacheService: MockCacheService.empty()
    )
    .previewModelContainer(PreviewModelContainer.empty())
}
