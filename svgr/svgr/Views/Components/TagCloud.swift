
import SwiftUI

struct TagCloud: View {
    
    let title: String
    let tags: [String]
    
    var body: some View {
        GameSection(title: title) {
            DetailsLayout {
                ForEach(tags, id: \.self) { tag in
                    Text(tag)
                        .font(.caption)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color.blue.opacity(0.1))
                        .clipShape(Capsule())
                }
            }
        }
    }
}

#Preview("Genres") {
    TagCloud(title: "Genres", tags: ["Action", "Adventure", "Free to Play"])
        .padding()
}

#Preview("Many categories (wraps)") {
    TagCloud(title: "Categories", tags: [
        "Single-player",
        "Multi-player",
        "Co-op",
        "Online Co-op",
        "Cross-Platform Multiplayer",
        "Steam Achievements",
        "Steam Trading Cards",
        "Steam Workshop",
        "Stats",
        "Includes level editor"
    ])
    .padding()
}

#Preview("Single tag") {
    TagCloud(title: "Genres", tags: ["Strategy"])
        .padding()
}
