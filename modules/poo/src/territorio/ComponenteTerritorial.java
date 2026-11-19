package territorio;

import java.time.LocalDate;
import java.util.Objects;

public abstract class ComponenteTerritorial {
    private final String id;
    private final String regiaoPublica;

    protected ComponenteTerritorial(String id, String regiaoPublica) {
        this.id = texto(id);
        this.regiaoPublica = texto(regiaoPublica);
    }

    public final String id() { return id; }
    public final String regiaoPublica() { return regiaoPublica; }
    public abstract void coletar(Sensor sensor, LocalDate data);
    public abstract Alerta avaliar(EstrategiaPrevisao estrategia, LocalDate hoje);
    public abstract String resumoPublico();

    protected static String texto(String valor) {
        Objects.requireNonNull(valor);
        if (valor.isBlank()) throw new IllegalArgumentException("Texto obrigatorio.");
        return valor;
    }
}
