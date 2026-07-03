# Mobile Client

This directory contains the Dart source code for the Flutter mobile application, which serves as the frontend for the dynamic poultry feed formulation system.

The mobile app operates as a thin client: it communicates with the FastAPI backend to run optimization jobs, fetch price forecasts, retrieve historical logs, and record local market prices.

Android APK: [feed_formulation-debug.apk](../apk/feed_formulation-debug.apk)

## Requirements & Setup

*   **SDK**: Flutter SDK 3.x
*   **Target Platforms**: Android (API 21+), iOS (12.0+)

### Setup Instructions
1.  **Fetch Dependencies**:
    ```bash
    flutter pub get
    ```
2.  **Run in Debug Mode**:
    ```bash
    flutter run
    ```
3.  **Build Release Android APK**:
    ```bash
    flutter build apk --release
    ```


## API Integration & Network Config

The API client base URL is defined in `lib/src/config.dart`. By default, it auto-detects the host platform:
*   **Android Emulators**: Points to `http://10.0.2.2:8000` (the host network gateway alias).
*   **iOS Simulators & Web/Desktop Clients**: Points to `http://localhost:8000`.
*   **Physical Devices**: You must pass your local development machine's LAN IP address during execution:
    ```bash
    flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8000
    ```

## Key App Components

### 1. Cascading Location Selection (`LocationSelector`)
To run forecasts or formulations for specific local markets, the app implements a cascading dropdown module ([LocationSelector](./lib/src/widgets/location_selector.dart)):
*   Loads unique market locations from the API.
*   Presents three sequential dropdowns: **Province**, **District**, and **Market Name**.
*   Ensures that only valid combinations matching the seeded WFP data are submitted to the backend.

### 2. LP vs. NSGA-II Comparison Dashboard
Upon optimization job completion, the results view ([result_screen.dart](.lib/src/screens/result_screen.dart)) renders a comparative analysis of the Linear Programming (LP) baseline vs the cheapest NSGA-II solution:
*   **Price Comparison**: Computes the formulation costs evaluated under both the forecasted price models and the latest actual chosen market prices, displaying the exact RWF difference.
*   **Ration Composition**: Evaluates the percentage of ingredients allocated to the LP and NSGA-II formulations, showing the recipe shift difference.

### 3. Labeled Data Visualizations
*   **Forecast Chart**: Visualizes historical prices alongside forecasted prices and their corresponding 80% confidence bands. The canvas includes X-axis date labels (e.g. `"26-06"`), Y-axis unit labels (`"RWF/kg"`), and a vertical forecast divider line.
*   **Pareto Chart**: Graphs the trade-off frontier solved by NSGA-II (Cost vs. Diet Transition Stability Index). The axes are fully labeled, mapping DTSI along the X-axis and price along the Y-axis.
