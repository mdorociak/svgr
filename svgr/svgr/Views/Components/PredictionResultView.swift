
import SwiftUI

struct PredictionResultView: View {
    
    let score: Int
    
    var body: some View {
        VStack(spacing: 8) {
            Text("\(score)% match")
                .font(.title2)
                .fontWeight(.bold)
            
            Text(description)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .card()
    }
    
    private var description: String {
        switch score {
        case 80...: return "Highly recommended for you!"
        case 60...: return "You'll probably enjoy this"
        case 40...: return "Might be worth a try"
        default: return "May not be your style"
        }
    }
}

#Preview("High match") {
    PredictionResultView(score: 87)
        .padding()
}

#Preview("Medium match") {
    PredictionResultView(score: 65)
        .padding()
}

#Preview("Low match") {
    PredictionResultView(score: 35)
        .padding()
}

#Preview("Very low match") {
    PredictionResultView(score: 12)
        .padding()
}
