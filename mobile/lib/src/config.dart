/// config.
///
/// The base URL can be overridden at build/run time without touching code:
///
///   flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000
///
/// Defaults are per platform:
///   * Android emulator reaches the host machine on 10.0.2.2, not localhost.
///   * iOS simulator / desktop / web use localhost directly.

library;

import 'package:flutter/foundation.dart'
    show kIsWeb, defaultTargetPlatform, TargetPlatform;

class AppConfig {
  static const String _override = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://portstead.com:8000');

  /// REST API base, including the /api/v1 prefix.
  static String get apiBaseUrl {
    if (_override.isNotEmpty) return '$_override/api/v1';
    return 'http://${_defaultHost()}:8000/api/v1';
  }

  static String _defaultHost() {
    if (kIsWeb) return 'localhost';
    if (defaultTargetPlatform == TargetPlatform.android) {
      return '10.0.2.2'; // host loopback as seen from the Android emulator
    }
    return 'localhost';
  }
}
