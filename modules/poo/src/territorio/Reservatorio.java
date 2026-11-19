package territorio;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** Estado mutavel privado; nenhuma colecao interna ou referencia restrita e exposta. */
public final class Reservatorio extends ComponenteTerritorial {
    private final String referenciaOperacionalRestrita;
    private final List<Leitura> leituras = new ArrayList<>();
    private final double limiarAtencao;
    private final double limiarCritico;

    public Reservatorio(String id, String regiaoPublica, String referenciaOperacionalRestrita,
                        double limiarAtencao, double limiarCritico) {
        super(id, regiaoPublica);
        this.referenciaOperacionalRestrita = texto(referenciaOperacionalRestrita);
        if (!Double.isFinite(limiarCritico) || !Double.isFinite(limiarAtencao)
                || limiarCritico < 0 || limiarAtencao > 100 || limiarCritico >= limiarAtencao) {
            throw new IllegalArgumentException("Exige 0 <= critico < atencao <= 100.");
        }
        this.limiarAtencao = limiarAtencao;
        this.limiarCritico = limiarCritico;
    }

    @Override public void coletar(Sensor sensor, LocalDate data) {
        if (!leituras.isEmpty() && !data.isAfter(leituras.get(leituras.size() - 1).data())) {
            throw new IllegalArgumentException("Datas devem ser unicas e crescentes.");
        }
        Leitura leitura = sensor.ler(data);
        if (!leitura.data().equals(data)) throw new IllegalArgumentException("Data divergente do sensor.");
        leituras.add(leitura);
    }

    /** Apenas niveis diarios agregados; a referencia operacional continua privada. */
    public List<Leitura> historicoAgregado() { return List.copyOf(leituras); }

    @Override public Alerta avaliar(EstrategiaPrevisao estrategia, LocalDate hoje) {
        Previsao previsao = estrategia.prever(historicoAgregado(), hoje);
        if (previsao.nivelProjetado().isEmpty()) {
            return new Alerta(Alerta.Nivel.DADOS_INSUFICIENTES, previsao.justificativa(), previsao, true);
        }
        double atual = leituras.get(leituras.size() - 1).nivelPercentual();
        double futuro = previsao.nivelProjetado().getAsDouble();
        double referencia = Math.min(atual, futuro);
        Alerta.Nivel nivel = referencia <= limiarCritico ? Alerta.Nivel.CRITICO
                : referencia <= limiarAtencao ? Alerta.Nivel.ATENCAO : Alerta.Nivel.SEM_ALERTA;
        String justificativa = String.format(Locale.ROOT,
                "Nivel atual %.1f%%, projetado %.1f%%; limiares didaticos: atencao <= %.1f%% e critico <= %.1f%%. %s",
                atual, futuro, limiarAtencao, limiarCritico, previsao.justificativa());
        return new Alerta(nivel, justificativa, previsao, true);
    }

    @Override public String resumoPublico() {
        return id() + " | " + regiaoPublica() + " | " + leituras.size() + " leituras diarias agregadas";
    }

    @Override public String toString() { return resumoPublico(); }
}
