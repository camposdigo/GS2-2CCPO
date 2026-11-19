package territorio;

import java.util.List;
import java.util.Locale;

/** Regressao linear simples; exemplo de polimorfismo, sem pretensao hidrologica. */
public final class TendenciaLinear extends EstrategiaPrevisao {
    public TendenciaLinear(int horizonteDias) { super(horizonteDias); }

    @Override protected Previsao estimar(List<Leitura> historico, int horizonteDias) {
        int n = historico.size();
        double mediaX = (n - 1) / 2.0;
        double mediaY = historico.stream().mapToDouble(Leitura::nivelPercentual).average().orElseThrow();
        double numerador = 0;
        double denominador = 0;
        for (int i = 0; i < n; i++) {
            numerador += (i - mediaX) * (historico.get(i).nivelPercentual() - mediaY);
            denominador += (i - mediaX) * (i - mediaX);
        }
        double inclinacao = numerador / denominador;
        double estimativa = mediaY + inclinacao * (n - 1 + horizonteDias - mediaX);
        return resultado(estimativa, String.format(Locale.ROOT,
                "Tendencia de %.2f pontos percentuais/dia em %d leituras; projecao para %d dias.",
                inclinacao, n, horizonteDias));
    }
}
