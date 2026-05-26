
import SwiftUI

struct WishlistScreen: View {
    
    let steamService: SteamService
    let cacheService: CacheService
    
    var body: some View {
        NavigationStack {
            GameListView(
                source: .wishlisted,
                steamService: steamService,
                cacheService: cacheService
            )
                .navigationTitle("Wishlist")
        }
    }
}

#Preview("Wishlist with games") {
    WishlistScreen(
        steamService: MockSteamService.successful(),
        cacheService: MockCacheService.empty()
    )
    .previewModelContainer(PreviewModelContainer.withWishlistedGames())
}

#Preview("Empty wishlist") {
    WishlistScreen(
        steamService: MockSteamService.successful(),
        cacheService: MockCacheService.empty()
    )
    .previewModelContainer(PreviewModelContainer.empty())
}
