import 'dart:async';
import 'package:flutter/material.dart';
import 'state.dart';
import 'widgets.dart';

const categories = {
  'buraco': 'Buraco na via',
  'iluminacao': 'Iluminação pública',
  'residuos': 'Descarte de resíduos',
  'acessibilidade': 'Acessibilidade',
};
const regions = [
  'Centro',
  'Zona Norte',
  'Zona Sul',
  'Zona Leste',
  'Zona Oeste',
];
String number(dynamic value, {int decimals = 2}) =>
    value is num ? value.toStringAsFixed(decimals) : '—';

class TerritoryHome extends StatefulWidget {
  final TerritoryState state;
  const TerritoryHome({super.key, required this.state});
  @override
  State<TerritoryHome> createState() => _TerritoryHomeState();
}

class _TerritoryHomeState extends State<TerritoryHome> {
  int tab = 0;
  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.state,
    builder: (context, _) => Scaffold(
      appBar: AppBar(
        title: const Text('Território Vivo'),
        actions: [
          IconButton(
            tooltip: 'Atualizar indicadores',
            onPressed: widget.state.loading ? null : widget.state.refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Column(
        children: [
          if (widget.state.loading) const LinearProgressIndicator(),
          if (widget.state.offline)
            Semantics(
              liveRegion: true,
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: Text(
                  widget.state.dashboard == null
                      ? 'Sem conexão'
                      : 'Offline · dados em cache',
                ),
              ),
            ),
          Expanded(
            child: switch (tab) {
              0 => DashboardScreen(state: widget.state),
              1 => AlertsScreen(state: widget.state),
              2 => OccurrencesScreen(state: widget.state),
              _ => PreferencesScreen(state: widget.state),
            },
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: tab,
        onDestinationSelected: (index) => setState(() => tab = index),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.space_dashboard_outlined),
            label: 'Painel',
          ),
          NavigationDestination(
            icon: Icon(Icons.notifications_outlined),
            label: 'Alertas',
          ),
          NavigationDestination(
            icon: Icon(Icons.location_city_outlined),
            label: 'Ocorrências',
          ),
          NavigationDestination(icon: Icon(Icons.tune), label: 'Preferências'),
        ],
      ),
    ),
  );
}

