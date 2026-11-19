package territorio;

import java.time.LocalDate;
import java.util.List;

/** Sequencia deterministica e explicitamente sintetica. */
public final class SensorSimulado implements Sensor {
    private final List<Double> niveis;
    private int proximo;

    public SensorSimulado(List<Double> niveis) {
        this.niveis = List.copyOf(niveis);
        if (niveis.isEmpty()) throw new IllegalArgumentException("Forneca leituras sinteticas.");
    }

    @Override public Leitura ler(LocalDate data) {
        if (proximo >= niveis.size()) throw new IllegalStateException("Sensor simulado sem novas amostras.");
        Leitura leitura = new Leitura(data, niveis.get(proximo), true);
        proximo++;
        return leitura;
    }

    @Override public String origem() { return "SINTETICO - demonstracao de POO"; }
}
