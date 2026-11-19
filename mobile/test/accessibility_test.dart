import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:territorio_vivo/api.dart';
import 'package:territorio_vivo/screens.dart';
import 'package:territorio_vivo/state.dart';
import 'support.dart';

void main() {
  testWidgets(
    'Painel offline e formulário cabem em 320 pixels com texto ampliado',
    (tester) async {
      tester.view.physicalSize = const Size(320, 568);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final state = TerritoryState(
        preferences: MemoryPreferences(),
        api: TerritoryApi(
          baseUrl: 'http://localhost:3000',
          client: MockClient((_) async => http.Response('{"items":[]}', 200)),
        ),
      );
      state.offline = true;
      state.cachedAt = DateTime(2026, 11, 9);
      state.dashboard = {
        'dataMode': 'demo',
        'occurrences': {'total': 4},
        'water': {'dataMode': 'unavailable'},
      };
      Widget enlarged(Widget child) => MaterialApp(
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(
            context,
          ).copyWith(textScaler: const TextScaler.linear(2)),
          child: child!,
        ),
        home: child,
      );
      await tester.pumpWidget(enlarged(TerritoryHome(state: state)));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(enlarged(OccurrenceForm(state: state)));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      state.dispose();
    },
  );
}
