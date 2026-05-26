
import SwiftUI

struct SearchScreen: View {
    
    @State private var searchText: String = ""
    @State private var searchViewModel: SearchGamesViewModel
    let steamService: SteamService
    let cacheService: CacheService
    
    init(steamService: SteamService, cacheService: CacheService) {
        self.steamService = steamService
        self.cacheService = cacheService
        self.searchViewModel = SearchGamesViewModel(steamService: steamService)
    }
    
    var body: some View {
        NavigationStack {
            Group {
                switch searchViewModel.state {
                case .idle:
                    ContentUnavailableView(
                        "Search Games",
                        systemImage: "magnifyingglass",
                        description: Text("Search for any game on Steam")
                    )
                    
                case .loading:
                    ProgressView("Searching...")
                    
                case .loaded(let games):
                    if games.isEmpty {
                        ContentUnavailableView(
                            "No Results",
                            systemImage: "magnifyingglass",
                            description: Text("No games found for \"\(searchText)\"")
                        )
                    } else {
                        GameListView(
                            source: .search(games),
                            steamService: steamService,
                            cacheService: cacheService
                        )
                    }
                    
                case .error(let message):
                    ContentUnavailableView(
                        "Error",
                        systemImage: "exclamationmark.triangle",
                        description: Text(message)
                    )
                }
            }
            .navigationTitle("Search")
            .searchable(text: $searchText, prompt: "Search games...")
            .task(id: searchText) {
                await searchViewModel.fetch(for: searchText)
            }
        }
    }
}

#Preview("Loaded with results") {
    SearchScreen(
        steamService: MockSteamService.successful(),
        cacheService: MockCacheService.empty()
    )
    .previewModelContainer(PreviewModelContainer.empty())
}

#Preview("Error") {
    SearchScreen(
        steamService: MockSteamService.failing(),
        cacheService: MockCacheService.empty()
    )
    .previewModelContainer(PreviewModelContainer.empty())
}
