import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api/api_client.dart';
import 'api/repository.dart';
import 'models/models.dart';

/// Holds auth state for the whole app and exposes the [Repository].
class Session extends ChangeNotifier {
  Session() {
    client = ApiClient();
    repo = Repository(client);
  }

  late final ApiClient client;
  late final Repository repo;

  static const _tokenKey = 'auth_token';

  User? _user;
  bool _restoring = true;

  User? get user => _user;
  bool get isLoggedIn => _user != null;
  bool get restoring => _restoring;

  /// Loads the persisted token (if any) and fetches the current user. If the
  /// token is invalid, clears it and sets [user] to null.
  Future<void> restore() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString(_tokenKey);
      if (token != null && token.isNotEmpty) {
        client.setToken(token);
        _user = await repo.me();
      }
    } catch (_) {
      await _clearToken();
      _user = null;
    } finally {
      _restoring = false;
      notifyListeners();
    }
  }

  Future<void> login(String email, String password) async {
    final token = await repo.login(email, password);
    client.setToken(token);
    await _persist(token);
    _user = await repo.me();
    notifyListeners();
  }

  Future<void> register(String name, String email, String role, String password) async {
    await repo.registerUser(name, email, role, password);
    await login(email, password); // sets token, persists, loads user, notifies
  }

  Future<void> logout() async {
    await _clearToken();
    client.setToken(null);
    _user = null;
    notifyListeners();
  }

  Future<void> _persist(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
  }

  Future<void> _clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
  }
}
