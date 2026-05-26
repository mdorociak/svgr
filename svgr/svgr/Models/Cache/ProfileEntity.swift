
import Foundation
import SwiftData

@Model
class ProfileEntity {
    @Attribute(.unique) var steamId: String
    var personaName: String
    var profileUrl: String
    var avatarSmall: String
    var avatarMedium: String
    var avatarFull: String
    
    var lastUpdated: Date = Date()
    
    init(
        steamId: String,
        personaName: String,
        profileUrl: String,
        avatarSmall: String,
        avatarMedium: String,
        avatarFull: String
    ) {
        self.steamId = steamId
        self.personaName = personaName
        self.profileUrl = profileUrl
        self.avatarSmall = avatarSmall
        self.avatarMedium = avatarMedium
        self.avatarFull = avatarFull
    }
    
    convenience init(from profile: Profile) {
        self.init(
            steamId: profile.steamId,
            personaName: profile.personaName,
            profileUrl: profile.profileUrl,
            avatarSmall: profile.avatarSmall,
            avatarMedium: profile.avatarMedium,
            avatarFull: profile.avatarFull
        )
    }
    
    func toDomain() -> Profile {
        Profile(
            steamId: steamId,
            personaName: personaName,
            profileUrl: profileUrl,
            avatarSmall: avatarSmall,
            avatarMedium: avatarMedium,
            avatarFull: avatarFull
        )
    }
    
    func update(from profile: Profile) {
        personaName = profile.personaName
        profileUrl = profile.profileUrl
        avatarSmall = profile.avatarSmall
        avatarMedium = profile.avatarMedium
        avatarFull = profile.avatarFull
        lastUpdated = Date()
    }
}
