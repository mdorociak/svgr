
import SwiftUI
import WebKit

struct SteamWebView: View {
    
    let url: String
    let onCallback: (String) -> Void
    let onCancel: () -> Void
    
    var body: some View {
        NavigationStack {
            WebView(url: url, onCallback: onCallback)
                .navigationTitle("Steam Login")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cancel") {
                            onCancel()
                        }
                    }
                }
        }
    }
}

struct WebView: UIViewRepresentable {
    let url: String
    let onCallback: (String) -> Void
    
    func makeCoordinator() -> Coordinator {
        Coordinator(onCallback: onCallback)
    }
    
    func makeUIView(context: Context) -> WKWebView {
        let webView = WKWebView()
        webView.navigationDelegate = context.coordinator
        
        if let url = URL(string: url) {
            webView.load(URLRequest(url: url))
        }
        return webView
    }
    
    func updateUIView(_ uiView: WKWebView, context: Context) {}
    
    class Coordinator: NSObject, WKNavigationDelegate {
        let onCallback: (String) -> Void
        
        init(onCallback: @escaping (String) -> Void) {
            self.onCallback = onCallback
        }
        
        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            
            if let url = navigationAction.request.url,
               url.scheme == "svgr" {
                
                let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
                let steamId = components?.queryItems?.first(where: { $0.name == "steam_id" })?.value
                
                if let steamId = steamId {
                    onCallback(steamId)
                }
                
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }
    }
}
