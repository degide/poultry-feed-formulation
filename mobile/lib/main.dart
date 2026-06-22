import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'src/session.dart';
import 'src/theme.dart';
import 'src/screens/home_screen.dart';
import 'src/screens/login_screen.dart';

void main() {
  runApp(
    ChangeNotifierProvider(
      create: (_) => Session()..restore(),
      child: const FeedApp(),
    ),
  );
}

class FeedApp extends StatelessWidget {
  const FeedApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Feed Formulation',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      home: const _Gate(),
    );
  }
}

/// A gate that shows a loading spinner while the session is restoring, then
/// either the home screen or the login screen depending on whether the user is
/// logged in.
class _Gate extends StatelessWidget {
  const _Gate();

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    if (session.restoring) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return session.isLoggedIn ? const HomeScreen() : const LoginScreen();
  }
}
