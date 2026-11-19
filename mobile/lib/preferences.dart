import 'package:shared_preferences/shared_preferences.dart';

abstract interface class TerritoryPreferences {
  Future<String?> getString(String key);
  Future<void> setString(String key, String value);
  Future<void> remove(String key);
}

class DevicePreferences implements TerritoryPreferences {
  final SharedPreferencesAsync storage = SharedPreferencesAsync();
  @override
  Future<String?> getString(String key) => storage.getString(key);
  @override
  Future<void> setString(String key, String value) =>
      storage.setString(key, value);
  @override
  Future<void> remove(String key) => storage.remove(key);
}
