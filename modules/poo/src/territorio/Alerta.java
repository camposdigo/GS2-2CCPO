package territorio;

public record Alerta(Nivel nivel, String justificativa, Previsao previsao,
                     boolean requerValidacaoHumana) {
    public enum Nivel { DADOS_INSUFICIENTES, ATENCAO, CRITICO, SEM_ALERTA }
}
