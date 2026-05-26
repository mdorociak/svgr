
import SwiftUI
import SwiftData

struct ProfileView: View {
    
    var profile: Profile
    let onLogout: () -> Void
    
    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                profileHeader
                
                StatsSection()
                
                SettingsSection()
                
                accountSection
                
                versionFooter
            }
            .padding(.top, 32)
            .padding(.bottom, 32)
        }
    }
}

private extension ProfileView {
    
    var profileHeader: some View {
        VStack(spacing: 16) {
            AsyncImage(url: URL(string: profile.avatarFull)) { image in
                image
                    .resizable()
                    .aspectRatio(contentMode: .fill)
            } placeholder: {
                Circle()
                    .fill(Color.gray.opacity(0.3))
            }
            .frame(width: 120, height: 120)
            .clipShape(Circle())
            
            VStack(spacing: 8) {
                Text(profile.personaName)
                    .font(.title)
                    .fontWeight(.bold)
                
                Text("Steam ID: \(profile.steamId)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            
            if let url = URL(string: profile.profileUrl) {
                Link(destination: url) {
                    Label("View Steam Profile", systemImage: "link")
                        .foregroundStyle(.blue)
                        .card()
                }
                .padding(.horizontal, 32)
            }
        }
    }
    
    var accountSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Account")
                .font(.headline)
                .padding(.horizontal)
            
            Button(role: .destructive) {
                onLogout()
            } label: {
                Label("Sign Out", systemImage: "rectangle.portrait.and.arrow.right")
                    .foregroundStyle(.red)
                    .card()
            }
            .padding(.horizontal)
        }
    }
    
    var versionFooter: some View {
        Text(versionString)
            .font(.caption2)
            .foregroundStyle(.tertiary)
            .padding(.top, 8)
    }
    
    var versionString: String {
        let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "?"
        let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "?"
        return "Version \(version) (\(build))"
    }
}

private struct StatsSection: View {
    
    @Query private var ownership: [OwnershipEntry]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Your Stats")
                .font(.headline)
                .padding(.horizontal)
            
            HStack(spacing: 16) {
                StatCard(value: "\(gameCount)", label: "Games")
                StatCard(value: hoursFormatted(totalMinutes), label: "Total Hours")
                StatCard(value: hoursFormatted(twoWeeksMinutes), label: "Last 2 Weeks")
            }
            .padding(.horizontal)
            
            if let mostPlayed {
                HStack {
                    Text("Most Played")
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text("\(mostPlayed.name) (\(Game.formatMinutes(mostPlayed.playtime)))")
                        .multilineTextAlignment(.trailing)
                        .lineLimit(1)
                }
                .font(.subheadline)
                .padding(.horizontal)
            }
        }
    }
    
    
    private var gameCount: Int { ownership.count }
    
    private var totalMinutes: Int {
        ownership.reduce(0) { $0 + $1.playtime }
    }
    
    private var twoWeeksMinutes: Int {
        ownership.reduce(0) { $0 + ($1.playtime2Weeks ?? 0) }
    }
    
    private var mostPlayed: (name: String, playtime: Int)? {
        guard let top = ownership.max(by: { $0.playtime < $1.playtime }),
              let gameEntity = top.game,
              top.playtime > 0 else { return nil }
        return (name: gameEntity.name, playtime: top.playtime)
    }
    
    private func hoursFormatted(_ minutes: Int) -> String {
        "\(minutes / 60)"
    }
}


private struct StatCard: View {
    let value: String
    let label: String
    
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

private struct SettingsSection: View {
    
    @AppStorage("appTheme") private var appTheme: AppTheme = .system
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Settings")
                .font(.headline)
                .padding(.horizontal)
            
            HStack {
                Text("Theme")
                Spacer()
                Picker("Theme", selection: $appTheme) {
                    ForEach(AppTheme.allCases) { theme in
                        Text(theme.label).tag(theme)
                    }
                }
                .pickerStyle(.menu)
                .labelsHidden()
            }
            .padding(.horizontal)
        }
    }
}
