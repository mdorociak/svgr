
import SwiftUI

struct ReviewsSection: View {
    
    let reviews: GameReviews
    
    var body: some View {
        GameSection(title: "Reviews") {
            HStack {
                VStack {
                    Text("\(reviews.score)/10")
                        .font(.title)
                        .fontWeight(.bold)
                    
                    Text(reviews.description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .card()
                
                VStack {
                    Text("\(reviews.total)")
                        .font(.title)
                        .fontWeight(.bold)
                    
                    Text("Total Reviews")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .card()
            }
        }
    }
}


#Preview("Overwhelmingly positive") {
    ReviewsSection(reviews: .preview)
        .padding()
}

#Preview("Mixed") {
    ReviewsSection(reviews: .previewMixed)
        .padding()
}
