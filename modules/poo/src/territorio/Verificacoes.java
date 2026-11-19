package territorio;

import java.time.LocalDate;
import java.util.List;

/** Verificacoes executaveis, independentes de JUnit e da flag -ea. */
public final class Verificacoes {
    private static int verificacoes;
    private static void verificar(boolean condicao, String mensagem) {
        if (!condicao) throw new AssertionError(mensagem);
        verificacoes++;
    }
    private static void rejeitar(Runnable acao, Class<? extends Throwable> tipo) {
        try { acao.run(); }
        catch (Throwable erro) {
            verificar(tipo.isInstance(erro), "Tipo de erro inesperado: " + erro);
            return;
        }
        throw new AssertionError("Entrada invalida foi aceita.");
    }
    public static void main(String[] args) {
        LocalDate hoje = LocalDate.of(2026, 11, 9);
        Reservatorio r = new Reservatorio("teste", "Regiao agregada", "NAO-EXIBIR", 40, 30);
        Sensor sensor = new SensorSimulado(List.of(44.0, 42.0, 40.0));
        for (int i = 0; i < 3; i++) r.coletar(sensor, hoje.minusDays(2 - i));
        Alerta tendencia = r.avaliar(new TendenciaLinear(7), hoje);
        verificar(tendencia.nivel() == Alerta.Nivel.CRITICO, "Queda deve produzir alerta critico.");
        verificar(Math.abs(tendencia.previsao().nivelProjetado().orElseThrow() - 26) < 1e-8,
                "Regressao da serie linear deve projetar 26%.");
        verificar(tendencia.justificativa().contains("-2.00"), "Alerta deve explicar a tendencia.");
        verificar(tendencia.requerValidacaoHumana(), "Nao pode autorizar racionamento automaticamente.");
        verificar(r.avaliar(new Persistencia(7), hoje).nivel() == Alerta.Nivel.ATENCAO,
                "Baseline precisa diferir da tendencia neste caso.");
        verificar(!r.toString().contains("NAO-EXIBIR"), "Referencia restrita vazou.");
        rejeitar(() -> r.historicoAgregado().clear(), UnsupportedOperationException.class);
        rejeitar(() -> r.coletar(new SensorSimulado(List.of(41.0)), hoje), IllegalArgumentException.class);
        rejeitar(() -> new Leitura(hoje, Double.NaN, true), IllegalArgumentException.class);
        rejeitar(() -> new Leitura(hoje, 101, true), IllegalArgumentException.class);
        rejeitar(() -> new Reservatorio("x", "y", "z", 20, 30), IllegalArgumentException.class);
        rejeitar(() -> new Persistencia(0), IllegalArgumentException.class);
        verificar(r.avaliar(new TendenciaLinear(7), hoje.plusDays(2)).nivel()
                == Alerta.Nivel.DADOS_INSUFICIENTES, "Dados antigos devem impedir previsao.");
        EstrategiaPrevisao estrategia = new TendenciaLinear(7);
        verificar(estrategia.prever(List.of(new Leitura(hoje, 40, true)), hoje).nivelProjetado().isEmpty(),
                "Serie insuficiente deve ser recusada.");
        verificar(estrategia.prever(List.of(new Leitura(hoje.minusDays(2), 50, true),
                new Leitura(hoje.minusDays(1), 49, false), new Leitura(hoje, 48, true)), hoje)
                .nivelProjetado().isEmpty(), "Leitura nao confiavel deve impedir previsao.");
        verificar(estrategia.prever(List.of(new Leitura(hoje.minusDays(4), 50, true),
                new Leitura(hoje.minusDays(1), 49, true), new Leitura(hoje, 48, true)), hoje)
                .nivelProjetado().isEmpty(), "Lacuna temporal deve impedir previsao.");
        verificar(estrategia.prever(List.of(new Leitura(hoje.minusDays(1), 5, true),
                new Leitura(hoje, 3, true), new Leitura(hoje.plusDays(1), 1, true)), hoje)
                .nivelProjetado().isEmpty(), "Datas futuras devem impedir previsao.");
        verificar(estrategia.prever(List.of(new Leitura(hoje.minusDays(2), 5, true),
                new Leitura(hoje.minusDays(1), 3, true), new Leitura(hoje, 1, true)), hoje)
                .nivelProjetado().orElseThrow() == 0, "Projecao deve respeitar limite fisico.");
        System.out.println(verificacoes + " verificacoes de POO aprovadas.");
    }
}
