
import SwiftUI

extension View {
    
    func card() -> some View {
        self
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.gray.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
