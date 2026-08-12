# RouteStop — Travel/Mapping App Design

A trip-planning app built around one insight the big map apps miss: when
you're mid-route, what matters isn't "what's nearby," it's **"what costs me
the least time to leave and rejoin my route."** The three features below all
fall out of that same underlying capability — the app needs to reason about
your *route*, not just your *point*.

---

## 1. The three core features

### A. Corridor food/gas search ("easy off, easy on")

**Problem with existing apps:** POI search ranks by straight-line or
drive-time distance from your *current position*, so a 4.9-star burger
place 6 minutes off the highway outranks a fine 4.2-star diner that's
literally at the next exit. You don't find out it costs you 14 minutes
round-trip until you've committed.

**What to build instead:**

- **Corridor search, not radius search.** Buffer a polygon along the
  remaining route geometry (e.g. 1–3 miles either side, tighter on
  highways, wider on rural roads) and only search POIs inside it.
- **Rank by "added minutes," not distance.** For each candidate POI,
  compute: `detour_cost = ETA(current → POI → rejoin_point_on_route) −
  ETA(current → rejoin_point_on_route_without_detour)`. This requires a
  routing engine that can do fast multi-leg ETA queries, not just a single
  A→B call.
- **Prefer POIs near highway exits/entrances specifically.** For
  highway trips, weight candidates by proximity to an off-ramp *and* an
  on-ramp that rejoins forward progress (not one that requires backtracking
  or a U-turn). This is the "easy off, easy on" heuristic — it's a
  geometric filter (distance from route to nearest exit ramp, distance from
  POI to that ramp) layered on top of the detour-cost ranking.
- **Show it as "+9 min" chips**, sorted ascending, instead of a distance
  or star-rating sort. Star rating becomes a secondary filter, not the
  primary sort key.

**Feasibility note:** this is the hardest of the three features
computationally, because it means running dozens of routing queries per
search (one ETA calc per candidate POI) in real time. This is solvable with
either (a) a self-hosted routing engine you can hit hard and cheaply
(OSRM/Valhalla), or (b) precomputed isochrones refreshed as you drive, so
"detour cost" is a lookup instead of a live route call.

### B. Impromptu detour with auto-rejoin

**Problem with existing apps:** if you tap a new destination mid-trip, most
apps just replace your route entirely — you lose your original destination
and have to re-search and re-enter it.

**What to build instead:**

- **Waypoint insertion, not route replacement.** The active route becomes
  an ordered list `[current_position, detour_stop, original_destination]`
  (plus any other stops already queued). This is standard multi-waypoint
  routing, but the *product* framing — "add a quick stop" as a distinct,
  lightweight action from "navigate somewhere new" — is what's missing from
  Apple Maps today.
- **One-tap "resume route."** After the detour stop, the app should
  auto-detect arrival (geofence around the stop) and prompt "Resume trip to
  [destination]?" or just silently continue guidance back to the original
  route.
- **ETA cascade.** Every downstream stop's ETA needs to recompute the
  moment a detour is inserted, and if the user has shared ETA/trip status
  (e.g. "share my arrival"), that update needs to propagate.
- **"Quick stop" search should default to corridor search from feature A**
  — i.e., if you say "I need gas," it should favor stations that don't
  wreck your route, not just the closest one.

This feature is mostly a UX/state-machine problem once you have a routing
engine that supports waypoints (all major ones do) — the differentiator is
making insertion and resumption a two-tap flow instead of a full re-plan.

### C. Customer/address book map layer (lightweight CRM on the map)

**Problem with existing apps:** Apple/Google Maps can drop pins for saved
places, but there's no concept of "my book of 20 customers, always visible
as a layer, addable from Contacts or from where I'm currently parked."

**What to build instead:**

- **A saved "layer" of entities**, each with: name, address, lat/lng,
  phone, notes, tags, last-visited date. This is a straightforward
  geocoded contact record — not fundamentally different from a lightweight
  field-sales CRM (Badger Maps, SPOTIO, Map Business Online all do this;
  useful prior art to look at for UX patterns).
- **Two entry paths:**
  1. **Import from device Contacts.** iOS: `CNContactPickerViewController`
     lets the user pick one or more contacts; you pull the postal address
     field and geocode it (Apple's `CLGeocoder`, or a batch geocoding API
     if importing many at once with rate limits in mind).
  2. **"Add current location as a stop."** Reverse-geocode the phone's
     current GPS coordinates to prefill an address, let the user
     name/tag it, save. This is the "I'm parked out front" flow — no
     typing an address at all, just confirm-and-save.
- **Map rendering at scale:** with only ~20 pins this is trivial (no
  clustering needed), but design the pin layer as a toggle-able overlay
  from day one so it scales if the user's book grows into the hundreds
  (then you'll want marker clustering — MapKit/Mapbox/Google Maps SDKs all
  have clustering built in).
