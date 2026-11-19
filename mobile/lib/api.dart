import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => message;
}

class TerritoryApi {
  final String baseUrl;
  final http.Client client;
  TerritoryApi({required this.baseUrl, http.Client? client})
    : client = client ?? http.Client();

  Future<Map<String, dynamic>> _request(
    String path, {
    Map<String, String>? query,
    Map<String, dynamic>? body,
  }) async {
    final uri = Uri.parse('$baseUrl$path').replace(queryParameters: query);
    http.Response response;
    try {
      response =
          await (body == null
                  ? client.get(uri)
                  : client.post(
                      uri,
                      headers: {'Content-Type': 'application/json'},
                      body: jsonEncode(body),
                    ))
              .timeout(const Duration(seconds: 12));
    } catch (_) {
      throw ApiException('Sem conexão com a API. Confira o servidor e a rede.');
    }
    dynamic payload;
    try {
      payload = jsonDecode(utf8.decode(response.bodyBytes));
    } catch (_) {
      throw ApiException('A API devolveu uma resposta inválida.');
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final error = payload is Map ? payload['error'] : null;
      if (error is Map) {
        final fields = error['fields'];
        final details = fields is List
            ? fields
                  .whereType<Map>()
                  .map((field) => field['message'])
                  .whereType<String>()
                  .join(' ')
            : '';
        throw ApiException(
          '${error['message'] ?? 'Solicitação recusada.'}${details.isEmpty ? '' : ' $details'}',
        );
      }
      throw ApiException(
        error is String
            ? error
            : 'Não foi possível concluir a solicitação (${response.statusCode}).',
      );
    }
    if (payload is! Map<String, dynamic>) {
      throw ApiException('O formato da resposta não é compatível com o app.');
    }
    return payload;
  }

  Future<Map<String, dynamic>> dashboard() => _request('/api/dashboard');
  Future<List<Map<String, dynamic>>> occurrences({String? category}) async {
    final result = await _request(
      '/api/occurrences',
      query: {
        'limit': '50',
        if (category != null && category.isNotEmpty) 'category': category,
      },
    );
    final items = result['items'];
    if (items is! List) throw ApiException('Lista de ocorrências inválida.');
    return items.map((item) => Map<String, dynamic>.from(item as Map)).toList();
  }

  Future<Map<String, dynamic>> createOccurrence({
    required String category,
    required String region,
    required String description,
  }) => _request(
    '/api/occurrences',
    body: {
      'category': category,
      'region': region.trim(),
      'description': description.trim(),
    },
  );

  void close() => client.close();
}
