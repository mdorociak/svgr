
import SwiftUI

struct WishlistButton: View {
    
    let isWishlisted: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Label(
                isWishlisted ? "Remove from Wishlist" : "Add to Wishlist",
                systemImage: isWishlisted ? "heart.fill" : "heart" 
            )
        }
        .foregroundStyle(isWishlisted ? .red : .blue)
        .card()
    }
}


#Preview("Not wishlisted") {
    WishlistButton(isWishlisted: false, action: {})
        .padding()
}

#Preview("Wishlisted") {
    WishlistButton(isWishlisted: false, action: {})
        .padding()
}