- **Useful extras once the base layer exists:** tap a pin → call/text/nav
  to it in one tap; "nearest customers to my route" (this reuses the
  corridor logic from feature A — same geometric-filter idea, applied to
  your own saved pins instead of public POIs); visit logging.

---

## 2. System architecture

```
┌─────────────────────────┐
│   Mobile App (iOS/       │  Map rendering, turn-by-turn UI,
│   Android or cross-plat) │  Contacts picker, background location
└───────────┬──────────────┘
            │ REST/GraphQL
┌───────────▼──────────────┐
│   Backend API             │  Auth, saved-places (CRM) CRUD,
│   (your service)          │  trip/route state, detour-cost orchestration
└───────────┬──────────────┘
            │
   ┌────────┼─────────────────┬───────────────────┐
   ▼                          ▼                    ▼
┌─────────────┐   ┌─────────────────────┐   ┌──────────────┐
│ Routing      │   │ POI / Places search  │   │ Geospatial DB │
│ engine       │   │ provider              │   │ (PostGIS)     │
│ (waypoints,  │   │ (restaurants, gas,   │   │ user's saved  │
│ multi-leg    │   │ etc.)                 │   │ pins, trip    │
│ ETA)         │   │                       │   │ history       │
└─────────────┘   └─────────────────────┘   └──────────────┘
```

**Where the phone vs. backend split matters:** turn-by-turn guidance and
map rendering should stay on-device (latency, offline resilience). The
"which POI costs the fewest minutes" computation can live on-device too if
you use a lightweight routing engine with local cost tables, or on your
backend if you're calling a hosted routing API — either works, but doing
detour-cost ranking purely client-side against a cloud routing API means a
lot of API calls per search, so budget for that in cost/rate-limit planning.

---

## 3. Tech stack options

| Layer | Options | Notes |
|---|---|---|
| Mobile | Native iOS (Swift/MapKit) vs. React Native/Flutter | You said you like Apple Maps' feel — native iOS + MapKit gets you that look/feel and free access to Contacts, CarPlay, and Siri integration for free. Cross-platform costs you some of that polish but doubles your reach. |
| Map rendering/tiles | Apple MapKit, Google Maps SDK, Mapbox | Mapbox is the most customizable (custom styling, offline tiles) and has first-class support for multi-waypoint routing + isochrones — worth serious consideration even on iOS instead of MapKit, specifically because of feature A/B. |
| Routing engine | Mapbox Directions API, Google Routes API, **OSRM** or **Valhalla** (self-hosted, open-source, OSM data) | Self-hosting OSRM/Valhalla is the difference between "detour-cost search costs me $0.005/query forever" and "detour-cost search is financially unworkable at scale," because feature A needs many ETA queries per search. Worth prototyping against a hosted API first, then evaluating self-hosting once you know real query volume. |
| POI/places data | Google Places API, Foursquare Places, **Overture Maps** (free, open) | Overture is worth a hard look — it's a well-maintained open POI dataset (backed by Meta/Microsoft/Amazon/TomTom) that avoids per-query Places API costs. |
| Backend | Node/TypeScript, Python (FastAPI), Go | Any works; pick what you/your team knows. Needs to comfortably do geospatial queries. |
| Database | PostgreSQL + PostGIS | The standard for "find things near this route geometry" queries — ST_DWithin/ST_Buffer against a route LineString is exactly the feature-A corridor query. |
| Contacts import | Apple `Contacts`/`ContactsUI` framework | Native, on-device, no server round-trip needed for the picker itself. |
| Auth/sync | Firebase Auth / Supabase / Auth0 | So the customer book syncs across the user's devices. |

---

## 4. Suggested build order (MVP → full vision)

1. **Phase 0 — Foundation.** Native iOS app, MapKit (or Mapbox) base map,
   basic single-destination routing. Get comfortable with the chosen
   routing SDK's waypoint support early — it's load-bearing for phases 2–3.
2. **Phase 1 — Customer/address book layer (feature C).** Simplest of the
   three, and gives you a usable app fast: CRUD for saved pins, Contacts
   import, "add current location" flow, pin layer toggle.
3. **Phase 2 — Impromptu detour + rejoin (feature B).** Add waypoint
   insertion to the active route and the "resume trip" flow. This is
   mostly state-machine + UX work on top of routing you already integrated
   in phase 0.
4. **Phase 3 — Corridor search with detour-cost ranking (feature A).**
   The hardest phase — build the route-buffer POI query, the detour-cost
   ranking, and the exit/entrance-aware filter. Prototype with a hosted
   routing API to validate the UX before investing in self-hosted routing
   infrastructure for cost control.
