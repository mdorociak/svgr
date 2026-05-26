
import Foundation

struct LoginResponseDTO: Codable, Equatable {
    let loginUrl: String
    
    enum CodingKeys: String, CodingKey {
        case loginUrl = "login_url"
    }
}

