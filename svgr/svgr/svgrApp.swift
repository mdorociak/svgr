
import SwiftUI
import SwiftData

@main
struct svgrApp: App {
    
    let modelContainer: ModelContainer
    let cacheService: CacheService
    let steamService: SteamService
    
    @AppStorage("appTheme") private var appTheme: AppTheme = .system
    
    init() {
        do {
            modelContainer = try ModelContainer(
                for: GameEntity.self,
                OwnershipEntry.self,
                WishlistEntry.self,
                RecommendationEntry.self,
                ProfileEntity.self
            )
            cacheService = DefaultCacheService(modelContainer: modelContainer)
            steamService = DefaultSteamService()
        } catch {
            fatalError("Could not initialize ModelContainer: \(error)")
        }
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView(
                steamService: steamService,
                cacheService: cacheService
            )
            .preferredColorScheme(appTheme.colorScheme)
        }
        .modelContainer(modelContainer)
    }
}
