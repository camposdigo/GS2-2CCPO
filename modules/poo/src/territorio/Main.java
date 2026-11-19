package territorio;

import java.time.LocalDate;
import java.util.List;

public final class Main {
    public static void main(String[] args) {
        System.out.println("Territorio Alerta | POO | DADOS SINTETICOS");
        Reservatorio reservatorio = new Reservatorio("res-demo", "RMSP - demonstracao",
                "CODIGO-INTERNO-FICTICIO", 40, 30);
        Sensor sensor = new SensorSimulado(List.of(52.0, 50.0, 48.0, 46.0, 44.0, 42.0, 40.0));
        LocalDate inicio = LocalDate.of(2026, 11, 1);
        for (int i = 0; i < 7; i++) reservatorio.coletar(sensor, inicio.plusDays(i));
        System.out.println(reservatorio.resumoPublico());
        for (EstrategiaPrevisao estrategia : List.of(new Persistencia(7), new TendenciaLinear(7))) {
            Alerta alerta = reservatorio.avaliar(estrategia, inicio.plusDays(6));
            System.out.println("\n" + estrategia.getClass().getSimpleName() + ": " + alerta.nivel());
            System.out.println(alerta.justificativa());
            System.out.println("Confianca: " + alerta.previsao().confianca());
            alerta.previsao().limitacoes().forEach(item -> System.out.println("- " + item));
            System.out.println("Validacao humana obrigatoria: " + alerta.requerValidacaoHumana());
        }
    }
}
