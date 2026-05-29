
import SwiftUI

struct ProfileScreen: View {
    
    let viewModel: ProfileViewModel
    let loginViewModel: LoginViewModel
    let gamesViewModel: GamesViewModel
    
    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.state {
                case .idle:
                    ContentUnavailableView("No Profile", systemImage: "person")
                case .loading:
                    ProgressView("Loading Profile...")
                case .loaded(let profile):
                    ProfileView(profile: profile, onLogout: logout)
                case .error(let message):
                    ContentUnavailableView(
                        "Error",
                        systemImage: "exclamationmark.triangle",
                        description: Text(message)
                    )
                }
            }
            .navigationTitle("Profile")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        guard let steamId = loginViewModel.steamId else { return }
                        Task {
                            await viewModel.syncData(steamId: steamId, gamesViewModel: gamesViewModel)
                        }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(loginViewModel.steamId == nil)
                }
            }
        }
    }
    
    private func logout() {
        loginViewModel.logout()
    }
}
