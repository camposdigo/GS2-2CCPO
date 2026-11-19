package territorio;

import java.util.List;

/** Baseline que permite comparar uma estrategia mais complexa com uma simples. */
public final class Persistencia extends EstrategiaPrevisao {
    public Persistencia(int horizonteDias) { super(horizonteDias); }

    @Override protected Previsao estimar(List<Leitura> historico, int horizonteDias) {
        return resultado(historico.get(historico.size() - 1).nivelPercentual(),
                "Persistencia: mantem o ultimo nivel observado durante " + horizonteDias + " dias.");
    }
}
