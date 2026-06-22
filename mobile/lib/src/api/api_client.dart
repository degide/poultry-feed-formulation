import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';

/// Raised for any non-2xx response or transport failure.
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

/// Thin wrapper around `http` that injects the base URL and bearer token,
/// decodes JSON, and surfaces server error detail as [ApiException].
class ApiClient {
  ApiClient({http.Client? client}) : _http = client ?? http.Client();

  final http.Client _http;
  String? _token;

  void setToken(String? token) => _token = token;
  bool get hasToken => _token != null;

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final q = query?.map((k, v) => MapEntry(k, '$v'));
    return Uri.parse('${AppConfig.apiBaseUrl}$path')
        .replace(queryParameters: q);
  }

  Map<String, String> _headers({bool json = true}) => {
        if (json) 'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) async {
    final r = await _send(() => _http.get(_uri(path, query), headers: _headers()));
    return _decode(r);
  }

  Future<dynamic> postJson(String path, Map<String, dynamic> body) async {
    final r = await _send(
        () => _http.post(_uri(path), headers: _headers(), body: jsonEncode(body)));
    return _decode(r);
  }

  /// OAuth2 password grant expects form-encoded username/password.
  Future<dynamic> postForm(String path, Map<String, String> form) async {
    final r = await _send(() => _http.post(
          _uri(path),
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            if (_token != null) 'Authorization': 'Bearer $_token',
          },
          body: form,
        ));
    return _decode(r);
  }

  Future<http.Response> _send(Future<http.Response> Function() req) async {
    try {
      return await req().timeout(const Duration(seconds: 30));
    } on Exception catch (e) {
      throw ApiException('Network error: $e');
    }
  }

  dynamic _decode(http.Response r) {
    final ok = r.statusCode >= 200 && r.statusCode < 300;
    if (r.body.isEmpty) {
      if (ok) return null;
      throw ApiException('Request failed', statusCode: r.statusCode);
    }
    dynamic parsed;
    try {
      parsed = jsonDecode(r.body);
    } catch (_) {
      if (ok) return r.body;
      throw ApiException(r.body, statusCode: r.statusCode);
    }
    if (ok) return parsed;
    throw ApiException(_detail(parsed), statusCode: r.statusCode);
  }

  String _detail(dynamic parsed) {
    if (parsed is Map && parsed['detail'] != null) {
      final d = parsed['detail'];
      if (d is String) return d;
      if (d is List && d.isNotEmpty) {
        final first = d.first;
        if (first is Map && first['msg'] != null) return '${first['msg']}';
      }
      return d.toString();
    }
    return 'Request failed';
  }
}