class DashboardScreen extends StatelessWidget {
  final TerritoryState state;
  const DashboardScreen({super.key, required this.state});
  @override
  Widget build(BuildContext context) {
    final data = state.dashboard;
    final water = asMap(data?['water']);
    final metrics = asMap(water['metrics']);
    final forecast = asMap(water['forecast']);
    final evaluation = asMap(water['evaluation']);
    final counts = asMap(data?['occurrences']);
    final source = asMap(water['source']);
    final expired =
        forecast['expired'] == true ||
        asMap(water['freshness'])['status'] != 'current';
    return RefreshIndicator(
      onRefresh: state.refresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            decoration: BoxDecoration(
              color: const Color(0xff123f34),
              borderRadius: BorderRadius.circular(24),
            ),
            padding: const EdgeInsets.all(24),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'DADOS QUE CUIDAM DO TERRITÓRIO',
                  style: TextStyle(
                    color: Color(0xffcde9af),
                    letterSpacing: 1.2,
                  ),
                ),
                SizedBox(height: 12),
                Text(
                  'Antecipar para\ncuidar melhor.',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 32,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                SizedBox(height: 12),
                Text(
                  'Infraestrutura e recursos hídricos com evidências e decisão humana.',
                  style: TextStyle(color: Colors.white),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Sua região: ${state.favoriteRegion}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const Text(
            'A preferência personaliza o contexto. Os indicadores hídricos são agregados do Cantareira.',
          ),
          if (state.offline && state.dashboard != null)
            Notice(
              'Cache salvo em ${state.cachedAt?.toLocal().toString().split('.').first ?? 'data desconhecida'}. Sem verificação atual; as previsões podem estar vencidas.',
            ),
          if (state.error != null)
            Notice(state.error!, icon: Icons.error_outline),
          if (data?['dataMode'] == 'demo')
            const Notice(
              'Ocorrências de demonstração. As medições hídricas têm origem indicada separadamente.',
            ),
          if (water['dataMode'] != 'real')
            const Notice(
              'Dados hídricos reais indisponíveis. Nenhuma medição ou previsão é inventada.',
            ),
          InfoCard(
            title: 'Cantareira · volume útil',
            value: '${number(metrics['volumePct'])}%',
            icon: Icons.water_drop_outlined,
          ),
          InfoCard(
            title: 'Ocorrências registradas',
            value: '${counts['total'] ?? '—'}',
            icon: Icons.receipt_long_outlined,
          ),
          InfoCard(
            title: 'Variação em sete dias',
            value: '${number(metrics['change7dPp'])} p.p.',
            icon: Icons.trending_up,
          ),
          if (water['observedAt'] != null)
            Padding(
              padding: const EdgeInsets.all(8),
              child: Text(
                'Observado em ${water['observedAt']} · ${source['name'] ?? 'Fonte não informada'}',
              ),
            ),
          WaterChart(
            series: water['series'] is List ? water['series'] as List : [],
          ),
          if (forecast.isNotEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Projeção acadêmica · ${forecast['targetDate']}',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      '${number(forecast['valuePct'])}% de volume útil',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    Text(
                      'Intervalo empírico: ${number(forecast['lowerPct'])}% a ${number(forecast['upperPct'])}%.',
                    ),
                    Text(
                      'MAE no teste: ${number(asMap(evaluation['test'])['mae'])} p.p. · referência: ${number(asMap(evaluation['baseline'])['mae'])} p.p.',
                    ),
                    Text(
                      'Cobertura observada do intervalo: ${number((asMap(evaluation['interval'])['testCoverage'] as num? ?? 0) * 100, decimals: 1)}%. Sem garantia de cobertura futura.',
                    ),
                    if (expired || state.offline)
                      const Notice(
                        'Dados antigos ou sem verificação atual. Não use esta projeção para decisões operacionais.',
                      ),
                    const SizedBox(height: 8),
                    const Text(
                      'Nenhuma restrição de oferta de água é acionada pelo aplicativo.',
                    ),
                  ],
                ),
              ),
            ),
          const Notice(
            'O app apoia análises. Medidas de alto impacto exigem avaliação humana e consulta às autoridades responsáveis.',
          ),
        ],
      ),
    );
  }
}

class AlertsScreen extends StatelessWidget {
  final TerritoryState state;
  const AlertsScreen({super.key, required this.state});
  @override
  Widget build(BuildContext context) {
    final water = asMap(state.dashboard?['water']);
    final alerts = water['alerts'] is List ? water['alerts'] as List : [];
    final coverage = asMap(
      asMap(water['evaluation'])['interval'],
    )['testCoverage'];
    final expired =
        asMap(water['forecast'])['expired'] == true ||
        asMap(water['freshness'])['status'] != 'current';
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          'Alertas com contexto',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 12),
        const Notice(
          'Cada sinal precisa ser interpretado com sua fonte, período e limitações. Não há decisão automática de racionamento.',
        ),
        if (expired || state.offline)
          const Notice(
            'Dados antigos ou sem verificação atual. Estes alertas não devem orientar decisões operacionais.',
            icon: Icons.schedule,
          ),
        if (alerts.isEmpty)
          const Notice(
            'Nenhum alerta disponível. Isso não comprova ausência de risco.',
          ),
        for (final raw in alerts)
          Builder(
            builder: (context) {
              final alert = asMap(raw);
              final limitations = alert['limitations'] is List
                  ? alert['limitations'] as List
                  : [];
              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.info_outline),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              '${alert['title'] ?? 'Alerta'}',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Text(
                        '${alert['justification'] ?? 'Justificativa indisponível.'}',
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Confiança: ${alert['confidence'] == null ? 'sem probabilidade calibrada de acerto' : readable(alert['confidence'])}.',
                      ),
                      if (coverage is num)
                        Text(
                          'Cobertura empírica do intervalo no teste: ${number(coverage * 100, decimals: 1)}%.',
                        ),
                      const SizedBox(height: 10),
                      const Text(
                        'Limitações',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      for (final limitation in limitations)
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text('• $limitation'),
                        ),
                      const SizedBox(height: 12),
                      const Text(
                        'Revisão humana necessária.',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
      ],
    );
  }
}

