import Foundation

struct Profile: Identifiable, Equatable {
    let steamId: String
    let personaName: String
    let profileUrl: String
    let avatarSmall: String
    let avatarMedium: String
    let avatarFull: String
    
    var id: String { steamId }
}

