
import SwiftUI

struct LoginScreen: View {
    
    @State private var showWebView = false
    let viewModel: LoginViewModel
    
    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            
            Image(systemName: "gamecontroller.fill")
                .font(.system(size: 80))
                .foregroundStyle(.blue)
            
            Text("SVGR")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            Text("Sign in with Steam")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 32)
            
            Spacer()
            
            Button {
                Task { await viewModel.getLoginUrl() }
            } label: {
                Label("Sign in with Steam", systemImage: "person.badge.key.fill")
                    .foregroundStyle(.blue)
                    .card()
            }
            .padding(.horizontal, 32)
            .disabled(viewModel.state.isLoading)
            
            if viewModel.state.isLoading {
                ProgressView()
            }
            
            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }
            Spacer()
        }
        .onChange(of: viewModel.state) { _, newState in
            if case .loaded = newState {
                showWebView = true
            }
        }
        .sheet(isPresented: $showWebView) {
            if case .loaded(let response) = viewModel.state {
                SteamWebView(
                    url: response.loginUrl,
                    onCallback: { steamId in
                        showWebView = false
                        viewModel.handleAuthCallback(steamId: steamId)
                    },
                    onCancel: {
                        showWebView = false
                    }
                )
            }
        }
    }
    
    private var errorMessage: String? {
        if case .error(let message) = viewModel.state {
            return message
        }
        return viewModel.authError
    }
}

#Preview("Idle (before tap)") {
    LoginScreen(
        viewModel: LoginViewModel(steamService: MockSteamService.successful())
    )
}

#Preview("Error") {
    LoginScreen(
        viewModel: LoginViewModel(steamService: MockSteamService.failing())
    )
}