class OccurrencesScreen extends StatefulWidget {
  final TerritoryState state;
  const OccurrencesScreen({super.key, required this.state});
  @override
  State<OccurrencesScreen> createState() => _OccurrencesScreenState();
}

class _OccurrencesScreenState extends State<OccurrencesScreen> {
  String? category;
  bool loading = false;
  String? error;
  int loadGeneration = 0;
  @override
  void initState() {
    super.initState();
    unawaited(load());
  }

  Future<void> load() async {
    final generation = ++loadGeneration;
    setState(() {
      loading = true;
      error = null;
    });
    try {
      await widget.state.loadOccurrences(category: category);
    } catch (exception) {
      if (mounted && generation == loadGeneration) {
        setState(() => error = exception.toString());
      }
    } finally {
      if (mounted && generation == loadGeneration) {
        setState(() => loading = false);
      }
    }
  }

  Future<void> register() async {
    final created = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => OccurrenceForm(state: widget.state)),
    );
    if (created == true && mounted) {
      await load();
      unawaited(widget.state.refresh());
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      Text(
        'Cuidar começa por registrar',
        style: Theme.of(context).textTheme.headlineMedium,
      ),
      const SizedBox(height: 12),
      FilledButton.icon(
        onPressed: register,
        icon: const Icon(Icons.add),
        label: const Text('Registrar ocorrência'),
      ),
      const SizedBox(height: 16),
      DropdownButtonFormField<String>(
        isExpanded: true,
        itemHeight: null,
        initialValue: category ?? '',
        decoration: const InputDecoration(labelText: 'Filtrar por categoria'),
        items: [
          const DropdownMenuItem(value: '', child: Text('Todas')),
          ...categories.entries.map(
            (entry) =>
                DropdownMenuItem(value: entry.key, child: Text(entry.value)),
          ),
        ],
        onChanged: (value) {
          setState(() => category = value);
          unawaited(load());
        },
      ),
      const SizedBox(height: 12),
      if (loading) const LinearProgressIndicator(),
      if (error != null) Notice(error!, icon: Icons.error_outline),
      if (!loading && error == null && widget.state.occurrences.isEmpty)
        const Notice('Nenhuma ocorrência encontrada para este filtro.'),
      for (final item in widget.state.occurrences)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  categories[item['category']] ?? '${item['category']}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                Text('${item['region']} · ${item['protocol']}'),
                const SizedBox(height: 8),
                Text('${item['description']}'),
                const SizedBox(height: 8),
                Text('Status: ${item['status']} · ${item['createdAt']}'),
              ],
            ),
          ),
        ),
      const Notice(
        'Consulta de até 50 registros por vez no aplicativo. A listagem completa paginada está disponível na API e no portal.',
      ),
    ],
  );
}

class OccurrenceForm extends StatefulWidget {
  final TerritoryState state;
  const OccurrenceForm({super.key, required this.state});
  @override
  State<OccurrenceForm> createState() => _OccurrenceFormState();
}

class _OccurrenceFormState extends State<OccurrenceForm> {
  final form = GlobalKey<FormState>();
  final region = TextEditingController();
  final description = TextEditingController();
  String category = 'buraco';
  bool saving = false;
  String? error;
  @override
  void initState() {
    super.initState();
    region.text = regions.contains(widget.state.favoriteRegion)
        ? widget.state.favoriteRegion
        : 'Centro';
  }

