package territorio;

import java.time.LocalDate;
import java.util.Objects;

/** Leitura agregada diaria; nao identifica pessoas ou domicilios. */
public record Leitura(LocalDate data, double nivelPercentual, boolean confiavel) {
    public Leitura {
        Objects.requireNonNull(data, "data");
        if (!Double.isFinite(nivelPercentual) || nivelPercentual < 0 || nivelPercentual > 100) {
            throw new IllegalArgumentException("Nivel deve estar entre 0 e 100.");
        }
    }
}
