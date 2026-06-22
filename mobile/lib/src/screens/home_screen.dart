import 'package:flutter/material.dart';

import 'dashboard_screen.dart';
import 'flocks_screen.dart';
import 'prices_screen.dart';
import 'forecasts_screen.dart';
import 'account_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;

  void _goTo(int i) => setState(() => _index = i);

  @override
  Widget build(BuildContext context) {
    final tabs = [
      DashboardScreen(onNavigate: _goTo),
      const FlocksScreen(),
      const PricesScreen(),
      const ForecastsScreen(),
      const AccountScreen(),
    ];
    return Scaffold(
      body: SafeArea(bottom: false, child: tabs[_index]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: _goTo,
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.dashboard_outlined),
              selectedIcon: Icon(Icons.dashboard),
              label: 'Home'),
          NavigationDestination(icon: Icon(Icons.pets), label: 'Flocks'),
          NavigationDestination(
              icon: Icon(Icons.sell_outlined),
              selectedIcon: Icon(Icons.sell),
              label: 'Prices'),
          NavigationDestination(icon: Icon(Icons.show_chart), label: 'Forecasts'),
          NavigationDestination(
              icon: Icon(Icons.person_outline),
              selectedIcon: Icon(Icons.person),
              label: 'Account'),
        ],
      ),
    );
  }
}
