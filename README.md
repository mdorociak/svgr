# SVGR — Steam Video Game Recommender

An iOS companion app for Steam, built with SwiftUI. It lets a user sign in with their Steam account, browse their game library, search the Steam catalog, maintain a wishlist, and receive personalized game recommendations from a machine-learning model.

---

## What it does

- **Sign in with Steam** via the Steam OpenID flow — no manual ID entry.
- **Browse your library** — owned games with playtime, fetched from the Steam Web API.
- **Search the Steam catalog** — debounced search with live results.
- **View game details** — descriptions, developers, reviews, genres, pricing.
- **Maintain a wishlist** — add/remove games, persisted locally across launches.
- **Get recommendations** — personalized suggestions from a recommendation model, persisted and refreshable on demand.
- **Profile & stats** — library stats (game count, total hours, recent playtime, most-played) and a persisted light/dark/system theme preference.

Owned games, wishlist, and recommendations all persist on device, so the app opens to populated content instantly and works without an immediate network round-trip.

---

## Tech stack

**iOS client**
- Swift 6 / SwiftUI
- `@Observable`
- SwiftData with `@Query`- reactive views
- `async/await` 
- Swift Testing for unit tests

**Backend** *
- Python / FastAPI
- Steam Web API + Steam OpenID
- A PyTorch hybrid recommendation model served behind the API

---

## What has been done

- Implemented the full four-layer architecture end to end (models, services, view models, views).
- Built protocol-first networking and caching layers, each with production and mock implementations.
- Designed the SwiftData schema around user–game relationships, with reactive `@Query` views and a single source of truth.
- Integrated Steam OpenID authentication and the Steam Web API; integrated the recommendation backend.
- Added on-device persistence for owned games, wishlist, and recommendations, with manual refresh.
- Built a profile screen with computed library stats and a persisted theme preference.
- Wrote unit tests covering every view model's state transitions, using injected mocks for the service and cache layers.
- Built a SwiftUI preview system with reusable fixtures, mock services, and in-memory `ModelContainer` factories — every component is previewable in isolation.
