package territorio;

import java.util.List;
import java.util.Objects;
import java.util.OptionalDouble;

public record Previsao(OptionalDouble nivelProjetado, int horizonteDias, String confianca,
                       String justificativa, List<String> limitacoes) {
    public Previsao {
        Objects.requireNonNull(nivelProjetado);
        Objects.requireNonNull(confianca);
        Objects.requireNonNull(justificativa);
        limitacoes = List.copyOf(limitacoes);
        if (horizonteDias < 1) throw new IllegalArgumentException("Horizonte invalido.");
        if (nivelProjetado.isPresent() && (!Double.isFinite(nivelProjetado.getAsDouble())
                || nivelProjetado.getAsDouble() < 0 || nivelProjetado.getAsDouble() > 100)) {
            throw new IllegalArgumentException("Previsao fora da faixa fisica.");
        }
    }
}
