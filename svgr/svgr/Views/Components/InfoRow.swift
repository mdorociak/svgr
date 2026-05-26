
import SwiftUI

struct InfoRow: View {
    
    let label: String
    let value: String
    
    var body: some View {
        HStack {
            Text(label)
                .foregroundStyle(.secondary)
            
            Spacer()
            
            Text(value)
                .multilineTextAlignment(.trailing)
        }
    }
}

#Preview {
    VStack(spacing: 12) {
        InfoRow(label: "Developer", value: "Valve")
        InfoRow(label: "Publisher", value: "Valve")
        InfoRow(label: "Release date", value: "Oct 10, 2007")
        InfoRow(label: "App ID", value: "440")
        InfoRow(label: "Genres", value: "Action, Adventure, Free to Play, Massively Multiplayer")
    }
    .padding()
}
