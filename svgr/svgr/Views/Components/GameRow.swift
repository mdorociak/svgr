
import SwiftUI

struct GameRow: View {
    
    let game: Game
    
    var body: some View {
        HStack(spacing: 12) {
            AsyncImage(url: URL(string: game.imageUrl ?? "")) { image in
                image
                    .resizable()
                    .aspectRatio(contentMode: .fill)
            } placeholder: {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.3))
                    .overlay {
                        Image(systemName: "gamecontroller.fill")
                            .foregroundStyle(.gray)
                    }
            }
            .frame(width: 48, height: 48)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            
            VStack(alignment: .leading, spacing: 4) {
                Text(game.name)
                    .font(.headline)
                    .lineLimit(1)
                
                if let score = game.scorePercentage {
                    HStack(spacing: 4) {
                        Image(systemName: "sparkles")
                            .foregroundStyle(.purple)
                            .font(.caption)
                        
                        Text("\(score)% match")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } else if let playtime = game.playtime, playtime > 0 {
                    Text(game.playtimeFormatted)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            
            Spacer()
        }
        .padding(.vertical, 4)
    }
}


#Preview("Owned with playtime") {
    List {
        GameRow(game: .preview)
        GameRow(game: .previewLowPlaytime)
        GameRow(game: .previewLongName)
    }
    .listStyle(.plain)
}

#Preview("Recommendation with score") {
    List {
        GameRow(game: .previewRecommendation)
        ForEach(Game.previewRecommendations) { game in
            GameRow(game: game)
        }
    }
    .listStyle(.plain)
}

#Preview("Search result (no playtime, no score)") {
    List {
        GameRow(game: .previewSearchResult)
    }
    .listStyle(.plain)
}
