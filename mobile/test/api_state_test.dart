import 'dart:convert';
import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:territorio_vivo/api.dart';
import 'package:territorio_vivo/state.dart';
import 'support.dart';

void main() {
  test('API serializa os campos de ocorrência e decodifica UTF-8', () async {
    final api = TerritoryApi(
      baseUrl: 'http://localhost:3000',
      client: MockClient((request) async {
        expect(request.url.path, '/api/occurrences');
        expect(request.method, 'POST');
        expect(jsonDecode(request.body), {
          'category': 'buraco',
          'region': 'Centro',
          'description': 'Buraco junto à passagem pública.',
        });
        return http.Response(
          jsonEncode({
            'item': {'protocol': 'TV-01', 'description': 'iluminação'},
          }),
          201,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      }),
    );
    final result = await api.createOccurrence(
      category: 'buraco',
      region: 'Centro',
      description: 'Buraco junto à passagem pública.',
    );
    expect((result['item'] as Map)['protocol'], 'TV-01');
    api.close();
  });

  test(
    'API rejeita indisponibilidade sem fingir resposta bem-sucedida',
    () async {
      final api = TerritoryApi(
        baseUrl: 'http://localhost:3000',
        client: MockClient(
          (_) async => http.Response(
            '{"error":{"code":"STORAGE_UNAVAILABLE","message":"Banco indisponível"}}',
            503,
            headers: {'content-type': 'application/json; charset=utf-8'},
          ),
        ),
      );
      await expectLater(
        api.dashboard(),
        throwsA(
          isA<ApiException>().having(
            (error) => error.message,
            'mensagem',
            'Banco indisponível',
          ),
        ),
      );
      api.close();
    },
  );

  test(
    'Estado guarda somente agregado e restaura cache sinalizando offline',
    () async {
      final storage = MemoryPreferences();
      final online = TerritoryState(
        preferences: storage,
        api: TerritoryApi(
          baseUrl: 'http://localhost:3000',
          client: MockClient(
            (_) async => http.Response(
              jsonEncode({
                'occurrences': {'total': 3},
                'water': {'dataMode': 'real'},
                'dataMode': 'demo',
                'privateDescription': 'NÃO GUARDAR',
              }),
              200,
              headers: {'content-type': 'application/json; charset=utf-8'},
            ),
          ),
        ),
      );
      await online.initialize();
      expect(online.offline, false);
      expect(
        storage.values['aggregatedDashboard'],
        isNot(contains('NÃO GUARDAR')),
      );
      online.dispose();
      final offline = TerritoryState(
        preferences: storage,
        api: TerritoryApi(
          baseUrl: 'http://localhost:3000',
          client: MockClient(
            (_) async => throw http.ClientException('offline'),
          ),
        ),
      );
      await offline.initialize();
      expect(offline.offline, true);
      expect(offline.dashboard?['occurrences'], {'total': 3});
      expect(offline.error, isNotNull);
      expect(offline.loading, false);
      await offline.clearCache();
      expect(offline.dashboard, isNull);
      offline.dispose();
    },
  );

  test('Preferência é persistida e não muda indicadores hídricos', () async {
    final storage = MemoryPreferences();
    final state = TerritoryState(
      preferences: storage,
      api: TerritoryApi(
        baseUrl: 'http://localhost:3000',
        client: MockClient((_) async => http.Response('{}', 200)),
      ),
    );
    await state.saveRegion('Zona Norte');
    expect(storage.values['favoriteRegion'], 'Zona Norte');
    expect(state.favoriteRegion, 'Zona Norte');
    state.dispose();
  });

  test('Filtro novo não é sobrescrito por resposta antiga', () async {
    final first = Completer<http.Response>();
    final state = TerritoryState(
      preferences: MemoryPreferences(),
      api: TerritoryApi(
        baseUrl: 'http://localhost:3000',
        client: MockClient((request) async {
          if (request.url.queryParameters['category'] == 'buraco') {
            return first.future;
          }
          return http.Response('{"items":[{"category":"residuos"}]}', 200);
        }),
      ),
    );
    final oldRequest = state.loadOccurrences(category: 'buraco');
    await state.loadOccurrences(category: 'residuos');
    first.complete(http.Response('{"items":[{"category":"buraco"}]}', 200));
    await oldRequest;
    expect(state.occurrences.single['category'], 'residuos');
    state.dispose();
  });

  test('Limpar cache invalida escrita de uma atualização pendente', () async {
    final response = Completer<http.Response>();
    final storage = MemoryPreferences();
    final state = TerritoryState(
      preferences: storage,
      api: TerritoryApi(
        baseUrl: 'http://localhost:3000',
        client: MockClient((_) => response.future),
      ),
    );
    final refreshing = state.refresh();
    await state.clearCache();
    response.complete(
      http.Response('{"occurrences":{"total":1},"water":{}}', 200),
    );
    await refreshing;
    expect(storage.values.containsKey('aggregatedDashboard'), false);
    state.dispose();
  });
}
