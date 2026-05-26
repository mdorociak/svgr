
import SwiftUI

struct PredictionSection: View {
    
    let state: LoadingState<PredictionResult>
    let fetchPrediction: () -> Void
    
    var body: some View {
        GameSection(title: "For You") {
            content
        }
    }
    
    @ViewBuilder
    private var content: some View {
        switch state {
        case .idle:
            Button(action: fetchPrediction) {
                Label("Will I enjoy this game?", systemImage: "sparkles")
            }
            .card()
            
        case .loading:
            ProgressView()
                .card()
            
        case .loaded(let result):
            PredictionResultView(score: result.scorePercentage)
            
        case .error:
            Button("Try Again") {
                fetchPrediction()
            }
            .card()
        }
    }
}
