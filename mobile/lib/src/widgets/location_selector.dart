import 'package:flutter/material.dart';

class LocationParts {
  LocationParts({
    required this.province,
    required this.district,
    required this.market,
    required this.raw,
  });
  final String province;
  final String district;
  final String market;
  final String raw;
}

class LocationSelector extends StatefulWidget {
  const LocationSelector({
    super.key,
    required this.locations,
    required this.selectedLocation,
    required this.onChanged,
  });

  final List<String> locations;
  final String selectedLocation;
  final ValueChanged<String> onChanged;

  @override
  State<LocationSelector> createState() => _LocationSelectorState();
}

class _LocationSelectorState extends State<LocationSelector> {
  String? _selectedProvince;
  String? _selectedDistrict;
  String? _selectedMarket;

  List<LocationParts> _parsed = [];
  List<String> _provinces = [];
  List<String> _districts = [];
  List<String> _markets = [];

  @override
  void initState() {
    super.initState();
    _parseLocations();
    _setInitialValues();
  }

  @override
  void didUpdateWidget(LocationSelector oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.locations != widget.locations) {
      _parseLocations();
      _setInitialValues();
    } else if (oldWidget.selectedLocation != widget.selectedLocation) {
      _setInitialValues();
    }
  }

  void _parseLocations() {
    _parsed = widget.locations.map((loc) {
      if (loc == 'Rwanda') {
        return LocationParts(
          province: 'National',
          district: 'All',
          market: 'National Average',
          raw: 'Rwanda',
        );
      }
      final parts = loc.split(' / ');
      if (parts.length >= 3) {
        return LocationParts(
          province: parts[0],
          district: parts[1],
          market: parts[2],
          raw: loc,
        );
      }
      return LocationParts(province: loc, district: '', market: '', raw: loc);
    }).toList();

    _provinces = _parsed.map((p) => p.province).toSet().toList()..sort();
  }

  void _setInitialValues() {
    if (_parsed.isEmpty) return;
    final match = _parsed.firstWhere(
      (p) => p.raw == widget.selectedLocation,
      orElse: () => _parsed.first,
    );

    _selectedProvince = match.province;
    _updateDistricts();
    _selectedDistrict = match.district;
    _updateMarkets();
    _selectedMarket = match.market;
  }

  void _updateDistricts() {
    _districts = _parsed
        .where((p) => p.province == _selectedProvince)
        .map((p) => p.district)
        .toSet()
        .toList()
      ..sort();
  }

  void _updateMarkets() {
    _markets = _parsed
        .where((p) =>
            p.province == _selectedProvince && p.district == _selectedDistrict)
        .map((p) => p.market)
        .toSet()
        .toList()
      ..sort();
  }

  void _notifyChange() {
    if (_parsed.isEmpty) return;
    final match = _parsed.firstWhere(
      (p) =>
          p.province == _selectedProvince &&
          p.district == _selectedDistrict &&
          p.market == _selectedMarket,
      orElse: () => _parsed.first,
    );
    widget.onChanged(match.raw);
  }

  @override
  Widget build(BuildContext context) {
    if (_parsed.isEmpty) {
      return const SizedBox.shrink();
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        DropdownButtonFormField<String>(
          value: _selectedProvince,
          isExpanded: true,
          decoration: const InputDecoration(
            labelText: 'Province',
            prefixIcon: Icon(Icons.map_outlined),
          ),
          items: _provinces
              .map((p) => DropdownMenuItem(value: p, child: Text(p)))
              .toList(),
          onChanged: (val) {
            setState(() {
              _selectedProvince = val;
              _updateDistricts();
              _selectedDistrict = _districts.isNotEmpty ? _districts.first : '';
              _updateMarkets();
              _selectedMarket = _markets.isNotEmpty ? _markets.first : '';
            });
            _notifyChange();
          },
        ),
        const SizedBox(height: 12),
        if (_selectedProvince != 'National' && _districts.isNotEmpty) ...[
          DropdownButtonFormField<String>(
            value: _selectedDistrict,
            isExpanded: true,
            decoration: const InputDecoration(
              labelText: 'District',
              prefixIcon: Icon(Icons.location_city_outlined),
            ),
            items: _districts
                .map((d) => DropdownMenuItem(value: d, child: Text(d)))
                .toList(),
            onChanged: (val) {
              setState(() {
                _selectedDistrict = val;
                _updateMarkets();
                _selectedMarket = _markets.isNotEmpty ? _markets.first : '';
              });
              _notifyChange();
            },
          ),
          const SizedBox(height: 12),
        ],
        if (_selectedProvince != 'National' && _markets.isNotEmpty) ...[
          DropdownButtonFormField<String>(
            value: _selectedMarket,
            isExpanded: true,
            decoration: const InputDecoration(
              labelText: 'Market Name',
              prefixIcon: Icon(Icons.place_outlined),
            ),
            items: _markets
                .map((m) => DropdownMenuItem(value: m, child: Text(m)))
                .toList(),
            onChanged: (val) {
              setState(() {
                _selectedMarket = val;
              });
              _notifyChange();
            },
          ),
        ],
      ],
    );
  }
}
