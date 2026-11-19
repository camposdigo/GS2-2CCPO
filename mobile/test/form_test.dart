import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:territorio_vivo/api.dart';
import 'package:territorio_vivo/screens.dart';
import 'package:territorio_vivo/state.dart';
import 'support.dart';

void main() {
  testWidgets('Formulário inválido não envia requisição', (tester) async {
    var requests = 0;
    final state = TerritoryState(
      preferences: MemoryPreferences(),
      api: TerritoryApi(
        baseUrl: 'http://localhost:3000',
        client: MockClient((_) async {
          requests++;
          return http.Response('{}', 201);
        }),
      ),
    );
    await tester.pumpWidget(MaterialApp(home: OccurrenceForm(state: state)));
    await tester.ensureVisible(find.text('Enviar ocorrência'));
    await tester.tap(find.text('Enviar ocorrência'));
    await tester.pumpAndSettle();
    expect(
      find.text('Descreva o problema com pelo menos 12 caracteres.'),
      findsOneWidget,
    );
    expect(requests, 0);
    state.dispose();
  });

  testWidgets('Falha da API mantém formulário e informa erro', (tester) async {
    final state = TerritoryState(
      preferences: MemoryPreferences(),
      api: TerritoryApi(
        baseUrl: 'http://localhost:3000',
        client: MockClient(
          (_) async => http.Response(
            '{"error":{"code":"STORAGE_UNAVAILABLE","message":"Banco indisponível"}}',
            503,
            headers: {'content-type': 'application/json; charset=utf-8'},
          ),
        ),
      ),
    );
    await tester.pumpWidget(MaterialApp(home: OccurrenceForm(state: state)));
    await tester.enterText(
      find.byType(TextFormField),
      'Buraco na passagem de pedestres.',
    );
    await tester.ensureVisible(find.text('Enviar ocorrência'));
    await tester.tap(find.text('Enviar ocorrência'));
    await tester.pumpAndSettle();
    expect(find.text('Banco indisponível'), findsOneWidget);
    expect(find.text('Buraco na passagem de pedestres.'), findsOneWidget);
    state.dispose();
  });
}
