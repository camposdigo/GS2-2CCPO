import 'dart:async';
import 'package:flutter/material.dart';
import 'api.dart';
import 'state.dart';
import 'screens.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  const baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:3000',
  );
  runApp(
    TerritoryApp(
      state: TerritoryState(api: TerritoryApi(baseUrl: baseUrl)),
    ),
  );
}

class TerritoryApp extends StatefulWidget {
  final TerritoryState state;
  const TerritoryApp({super.key, required this.state});
  @override
  State<TerritoryApp> createState() => _TerritoryAppState();
}

class _TerritoryAppState extends State<TerritoryApp> {
  @override
  void initState() {
    super.initState();
    unawaited(widget.state.initialize());
  }

  @override
  void dispose() {
    widget.state.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Território Vivo',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff175847)),
      scaffoldBackgroundColor: const Color(0xfff5f5ee),
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
      ),
    ),
    home: TerritoryHome(state: widget.state),
  );
}
