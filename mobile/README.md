# Feed Formulation

Mobile client for the dynamic least-cost poultry feed formulation system. It's a
thin client over the FastAPI backend: the heavy NSGA-II optimisation and the
price-forecasting model run server-side, and the app handles auth, data entry,
launching optimisation jobs, and visualising the results (Pareto front, price
forecasts, ration breakdown).

Built with Flutter (Material 3). State is handled with `provider`; the two charts
(Pareto scatter, forecast line) are drawn with `CustomPainter` rather than a
charting package, so there's one less dependency to resolve.

## Requirements

- Flutter SDK 3.x (`flutter --version`)
- The backend running and reachable. Seed it first:
  `alembic upgrade head`, `seed_ingredients`, `seed_price_history`.

## Setup

```bash
flutter pub get
```

## Pointing the app at the backend

The base URL is resolved in `lib/src/config.dart`:

- **Android emulator**: defaults to `http://10.0.2.2:8000` (the emulator's alias
  for the host machine's `localhost`. Plain `localhost` would resolve to the
  emulator itself).
- **iOS simulator / web / desktop**: defaults to `http://localhost:8000`.
- **Physical device**: pass your machine's LAN IP at run time:

```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000
```

## Run

```bash
flutter run                     # pick a device/emulator when prompted
# or build a release APK:
flutter build apk --release
```

## Screens / flow

| Screen | What it does |
|--------|--------------|
| Login / Register | OAuth2 password login on a branded gradient hero; JWT is stored and the session is restored on next launch |
| Home (dashboard) | Greeting header, at-a-glance stats (flocks, forecasted inputs), model-status card, and quick-action shortcuts into the other tabs |
| Flocks | List and create flocks; tap one for its detail |
| Flock detail | Flock summary + past formulations; launch a new formulation |
| Formulate | Choose market, price mode (latest vs ML forecast), horizon, and engine, then run |
| Result | Polls the optimisation job, draws the Pareto front (NSGA-II points + LP benchmark), lists solutions |
| Ration detail | Composition bars, cost/DTSI metrics, set a ration active, copy as CSV |
| Prices | Latest price per ingredient at a market; add a price |
| Forecasts | Train/refresh the model, per-ingredient forecast charts, walk-forward accuracy table |
| Account | User info, current API endpoint, sign out |

The headline flow for a demo is Flock --> Formulate (forecast mode) --> Result -->
open a solution --> set active. Running the same flock once in "latest" and once in
"forecast" mode shows the ration and cost shifting with the predicted prices.

## Project structure

```
lib/
  main.dart                 # provider + session-restore auth gate
  src/
    config.dart             # API base URL resolution
    session.dart            # auth state (ChangeNotifier), token persistence
    api/
      api_client.dart       # http wrapper: base URL, bearer token, error mapping
      repository.dart       # typed calls for every endpoint used
    models/models.dart      # models mirroring the backend schemas
    widgets/                # async builder, Pareto chart, forecast chart, UI kit (ui.dart)
    screens/                # one file per screen (incl. dashboard)
    theme.dart              # palette + Material 3 theme
```

## Notes

- No offline mode in this version. It needs the backend reachable. An on-device
  reduced NSGA-II + SQLite cache is the planned offline extension.
- Export here copies the ration as CSV to the clipboard; the backend also serves
  PDF/CSV at `GET /formulations/{id}/export` if you want server-rendered files.
