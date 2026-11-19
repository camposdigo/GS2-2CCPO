package territorio;

import java.time.LocalDate;

/** Contrato para adaptadores reais ou simulados. */
public interface Sensor {
    Leitura ler(LocalDate data);
    String origem();
}
