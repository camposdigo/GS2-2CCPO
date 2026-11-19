import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'api.dart';
import 'preferences.dart';

class TerritoryState extends ChangeNotifier {
  final TerritoryApi api;
  final TerritoryPreferences preferences;
  Map<String, dynamic>? dashboard;
  List<Map<String, dynamic>> occurrences = [];
  String favoriteRegion = 'Centro';
  String? error;
  DateTime? cachedAt;
  bool loading = false;
  bool offline = false;
  bool _disposed = false;
  int _occurrenceRequest = 0;
  int _cacheGeneration = 0;
  Future<void> _cacheOperation = Future<void>.value();

  TerritoryState({required this.api, TerritoryPreferences? preferences})
    : preferences = preferences ?? DevicePreferences();

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  Future<void> initialize() async {
    try {
      favoriteRegion =
          await preferences.getString('favoriteRegion') ?? 'Centro';
      final saved = await preferences.getString('aggregatedDashboard');
      if (saved != null) {
        final cache = jsonDecode(saved) as Map<String, dynamic>;
        dashboard = Map<String, dynamic>.from(cache['data'] as Map);
        cachedAt = DateTime.tryParse(cache['cachedAt'] as String? ?? '');
        offline = true;
      }
    } catch (_) {
      // Cache é conveniência; ausência ou corrupção não impede buscar a API.
    }
    await refresh();
  }

  Future<void> refresh() async {
    if (loading) return;
    final cacheGeneration = _cacheGeneration;
    loading = true;
    error = null;
    _notify();
    try {
      final data = await api.dashboard();
      dashboard = data;
      offline = false;
      cachedAt = DateTime.now();
      // Apenas contagens agregadas e dados hídricos públicos, nunca descrições.
      try {
        final contents = jsonEncode({
          'cachedAt': cachedAt!.toIso8601String(),
          'data': {
            'occurrences': data['occurrences'],
            'water': data['water'],
            'dataMode': data['dataMode'],
          },
        });
        _cacheOperation = _cacheOperation.catchError((Object _) {}).then((
          _,
        ) async {
          if (cacheGeneration == _cacheGeneration) {
            await preferences.setString('aggregatedDashboard', contents);
          }
        });
        await _cacheOperation;
      } catch (_) {
        // Uma falha de preferência não transforma dados recebidos em offline.
      }
    } catch (exception) {
      offline = true;
      error = exception.toString();
    } finally {
      loading = false;
      _notify();
    }
  }

  Future<void> loadOccurrences({String? category}) async {
    final request = ++_occurrenceRequest;
    occurrences = [];
    _notify();
    final received = await api.occurrences(category: category);
    if (request != _occurrenceRequest || _disposed) return;
    occurrences = received;
    _notify();
  }

  Future<void> saveRegion(String region) async {
    await preferences.setString('favoriteRegion', region.trim());
    favoriteRegion = region.trim();
    _notify();
  }

  Future<void> clearCache() async {
    _cacheGeneration++;
    _cacheOperation = _cacheOperation
        .catchError((Object _) {})
        .then((_) => preferences.remove('aggregatedDashboard'));
    await _cacheOperation;
    if (offline) dashboard = null;
    cachedAt = null;
    _notify();
  }

  @override
  void dispose() {
    _disposed = true;
    api.close();
    super.dispose();
  }
}