5. **Phase 4 — Cross-pollination.** "Nearest customers to my route" reuses
   phase 3's corridor logic against phase 1's saved pins. ETA sharing,
   visit history, CarPlay support.

---

## 5. Key risks / open questions worth deciding early

- **Build native iOS-only first, or cross-platform from day one?** Affects
  map SDK choice and how much of Apple's Contacts/CarPlay integration you
  get for free.
- **Routing cost model:** hosted API (fast to build, costs scale with
  usage — could get expensive given feature A's many-queries-per-search
  pattern) vs. self-hosted OSRM/Valhalla (more ops work, ~fixed cost).
  Worth prototyping on hosted, then measuring real query volume before
  deciding.
- **Data licensing:** Google Places/Maps terms restrict some
  combinations (e.g. you generally can't show Google POI data on a non-Google
  base map). Mapbox + Overture, or Apple MapKit + a separate Places
  provider, avoid that trap — worth confirming licensing terms for whatever
  combination you pick before building on it.
- **Offline support:** useful for the "no signal on the highway" case;
  affects whether you can self-host routing tiles on-device (Valhalla and
  OSRM both support this) vs. depending on connectivity.

---

## 6. App Store / Play Store readiness checklist

Both stores allow this category of app (navigation + lightweight CRM are
well-established categories on both), but a few store-specific requirements
are cheaper to design for now than to retrofit later.

### Permissions & privacy

- [ ] **Location permission tier decided:** "While Using the App" is enough
      for features A and C. "Always"/background is only needed if a future
      version auto-detects arrival at a detour stop (feature B) while the
      app isn't in the foreground — Apple requires a specific, user-facing
      justification string for this tier and reviews it more closely.
      Recommendation: ship with "While Using the App" for v1 and defer
      background tracking to a later release once it's clearly needed.
- [ ] **Specific purpose strings written** for `NSLocationWhenInUseUsageDescription`
      (and `NSLocationAlwaysAndWhenInUseUsageDescription` if/when needed) —
      generic text like "for app functionality" is a common rejection reason.
- [ ] **Contacts import uses the native picker**
      (`CNContactPickerViewController` on iOS / Android's equivalent
      contact-picker intent), not a bulk contacts-read API. The picker lets
      the user choose exactly which contacts to share and — on iOS —
      doesn't even trigger the Contacts permission prompt, which simplifies
      both the review and the privacy story.
- [ ] **App Privacy "nutrition label" (Apple) / Data Safety form (Google Play)
      filled out accurately** — both disclose precise location and contacts
      collection. Reviewers spot-check that the declared labels match actual
      app behavior, so keep this in sync as features change.
- [ ] **Purpose strings + privacy labels reviewed together before every
      submission** — a common rejection is a mismatch between what's
      disclosed and what the code actually does (e.g. adding a new location
      use case without updating the label).

### Map & POI data licensing

- [ ] **Map tile provider and POI/places data provider chosen as a matched
      pair**, with terms confirmed to allow that combination (see §7 below
      — some providers restrict displaying their POI data on a competitor's
      base map). Lock this in before building much UI against it, since
      swapping providers later means redoing search/geocoding integration.
- [ ] **API usage terms reviewed for the specific use case**, particularly
      routing/detour-cost search, since that pattern makes many queries per
      user search — confirm the provider's terms and pricing tier account
      for that query volume, not just typical single-route usage.

### Monetization (if applicable)

- [ ] **In-app purchases routed through Apple IAP / Google Play Billing**
      if charging for any digital tier (e.g. a paid customer-book tier) —
      external payment links for a purely digital feature are not allowed
      on iOS and are restricted on Android.
- [ ] **Subscription terms (if used) match store subscription UI
      requirements** — clear pricing, renewal terms, and an in-app way to
      manage/cancel.

### General submission hygiene

- [ ] **Background location, if ever added, has review notes prepared**
      explaining the specific feature that needs it (App Review often asks).
- [ ] **Account deletion / data export path exists** if user accounts are
      required — both stores increasingly require this for apps that collect
      personal data (Apple has required it since 2022).
- [ ] **Crash-free test pass on a real device** (not just simulator) before
      submission — routing/location bugs are easy to miss in the simulator.

---

## Next steps

Two things worth deciding next:

1. **Map tile + POI data provider pairing** — this is the licensing decision
   that's expensive to change later. Tell me which combination you're
   leaning toward (e.g. Mapbox tiles + Mapbox/Overture POI data, or Apple
   MapKit + a separate Places provider) and I'll dig into that pairing's
   specific terms and cost model.
2. Or pick a feature to turn into buildable specs/code: a clickable
   prototype of the corridor-search ranking (feature A, the hardest one),
   a data model + API spec for the customer book (feature C, the fastest
   to ship), or a comparison of Mapbox vs. MapKit for your specific use
   case.
