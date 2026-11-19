package territorio;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.OptionalDouble;

/** Template Method: as estrategias herdam as mesmas verificacoes de qualidade. */
public abstract class EstrategiaPrevisao {
    private final int horizonteDias;

    protected EstrategiaPrevisao(int horizonteDias) {
        if (horizonteDias < 1 || horizonteDias > 30) {
            throw new IllegalArgumentException("Use horizonte entre 1 e 30 dias.");
        }
        this.horizonteDias = horizonteDias;
    }

    public final Previsao prever(List<Leitura> historico, LocalDate hoje) {
        List<Leitura> copia = List.copyOf(historico);
        if (copia.size() < 3) return indisponivel("Menos de tres leituras: nao prever.");
        for (int i = 0; i < copia.size(); i++) {
            Leitura atual = copia.get(i);
            if (!atual.confiavel()) return indisponivel("Ha leitura marcada como nao confiavel.");
            if (atual.data().isAfter(hoje)) return indisponivel("Ha leitura com data futura.");
            if (i > 0 && ChronoUnit.DAYS.between(copia.get(i - 1).data(), atual.data()) != 1) {
                return indisponivel("Serie deve ter dias consecutivos e ordem crescente.");
            }
        }
        if (ChronoUnit.DAYS.between(copia.get(copia.size() - 1).data(), hoje) > 1) {
            return indisponivel("Ultima leitura esta desatualizada (mais de um dia).");
        }
        return estimar(copia, horizonteDias);
    }

    protected abstract Previsao estimar(List<Leitura> historico, int horizonteDias);

    protected final Previsao resultado(double estimativa, String explicacao) {
        double limitada = Math.max(0, Math.min(100, estimativa));
        return new Previsao(OptionalDouble.of(limitada), horizonteDias,
                "BAIXA - heuristica sem calibracao probabilistica", explicacao,
                List.of("Demonstracao com dados sinteticos; nao e modelo hidrologico validado.",
                        "Nao incorpora chuva, operacao, demanda ou mudancas de regime.",
                        "Projecao limitada a [0,100]; sem intervalo de previsao calibrado.",
                        "Qualquer restricao na oferta de agua depende de avaliacao humana."));
    }

    private Previsao indisponivel(String motivo) {
        return new Previsao(OptionalDouble.empty(), horizonteDias, "INDISPONIVEL", motivo,
                List.of("Corrigir ou atualizar os dados antes de interpretar o risco."));
    }
}