  @override
  void dispose() {
    region.dispose();
    description.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    if (!form.currentState!.validate()) return;
    setState(() {
      saving = true;
      error = null;
    });
    try {
      final result = await widget.state.api.createOccurrence(
        category: category,
        region: region.text,
        description: description.text,
      );
      if (!mounted) return;
      final item = asMap(result['item']);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Ocorrência registrada: ${item['protocol'] ?? 'protocolo disponível no portal'}',
          ),
        ),
      );
      Navigator.pop(context, true);
    } catch (exception) {
      if (mounted) {
        setState(() {
          saving = false;
          error = exception.toString();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Registrar ocorrência')),
    body: Form(
      key: form,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Notice(
            'Informe apenas o bairro ou a região. Não inclua nomes, contatos, placas ou endereço residencial. Este canal acadêmico não atende emergências.',
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            initialValue: category,
            isExpanded: true,
            itemHeight: null,
            decoration: const InputDecoration(labelText: 'Categoria'),
            items: categories.entries
                .map(
                  (entry) => DropdownMenuItem(
                    value: entry.key,
                    child: Text(entry.value),
                  ),
                )
                .toList(),
            onChanged: saving
                ? null
                : (value) => setState(() => category = value!),
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            initialValue: region.text,
            isExpanded: true,
            itemHeight: null,
            decoration: const InputDecoration(labelText: 'Região de São Paulo'),
            items: regions
                .map((name) => DropdownMenuItem(value: name, child: Text(name)))
                .toList(),
            onChanged: saving ? null : (value) => region.text = value!,
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: description,
            enabled: !saving,
            minLines: 4,
            maxLines: 8,
            maxLength: 600,
            decoration: const InputDecoration(
              labelText: 'O que está acontecendo?',
              alignLabelWithHint: true,
            ),
            validator: (value) => (value?.trim().length ?? 0) < 12
                ? 'Descreva o problema com pelo menos 12 caracteres.'
                : (value?.trim().length ?? 0) > 600
                ? 'A descrição ultrapassa o limite permitido.'
                : null,
          ),
          if (error != null) Notice(error!, icon: Icons.error_outline),
          FilledButton(
            onPressed: saving ? null : submit,
            child: Text(saving ? 'Enviando…' : 'Enviar ocorrência'),
          ),
        ],
      ),
    ),
  );
}

class PreferencesScreen extends StatefulWidget {
  final TerritoryState state;
  const PreferencesScreen({super.key, required this.state});
  @override
  State<PreferencesScreen> createState() => _PreferencesScreenState();
}

class _PreferencesScreenState extends State<PreferencesScreen> {
  final form = GlobalKey<FormState>();
  late final region = TextEditingController(text: widget.state.favoriteRegion);
  @override
  void dispose() {
    region.dispose();
    super.dispose();
  }

  Future<void> save() async {
    if (!form.currentState!.validate()) return;
    try {
      await widget.state.saveRegion(region.text);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Preferência salva neste dispositivo.')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Não foi possível salvar a preferência.'),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(20),
    children: [
      Text('Seu contexto', style: Theme.of(context).textTheme.headlineMedium),
      const SizedBox(height: 16),
      Form(
        key: form,
        child: DropdownButtonFormField<String>(
          initialValue: regions.contains(region.text) ? region.text : 'Centro',
          isExpanded: true,
          itemHeight: null,
          decoration: const InputDecoration(labelText: 'Região favorita'),
          items: regions
              .map((name) => DropdownMenuItem(value: name, child: Text(name)))
              .toList(),
          onChanged: (value) => region.text = value!,
        ),
      ),
      FilledButton(onPressed: save, child: const Text('Salvar preferência')),
      const SizedBox(height: 16),
      const Notice(
        'Persistência local: região favorita e último painel agregado. Descrições das ocorrências não são guardadas no cache do app.',
      ),
      OutlinedButton.icon(
        onPressed: () async {
          try {
            await widget.state.clearCache();
            if (context.mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Cache de indicadores removido.')),
              );
            }
          } catch (_) {
            if (context.mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Não foi possível remover o cache.'),
                ),
              );
            }
          }
        },
        icon: const Icon(Icons.delete_outline),
        label: const Text('Limpar cache de indicadores'),
      ),
      const SizedBox(height: 24),
      const Text(
        'Território Vivo · GS 2026.2',
        style: TextStyle(fontWeight: FontWeight.bold),
      ),
      const Text(
        'Protótipo acadêmico. Dados hídricos agregados do Cantareira, com atribuição à Sabesp. Não representa disponibilidade por bairro.',
      ),
      const SizedBox(height: 12),
      const Text(
        'Acessibilidade: componentes Material com rótulos, suporte ao aumento de texto, descrição textual do gráfico e alertas que não dependem apenas de cores.',
      ),
      const SizedBox(height: 12),
      Text('API: ${widget.state.api.baseUrl}'),
    ],
  );
}
