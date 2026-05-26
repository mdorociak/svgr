
import Foundation

struct ProfileDTO: Codable {
    
    let steamId: String
    let personaName: String
    let profileUrl: String
    let avatar: String
    let avatarMedium: String
    let avatarFull: String
    
    enum CodingKeys: String, CodingKey {
        case steamId = "steam_id"
        case personaName = "persona_name"
        case profileUrl = "profile_url"
        case avatar
        case avatarMedium = "avatar_medium"
        case avatarFull = "avatar_full"
    }
}
