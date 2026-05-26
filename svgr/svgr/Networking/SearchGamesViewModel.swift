
import Foundation
import Observation

@Observable
class SearchGamesViewModel {
    
    var state: LoadingState<[Game]> = .idle
    private var currentSearchTerm: String = ""
    
    private let steamService: SteamService
    
    init(steamService: SteamService) {
        self.steamService = steamService
    }
    
    func fetch(for searchTerm: String) async {
        self.currentSearchTerm = searchTerm
        
        guard !searchTerm.isEmpty else {
            state = .idle
            return
        }
        
        state = .loading
        
        try? await Task.sleep(for: .milliseconds(500))
        guard !Task.isCancelled else { return }
        
        do {
            let games = try await steamService.searchGames(for: searchTerm, page: 1)
            state = .loaded(games)
        } catch {
            guard currentSearchTerm == searchTerm else { return }
            state = .error(error.localizedDescription)
        }
    }
}
