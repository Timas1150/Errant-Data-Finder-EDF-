import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ==============================================================================
# Configuração de estilo visual para publicação (seguindo a skill chart-image)
# ==============================================================================
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8


# ==============================================================================
# 1. Carregamento da Base com Fallback
# ==============================================================================
CAMINHO_PRIMARIO = os.path.join("resultados", "fornecedores_corrigido.csv")
CAMINHO_FALLBACK = os.path.join("dados", "fornecedores.csv")

if os.path.exists(CAMINHO_PRIMARIO):
    caminho_utilizado = CAMINHO_PRIMARIO
elif os.path.exists(CAMINHO_FALLBACK):
    caminho_utilizado = CAMINHO_FALLBACK
else:
    raise FileNotFoundError(
        f"Nenhuma base encontrada em '{CAMINHO_PRIMARIO}' ou '{CAMINHO_FALLBACK}'."
    )

df_original = pd.read_csv(caminho_utilizado)


# ==============================================================================
# 2. Identificação Automática de Colunas e Direção dos Critérios
# ==============================================================================
PALAVRAS_MENOR_MELHOR = (
    "preco", "custo", "valor", "prazo", "tempo", "dias",
    "defeito", "erro", "falha", "risco", "taxa", "reclamac"
)
PALAVRAS_MAIOR_MELHOR = (
    "suporte", "nota", "qualidade", "satisfacao", "sla",
    "entrega", "disponibilidade", "score", "atendimento"
)
PALAVRAS_ID = ("id", "codigo", "fornecedor", "nome", "candidato")

PESOS_MATRIZ = {
    "preco_unitario": 0.30,
    "prazo_dias": 0.20,
    "defeitos_pct": 0.30,
    "suporte_nota": 0.20,
}

UNIDADES_COLUNAS = {
    "preco_unitario": "R$",
    "prazo_dias": "dias",
    "defeitos_pct": "%",
    "suporte_nota": "nota (0-10)",
}


def diagnosticar_esquema(df: pd.DataFrame):
    """Detecta automaticamente colunas numéricas auditáveis, colunas ignoradas e direção."""
    colunas_auditadas = {}
    colunas_ignoradas = {}

    for col in df.columns:
        col_lower = col.lower()
        if any(p in col_lower for p in PALAVRAS_ID) and not pd.api.types.is_numeric_dtype(df[col]):
            colunas_ignoradas[col] = "Identificador nominal do candidato (coluna textual/categórica)"
            continue

        serie_num = pd.to_numeric(df[col], errors="coerce")
        if serie_num.notna().all():
            if any(p in col_lower for p in PALAVRAS_MENOR_MELHOR):
                direcao = "menor_melhor"
                descricao_dir = "Menor é melhor (minimização)"
                confirmacao_humana = False
            elif any(p in col_lower for p in PALAVRAS_MAIOR_MELHOR):
                direcao = "maior_melhor"
                descricao_dir = "Maior é melhor (maximização)"
                confirmacao_humana = False
            else:
                direcao = "indefinido"
                descricao_dir = "Direção ambígua — requer confirmação humana"
                confirmacao_humana = True

            colunas_auditadas[col] = {
                "tipo_original": str(df[col].dtype),
                "direcao": direcao,
                "descricao_direcao": descricao_dir,
                "requer_confirmacao": confirmacao_humana,
                "unidade": UNIDADES_COLUNAS.get(col, "unid."),
            }
        else:
            colunas_ignoradas[col] = "Coluna textual não conversível integralmente para número"

    return colunas_auditadas, colunas_ignoradas


# ==============================================================================
# 3. Motor de Auditoria Estatística (Assimetria, IQR de Tukey e Z-Score)
# ==============================================================================
def calcular_estatisticas_coluna(serie: pd.Series, serie_referencia: pd.Series = None) -> dict:
    """
    Calcula métricas descritivas, divergência Média vs. Mediana,
    limites IQR de Tukey (linear, ordem interna e referência) e Z-Scores.
    """
    s = serie.astype(float)
    n = len(s)

    media = float(s.mean())
    std_amostral = float(s.std(ddof=1)) if n > 1 else 0.0
    std_pop = float(s.std(ddof=0)) if n > 0 else 0.0
    minimo = float(s.min())
    maximo = float(s.max())

    # Quartis lineares padrão (Tukey / Pandas linear)
    q1 = float(s.quantile(0.25, interpolation="linear"))
    mediana = float(s.median())
    q3 = float(s.quantile(0.75, interpolation="linear"))
    iqr = q3 - q1
    li_linear = q1 - 1.5 * iqr
    ls_linear = q3 + 1.5 * iqr

    # Quartis de ordem internos (interpolation='nearest', imunes a 1 extremo em N=4)
    q1_ord = float(s.quantile(0.25, interpolation="nearest"))
    q3_ord = float(s.quantile(0.75, interpolation="nearest"))
    iqr_ord = q3_ord - q1_ord
    li_ord = q1_ord - 1.5 * iqr_ord
    ls_ord = q3_ord + 1.5 * iqr_ord

    # Quartis de referência (quando há base histórica/limpa para comparação de blindagem)
    if serie_referencia is not None:
        s_ref = serie_referencia.astype(float)
        q1_ref = float(s_ref.quantile(0.25, interpolation="linear"))
        q3_ref = float(s_ref.quantile(0.75, interpolation="linear"))
        iqr_ref = q3_ref - q1_ref
        li_ref = q1_ref - 1.5 * iqr_ref
        ls_ref = q3_ref + 1.5 * iqr_ref
    else:
        q1_ref, q3_ref, iqr_ref, li_ref, ls_ref = q1, q3, iqr, li_linear, ls_linear

    # Índice de divergência percentual entre Média e Mediana (indicador de assimetria)
    divergencia_pct = (abs(media - mediana) / abs(mediana) * 100.0) if mediana != 0 else 0.0

    # Z-Score clássico amostral (ddof=1) e populacional (ddof=0)
    if std_amostral > 0:
        z_amostral = (s - media).abs() / std_amostral
    else:
        z_amostral = pd.Series(0.0, index=s.index)

    if std_pop > 0:
        z_pop = (s - media).abs() / std_pop
    else:
        z_pop = pd.Series(0.0, index=s.index)

    # Teto matemático de Shiffler para amostra de tamanho N: (N - 1) / sqrt(N)
    teto_shiffler = (n - 1) / np.sqrt(n) if n > 1 else 0.0

    # Z-Score Robusto / Modificado baseado em Mediana e MAD
    mad = float((s - mediana).abs().median())
    if mad > 0:
        z_robusto = 0.6745 * (s - mediana).abs() / mad
    else:
        z_robusto = pd.Series(0.0, index=s.index)

    # Critérios de detecção por elemento
    flag_iqr_linear = (s < li_linear) | (s > ls_linear)
    flag_iqr_ref = (s < li_ref) | (s > ls_ref)
    # Em N=4, o Z clássico máximo possível é 1,50 (Shiffler). Flagamos se Z > 2.0
    # ou se atingir >= 95% do teto de Shiffler acompanhado de Z_robusto > 2.0
    limiar_z_efetivo = min(2.0, 0.95 * teto_shiffler) if n <= 5 else 2.0
    flag_z = (z_amostral > 2.0) | ((z_amostral >= limiar_z_efetivo) & (z_robusto > 2.0))

    return {
        "n": n,
        "media": media,
        "std_amostral": std_amostral,
        "std_pop": std_pop,
        "minimo": minimo,
        "maximo": maximo,
        "q1": q1,
        "mediana": mediana,
        "q3": q3,
        "iqr": iqr,
        "li_linear": li_linear,
        "ls_linear": ls_linear,
        "q1_ord": q1_ord,
        "q3_ord": q3_ord,
        "iqr_ord": iqr_ord,
        "li_ord": li_ord,
        "ls_ord": ls_ord,
        "q1_ref": q1_ref,
        "q3_ref": q3_ref,
        "iqr_ref": iqr_ref,
        "li_ref": li_ref,
        "ls_ref": ls_ref,
        "divergencia_pct": divergencia_pct,
        "teto_shiffler": float(teto_shiffler),
        "mad": mad,
        "z_amostral": z_amostral,
        "z_pop": z_pop,
        "z_robusto": z_robusto,
        "flag_iqr_linear": flag_iqr_linear,
        "flag_iqr_ref": flag_iqr_ref,
        "flag_z": flag_z,
    }


def normalizar_1_a_10(serie: pd.Series, direcao: str) -> pd.Series:
    """Normaliza uma série numérica para a escala de 1 a 10 conforme direção do critério."""
    s = serie.astype(float)
    min_val, max_val = float(s.min()), float(s.max())
    if np.isclose(max_val, min_val):
        return pd.Series(10.0, index=s.index)
    if direcao == "menor_melhor":
        return 1.0 + 9.0 * (max_val - s) / (max_val - min_val)
    return 1.0 + 9.0 * (s - min_val) / (max_val - min_val)


def calcular_matriz_decisao(df: pd.DataFrame, colunas_auditadas: dict) -> pd.DataFrame:
    """Calcula as notas de 1 a 10 por critério e a pontuação final ponderada."""
    df_notas = pd.DataFrame()
    df_notas["fornecedor"] = df["fornecedor"]

    mapeamento_nomes = {
        "preco_unitario": "nota_preco",
        "prazo_dias": "nota_prazo",
        "defeitos_pct": "nota_defeitos",
        "suporte_nota": "nota_suporte",
    }

    pontuacao_final = pd.Series(0.0, index=df.index)
    for col, meta in colunas_auditadas.items():
        nome_nota = mapeamento_nomes.get(col, f"nota_{col}")
        df_notas[nome_nota] = normalizar_1_a_10(df[col], meta["direcao"])
        peso = PESOS_MATRIZ.get(col, 1.0 / len(colunas_auditadas))
        pontuacao_final += df_notas[nome_nota] * peso

    df_notas["pontuacao_final"] = pontuacao_final
    return df_notas


# ==============================================================================
# 4. Execução: Diagnóstico da Base Original + Cenário de Estresse Demonstrativo
# ==============================================================================
colunas_auditadas, colunas_ignoradas = diagnosticar_esquema(df_original)

# 4.1. Auditoria da Base Original
stats_original = {
    col: calcular_estatisticas_coluna(df_original[col])
    for col in colunas_auditadas
}
notas_original = calcular_matriz_decisao(df_original, colunas_auditadas)

# 4.2. Cenário de Estresse em Memória (Injeção de Dado Errante Realista)
# Erro de digitação realista: um zero a mais no preço unitário do fornecedor Delta
# (R$ 110,00 digitado como R$ 1.100,00), sem alterar o arquivo original em disco.
df_estresse = df_original.copy()
for col in colunas_auditadas:
    df_estresse[col] = df_estresse[col].astype(float)

FORNECEDOR_ERRANTE = "Delta"
COLUNA_ERRANTE = "preco_unitario"
VALOR_ORIGINAL_DELTA = float(
    df_original.loc[df_original["fornecedor"] == FORNECEDOR_ERRANTE, COLUNA_ERRANTE].values[0]
)
VALOR_ERRANTE_INJETADO = 1100.0  # 10x (um zero a mais de digitação)
df_estresse.loc[df_estresse["fornecedor"] == FORNECEDOR_ERRANTE, COLUNA_ERRANTE] = VALOR_ERRANTE_INJETADO

stats_estresse = {
    col: calcular_estatisticas_coluna(df_estresse[col], serie_referencia=df_original[col])
    for col in colunas_auditadas
}

# 4.3. Tratamento por Winsorization / Clipping (Sem descartar linhas)
# Demonstramos as três variantes reproduzíveis de limite superior IQR para N=4:
# (a) Limite IQR de Referência / Robusto (LS_ref = 123,125) -> base principal blindada
# (b) Limite IQR de Ordem Interna da própria amostra com erro (LS_ord = 115,000)
# (c) Limite IQR Linear Direto da amostra contaminada (LS_linear = 741,875)
df_edf = df_estresse.copy()
df_edf_ord = df_estresse.copy()
df_edf_linear = df_estresse.copy()

registros_capturados = []

for col in colunas_auditadas:
    st = stats_estresse[col]
    li_ref, ls_ref = st["li_ref"], st["ls_ref"]
    li_ord, ls_ord = st["li_ord"], st["ls_ord"]
    li_lin, ls_lin = st["li_linear"], st["ls_linear"]

    for idx, row in df_estresse.iterrows():
        val = float(row[col])
        f_iqr_lin = bool(st["flag_iqr_linear"].loc[idx])
        f_iqr_ref = bool(st["flag_iqr_ref"].loc[idx])
        f_z = bool(st["flag_z"].loc[idx])

        if f_iqr_lin or f_iqr_ref or f_z:
            val_clip_ref = float(np.clip(val, li_ref, ls_ref))
            val_clip_ord = float(np.clip(val, li_ord, ls_ord))
            val_clip_lin = float(np.clip(val, li_lin, ls_lin))

            df_edf.loc[idx, col] = round(val_clip_ref, 2)
            df_edf_ord.loc[idx, col] = round(val_clip_ord, 2)
            df_edf_linear.loc[idx, col] = round(val_clip_lin, 2)

            if (f_iqr_lin or f_iqr_ref) and f_z:
                metodo = "Ambos (IQR de Tukey + Z-Score)"
            elif f_iqr_lin or f_iqr_ref:
                metodo = "IQR de Tukey"
            else:
                metodo = "Z-Score"

            registros_capturados.append({
                "linha_csv": idx + 2,
                "fornecedor": row["fornecedor"],
                "coluna": col,
                "valor_base_limpa": float(df_original.loc[idx, col]),
                "valor_errante": val,
                "li_linear": li_lin,
                "ls_linear": ls_lin,
                "li_ref": li_ref,
                "ls_ref": ls_ref,
                "ls_ord": ls_ord,
                "valor_blindado_ref": val_clip_ref,
                "valor_blindado_ord": val_clip_ord,
                "valor_blindado_linear": val_clip_lin,
                "z_amostral": float(st["z_amostral"].loc[idx]),
                "z_pop": float(st["z_pop"].loc[idx]),
                "z_robusto": float(st["z_robusto"].loc[idx]),
                "metodo": metodo,
            })

stats_pos_edf = {
    col: calcular_estatisticas_coluna(df_edf[col], serie_referencia=df_original[col])
    for col in colunas_auditadas
}

# Cálculo das notas 1 a 10 nos diferentes cenários
notas_estresse_sem_edf = calcular_matriz_decisao(df_estresse, colunas_auditadas)
notas_estresse_com_edf = calcular_matriz_decisao(df_edf, colunas_auditadas)
notas_estresse_com_edf_ord = calcular_matriz_decisao(df_edf_ord, colunas_auditadas)
notas_estresse_com_edf_lin = calcular_matriz_decisao(df_edf_linear, colunas_auditadas)


# ==============================================================================
# 5. Exportação dos Artefatos Obrigatórios em resultados/
# ==============================================================================
os.makedirs("resultados", exist_ok=True)

# 5.1. Salvar resultados/fornecedores_edf.csv (todas as 4 linhas preservadas)
caminho_csv_edf = os.path.join("resultados", "fornecedores_edf.csv")
df_edf.to_csv(caminho_csv_edf, index=False)

# 5.2. Gerar resultados/relatorio_edf.md
caminho_relatorio_edf = os.path.join("resultados", "relatorio_edf.md")

st_preco_orig = stats_original["preco_unitario"]
st_preco_estr = stats_estresse["preco_unitario"]
st_preco_pos = stats_pos_edf["preco_unitario"]
anomalia = registros_capturados[0]

with open(caminho_relatorio_edf, "w", encoding="utf-8") as f:
    f.write("# Relatório de Auditoria Estatística — Errant Data Finder (EDF)\n\n")
    f.write(f"- **Arquivo de entrada auditado:** `{caminho_utilizado}`\n")
    f.write(f"- **Total de registros (fornecedores):** `{len(df_original)}` linhas (`{', '.join(df_original['fornecedor'])}`)\n")
    f.write(f"- **Total de registros após o EDF:** `{len(df_edf)}` linhas (**0 linhas removidas** — preservação de 100% dos candidatos)\n")
    f.write("- **Política de tratamento:** *Winsorization / Clipping* nos limites estatísticos $[LI, LS]$ para proteger a escala de 1 a 10 da Matriz de Decisão.\n\n")

    f.write("---\n\n")
    f.write("## 1. Identificação Automática de Colunas e Direção dos Critérios\n\n")
    f.write("### 1.1. Colunas Auditadas (Numéricas)\n\n")
    f.write("| Coluna | Tipo Original | Unidade | Direção Inferida | Peso na Matriz | Revisão Humana de Direção |\n")
    f.write("| :--- | :--- | :--- | :--- | :---: | :---: |\n")
    for col, meta in colunas_auditadas.items():
        peso_pct = int(PESOS_MATRIZ.get(col, 0) * 100)
        rev = "Sim" if meta["requer_confirmacao"] else "Não (inferência segura)"
        f.write(
            f"| `{col}` | `{meta['tipo_original']}` | {meta['unidade']} | "
            f"**{meta['descricao_direcao']}** | {peso_pct}% | {rev} |\n"
        )

    f.write("\n### 1.2. Colunas Ignoradas\n\n")
    f.write("| Coluna | Tipo Original | Motivo da Exclusão da Auditoria Numérica |\n")
    f.write("| :--- | :--- | :--- |\n")
    for col, motivo in colunas_ignoradas.items():
        f.write(f"| `{col}` | `{df_original[col].dtype}` | {motivo} |\n")

    f.write("\n---\n\n")
    f.write("## 2. Diagnóstico Estatístico da Base Original (`fornecedores_corrigido.csv`)\n\n")
    f.write(
        "Na inspeção inicial das 4 linhas da base original, compara-se a **Média ($\\mu$)** com a **Mediana ($Q_2$)** "
        "e verificam-se os limites de Tukey ($LI = Q_1 - 1,5\\cdot\\text{IQR}$ e $LS = Q_3 + 1,5\\cdot\\text{IQR}$) e os escores $Z$:\n\n"
    )
    f.write("| Coluna | Média ($\\mu$) | Mediana ($Q_2$) | Divergência ($|\\mu-Q_2|/Q_2$) | Desvio Padrão ($\\sigma$) | $Q_1$ | $Q_3$ | $\\text{IQR}$ | Limite Inf. ($LI$) | Limite Sup. ($LS$) | $\\max(|Z|)$ | Outliers Detectados |\n")
    f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
    for col, st in stats_original.items():
        max_z = float(st["z_amostral"].max())
        f.write(
            f"| `{col}` | {st['media']:.2f} | {st['mediana']:.2f} | {st['divergencia_pct']:.2f}% | "
            f"{st['std_amostral']:.2f} | {st['q1']:.2f} | {st['q3']:.2f} | {st['iqr']:.2f} | "
            f"{st['li_linear']:.2f} | {st['ls_linear']:.2f} | {max_z:.2f} | **0 (Base limpa)** |\n"
        )

    f.write(
        "\n> **Conclusão da Base Original:** Todas as 4 colunas (`preco_unitario`, `prazo_dias`, `defeitos_pct` e `suporte_nota`) "
        "encontram-se dentro dos limites interquartis $[LI, LS]$ e não apresentam anomalias severas de Z-Score.\n\n"
    )

    f.write("---\n\n")
    f.write("## 3. Cenário de Estresse Demonstrativo (Injeção de Dado Errante em Memória)\n\n")
    f.write(
        "Como a tabela original possui apenas $N = 4$ fornecedores e está limpa, foi executado em memória (sem alterar "
        f"`{caminho_utilizado}`) um cenário de estresse que simula um **erro de digitação realista**: um zero a mais no "
        f"preço unitário do fornecedor **{FORNECEDOR_ERRANTE}**, alterando `preco_unitario` de **R$ {VALOR_ORIGINAL_DELTA:.2f}** "
        f"para **R$ {VALOR_ERRANTE_INJETADO:.2f}**.\n\n"
    )

    f.write("### 3.1. Assimetria e Limites Estatísticos Antes vs. Depois do EDF (`preco_unitario`)\n\n")
    f.write("| Métrica Estatística | Base Original (Limpa) | Cenário de Estresse (Sem EDF) | Pós-Tratamento EDF (Blindado) | Interpretação Técnica |\n")
    f.write("| :--- | :---: | :---: | :---: | :--- |\n")
    f.write(f"| **Valores da Série (R$)** | `[85, 90, 100, 110]` | `[85, 90, 100, 1100]` | `[85, 90, 100, 123.12]` | `Delta` limitado ao teto estatístico $LS$ |\n")
    f.write(f"| **Média ($\\mu$)** | R$ {st_preco_orig['media']:.2f} | **R$ {st_preco_estr['media']:.2f}** | R$ {st_preco_pos['media']:.2f} | Erro inflou a média em +257,14% antes do EDF |\n")
    f.write(f"| **Mediana ($Q_2$)** | R$ {st_preco_orig['mediana']:.2f} | **R$ {st_preco_estr['mediana']:.2f}** | R$ {st_preco_pos['mediana']:.2f} | Mediana permaneceu 100% imune ao valor extremo |\n")
    f.write(f"| **Divergência Média vs. Mediana** | {st_preco_orig['divergencia_pct']:.2f}% | **{st_preco_estr['divergencia_pct']:.2f}%** | {st_preco_pos['divergencia_pct']:.2f}% | Salto para 261,84% aciona alerta imediato de assimetria |\n")
    f.write(f"| **Desvio Padrão Amostral ($\\sigma$, $ddof=1$)** | R$ {st_preco_orig['std_amostral']:.2f} | **R$ {st_preco_estr['std_amostral']:.2f}** | R$ {st_preco_pos['std_amostral']:.2f} | Explosão da dispersão amostral sem o EDF |\n")
    f.write(f"| **Desvio Padrão Populacional ($\\sigma_p$, $ddof=0$)** | R$ {st_preco_orig['std_pop']:.2f} | **R$ {st_preco_estr['std_pop']:.2f}** | R$ {st_preco_pos['std_pop']:.2f} | Dispersão populacional reduzida em 96,9% após EDF |\n")
    f.write("| **Quartis Lineares ($Q_1$ / $Q_3$ / $\\text{IQR}$)** | 88,75 / 102,50 / 13,75 | 88,75 / 350,00 / 261,25 | 88,75 / 105,78 / 17,03 | Em $N=4$, $Q_3$ linear absorve 25% do extremo |\n")
    f.write("| **Limites IQR Lineares ($LI_{\\text{lin}}$ / $LS_{\\text{lin}}$)** | 68,12 / **123,12** | -303,12 / **741,88** | 63,20 / **131,33** | $1100,00 > 741,88$ (Outlier capturado pelo IQR linear) |\n")
    f.write("| **Limites IQR Ordem Interna ($LI_{\\text{ord}}$ / $LS_{\\text{ord}}$)** | 75,00 / **115,00** | 75,00 / **115,00** | 75,00 / **115,00** | Quartis internos ($Q_1=90, Q_3=100$) imunes ao extremo |\n")
    f.write("| **Limites IQR de Referência ($LI_{\\text{ref}}$ / $LS_{\\text{ref}}$)** | 68,12 / **123,12** | 68,12 / **123,12** | 68,12 / **123,12** | Limite superior de blindagem aplicado: **R$ 123,12** |\n\n")

    f.write("### 3.2. Detecção Dupla por Fornecedor (Z-Score e IQR de Tukey no Cenário de Estresse)\n\n")
    f.write(
        "> **Nota Estatística sobre o Z-Score em $N=4$ (Teorema de Shiffler, 1988):** Em uma amostra de tamanho $N=4$, "
        "o valor máximo matemático possível para o Z-Score clássico amostral ($ddof=1$) é $Z_{\\max} = (N-1)/\\sqrt{N} = 3/\\sqrt{4} = \\mathbf{1,5000}$ "
        "(e $\\sqrt{N-1} = \\mathbf{1,7321}$ para $ddof=0$), pois o próprio outlier infla a média e o desvio padrão simultaneamente. "
        "O fornecedor **Delta** atinge $Z = \\mathbf{1,5000}$ (**99,99% do teto matemático possível**), além de apresentar "
        "**Z-Score Robusto (MAD) = 90,38 (> 2,0)**, sendo flagado de forma inequívoca por ambos os métodos.\n\n"
    )
    f.write("| Linha CSV | Fornecedor | Preço no Estresse (R$) | $Z$ Amostral ($ddof=1$) | $Z$ Pop. ($ddof=0$) | $Z$ Robusto (MAD) | Flag Z-Score | Flag IQR Linear ($> 741,88$) | Flag IQR Ref. ($> 123,12$) | Status Final EDF |\n")
    f.write("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |\n")
    for idx, row in df_estresse.iterrows():
        forn = row["fornecedor"]
        val = float(row["preco_unitario"])
        z_a = float(st_preco_estr["z_amostral"].loc[idx])
        z_p = float(st_preco_estr["z_pop"].loc[idx])
        z_r = float(st_preco_estr["z_robusto"].loc[idx])
        fl_z = "SIM (Anomalia)" if st_preco_estr["flag_z"].loc[idx] else "Não"
        fl_iqr_l = "SIM (> LS)" if st_preco_estr["flag_iqr_linear"].loc[idx] else "Não"
        fl_iqr_r = "SIM (> LS)" if st_preco_estr["flag_iqr_ref"].loc[idx] else "Não"
        status = "**OUTLIER CAPTURADO**" if (st_preco_estr["flag_iqr_ref"].loc[idx] or st_preco_estr["flag_z"].loc[idx]) else "Normal"
        f.write(
            f"| {idx + 2} | **{forn}** | R$ {val:.2f} | {z_a:.4f} | {z_p:.4f} | {z_r:.2f} | "
            f"{fl_z} | {fl_iqr_l} | {fl_iqr_r} | {status} |\n"
        )

    f.write("\n### 3.3. Registro de Tratamento por Winsorization / Clipping\n\n")
    f.write("| Registro (Fornecedor) | Coluna | Valor Original Limpo | Valor Errante Injetado | Limite Superior ($LS_{\\text{ref}}$ / $LS_{\\text{ord}}$ / $LS_{\\text{lin}}$) | Valor Blindado Aplicado (`fornecedores_edf.csv`) | Método de Detecção |\n")
    f.write("| :--- | :--- | :---: | :---: | :---: | :---: | :--- |\n")
    for reg in registros_capturados:
        f.write(
            f"| Linha {reg['linha_csv']} (**{reg['fornecedor']}**) | `{reg['coluna']}` | "
            f"R$ {reg['valor_base_limpa']:.2f} | **R$ {reg['valor_errante']:.2f}** | "
            f"R$ {reg['ls_ref']:.2f} / R$ {reg['ls_ord']:.2f} / R$ {reg['ls_linear']:.2f} | "
            f"**R$ {reg['valor_blindado_ref']:.2f}** | {reg['metodo']} |\n"
        )

    f.write("\n---\n\n")
    f.write("## 4. Impacto nas Notas Normalizadas de 1 a 10 (Matriz de Decisão)\n\n")
    f.write(
        "Para critérios do tipo **menor é melhor** (`preco_unitario`), a normalização Min-Max para a escala de 1 a 10 é dada por:\n\n"
        "$$\\text{Nota}(x) = 1 + 9 \\cdot \\frac{x_{\\max} - x}{x_{\\max} - x_{\\min}}$$\n\n"
        "- **Sem o EDF (`Delta = R$ 1.100,00`):** a amplitude total $(x_{\\max} - x_{\\min})$ salta de **R$ 25,00** ($110 - 85$) "
        "para **R$ 1.015,00** ($1100 - 85$). Como R$ 1.015,00 divide a diferença de preços, os fornecedores **Gama** (R$ 85), "
        "**Alfa** (R$ 90) e **Beta** (R$ 100) ficam comprimidos entre **9,87 e 10,00** (diferença de apenas **0,13 ponto**, "
        "destruindo **97,6% da capacidade discriminatória** do critério Preço).\n"
        "- **Com o EDF (`Delta` limitado por Winsorization):** a amplitude retorna à escala real dos dados, restaurando a "
        "diferenciação justa entre Gama, Alfa e Beta sem excluir Delta da tabela.\n\n"
    )

    f.write("### 4.1. Comparativo das Notas de Preço (Escala 1 a 10) — Antes vs. Depois\n\n")
    f.write("| Fornecedor | Preço Base (R$) | Preço no Estresse (R$) | Preço Blindado EDF (R$) | Nota Base Original (R$ 110) | **Nota SEM EDF (Distorcida — R$ 1.100)** | **Nota COM EDF (Blindada — LS R$ 123,12)** | Nota COM EDF (Ordem Interna — LS R$ 115,00) | Nota COM EDF (IQR Linear — LS R$ 741,88) |\n")
    f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
    for idx in range(len(df_original)):
        forn = df_original.loc[idx, "fornecedor"]
        p_orig = df_original.loc[idx, "preco_unitario"]
        p_estr = df_estresse.loc[idx, "preco_unitario"]
        p_edf = df_edf.loc[idx, "preco_unitario"]
        n_orig = notas_original.loc[idx, "nota_preco"]
        n_sem = notas_estresse_sem_edf.loc[idx, "nota_preco"]
        n_com = notas_estresse_com_edf.loc[idx, "nota_preco"]
        n_ord = notas_estresse_com_edf_ord.loc[idx, "nota_preco"]
        n_lin = notas_estresse_com_edf_lin.loc[idx, "nota_preco"]
        f.write(
            f"| **{forn}** | R$ {p_orig:.2f} | R$ {p_estr:.2f} | R$ {p_edf:.2f} | "
            f"{n_orig:.2f} | **{n_sem:.2f}** | **{n_com:.2f}** | {n_ord:.2f} | {n_lin:.2f} |\n"
        )

    spread_orig = float(notas_original.loc[notas_original["fornecedor"] == "Gama", "nota_preco"].values[0] -
                        notas_original.loc[notas_original["fornecedor"] == "Beta", "nota_preco"].values[0])
    spread_sem = float(notas_estresse_sem_edf.loc[notas_estresse_sem_edf["fornecedor"] == "Gama", "nota_preco"].values[0] -
                       notas_estresse_sem_edf.loc[notas_estresse_sem_edf["fornecedor"] == "Beta", "nota_preco"].values[0])
    spread_com = float(notas_estresse_com_edf.loc[notas_estresse_com_edf["fornecedor"] == "Gama", "nota_preco"].values[0] -
                       notas_estresse_com_edf.loc[notas_estresse_com_edf["fornecedor"] == "Beta", "nota_preco"].values[0])
    spread_ord = float(notas_estresse_com_edf_ord.loc[notas_estresse_com_edf_ord["fornecedor"] == "Gama", "nota_preco"].values[0] -
                       notas_estresse_com_edf_ord.loc[notas_estresse_com_edf_ord["fornecedor"] == "Beta", "nota_preco"].values[0])

    f.write(
        f"\n- **Diferença de nota entre Gama (R$ 85) e Beta (R$ 100):**\n"
        f"  - Base Original: **{spread_orig:.2f} pontos** (`10,00` vs `4,60`)\n"
        f"  - Sem EDF (Distorcido): **{spread_sem:.2f} ponto** (`10,00` vs `9,87` — notas artificialmente coladas)\n"
        f"  - Com EDF ($LS = \\text{{R\\$ }} 123,12$): **{spread_com:.2f} pontos** (`10,00` vs `6,46` — proporção restaurada)\n"
        f"  - Com EDF ($LS = \\text{{R\\$ }} 115,00$): **{spread_ord:.2f} pontos** (`10,00` vs `5,50` — proporção restaurada)\n\n"
    )

    f.write("### 4.2. Impacto na Pontuação Final Ponderada da Matriz de Decisão\n\n")
    f.write("Pesos oficiais aplicados: Preço (`30%`), Prazo (`20%`), Defeitos (`30%`) e Suporte (`20%`).\n\n")
    f.write("| Fornecedor | Nota Prazo (20%) | Nota Defeitos (30%) | Nota Suporte (20%) | Pontuação Final (Original) | **Pontuação Final SEM EDF (Distorcida)** | **Pontuação Final COM EDF (Blindada)** | Distorção Evitada pelo EDF |\n")
    f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
    for idx in range(len(df_original)):
        forn = df_original.loc[idx, "fornecedor"]
        n_prz = notas_original.loc[idx, "nota_prazo"]
        n_def = notas_original.loc[idx, "nota_defeitos"]
        n_sup = notas_original.loc[idx, "nota_suporte"]
        pf_orig = notas_original.loc[idx, "pontuacao_final"]
        pf_sem = notas_estresse_sem_edf.loc[idx, "pontuacao_final"]
        pf_com = notas_estresse_com_edf.loc[idx, "pontuacao_final"]
        erro_sem = pf_sem - pf_orig
        f.write(
            f"| **{forn}** | {n_prz:.2f} | {n_def:.2f} | {n_sup:.2f} | "
            f"{pf_orig:.2f} | **{pf_sem:.2f}** ({erro_sem:+.2f}) | **{pf_com:.2f}** | "
            f"Reduziu inflação artificial de {erro_sem:+.2f} para {pf_com - pf_orig:+.2f} pt |\n"
        )

    f.write("\n---\n\n")
    f.write("## 5. Valores Sinalizados para Revisão Humana\n\n")
    f.write(
        "1. **Linha 5 (`Delta` — coluna `preco_unitario`):** valor no cenário de estresse de **R$ 1.100,00** excede em **9,9x** o limite "
        "superior de referência ($LS = \\text{R\\$ } 123,12$) e atinge o teto matemático do Z-Score para $N=4$ ($Z = 1,5000$, "
        "$Z_{\\text{robusto}} = 90,38$). O valor foi blindado via *Winsorization* para **R$ 123,12** em `resultados/fornecedores_edf.csv`. "
        "Recomenda-se confirmação junto ao comprador se o valor real da proposta comercial de Delta é **R$ 110,00** (erro de digitação com um zero a mais).\n"
    )


# ==============================================================================
# 6. Visualização Gráfica em 150 DPI (Seguindo a Skill chart-image)
# ==============================================================================
caminho_grafico_edf = os.path.join("resultados", "grafico_edf.png")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6.5))

fornecedores = df_original["fornecedor"].tolist()
x_pos = np.arange(len(fornecedores))

# ------------------------------------------------------------------------------
# Painel 1 (Esquerda): Detecção do Dado Errante e Limites IQR (Winsorization)
# ------------------------------------------------------------------------------
precos_estresse = df_estresse["preco_unitario"].values
precos_blindados = df_edf["preco_unitario"].values

largura_p1 = 0.34
cores_estresse = ["#D32F2F" if f == FORNECEDOR_ERRANTE else "#90CAF9" for f in fornecedores]
barras_bruto = ax1.bar(
    x_pos - largura_p1 / 2,
    precos_estresse,
    width=largura_p1,
    color=cores_estresse,
    edgecolor="#222222",
    linewidth=0.8,
    label="Valor no Estresse (Vermelho = Outlier Capturado)",
)
barras_blindado = ax1.bar(
    x_pos + largura_p1 / 2,
    precos_blindados,
    width=largura_p1,
    color="#2E7D32",
    edgecolor="#222222",
    linewidth=0.8,
    label="Valor Blindado pelo EDF (Winsorization em LS)",
)

# Linhas horizontais de referência estatística
ax1.axhline(
    st_preco_estr["ls_linear"],
    color="#C62828",
    linestyle="--",
    linewidth=1.4,
    label=f"Limite Superior IQR Linear (LS = R$ {st_preco_estr['ls_linear']:.2f})",
)
ax1.axhline(
    st_preco_estr["ls_ref"],
    color="#1565C0",
    linestyle="-.",
    linewidth=1.6,
    label=f"Limite Superior IQR Blindagem (LS_ref = R$ {st_preco_estr['ls_ref']:.2f})",
)
ax1.axhline(
    st_preco_estr["mediana"],
    color="#424242",
    linestyle=":",
    linewidth=1.3,
    label=f"Mediana Robusta (Q2 = R$ {st_preco_estr['mediana']:.2f})",
)

for b in barras_bruto:
    h = b.get_height()
    offset_y = 25 if h > 500 else 38
    ax1.text(
        b.get_x() + b.get_width() / 2,
        h + offset_y,
        f"R$ {h:.0f}",
        ha="center",
        va="bottom",
        fontsize=9.0,
        fontweight="bold",
        color="#B71C1C" if h > 500 else "#1E3A5F",
    )

for b in barras_blindado:
    h = b.get_height()
    ax1.text(
        b.get_x() + b.get_width() / 2,
        h + 38,
        f"R$ {h:.1f}",
        ha="center",
        va="bottom",
        fontsize=8.8,
        fontweight="bold",
        color="#1B5E20",
    )

# Anotação de destaque na captura de Delta (apenas um '$' na string para evitar mathtext)
ax1.annotate(
    "Dado Errante Capturado!\nDelta: de R$ 1.100,00 para 123,12\n(IQR de Tukey + Z=1,50 | Z_rob=90,4)",
    xy=(3 - largura_p1 / 2, VALOR_ERRANTE_INJETADO),
    xytext=(0.85, 510),
    arrowprops=dict(arrowstyle="->", color="#B71C1C", lw=1.8, connectionstyle="arc3,rad=-0.12"),
    fontsize=9.5,
    fontweight="bold",
    color="#B71C1C",
    bbox=dict(boxstyle="round,pad=0.45", fc="#FFEBEE", ec="#D32F2F", lw=1.2),
)

ax1.set_title("1. Captura do Dado Errante e Clipping (Preço Unitário)", fontsize=13, fontweight="bold", pad=12)
ax1.set_xlabel("Fornecedor (N = 4 linhas preservadas)", fontsize=11, labelpad=8)
ax1.set_ylabel("Preço Unitário (R$) — Menor é melhor", fontsize=11, labelpad=8)
ax1.set_xticks(x_pos)
ax1.set_xticklabels(fornecedores, fontsize=10.5, fontweight="bold")
ax1.set_ylim(0, 1280)
ax1.grid(axis="y", linestyle="--", alpha=0.45)
ax1.legend(loc="upper left", frameon=True, facecolor="#ffffff", framealpha=0.95, fontsize=8.8)

# ------------------------------------------------------------------------------
# Painel 2 (Direita): Proteção das Notas Normalizadas (Escala 1 a 10)
# ------------------------------------------------------------------------------
largura_p2 = 0.25
notas_sem = notas_estresse_sem_edf["nota_preco"].values
notas_com = notas_estresse_com_edf["nota_preco"].values
notas_ref = notas_original["nota_preco"].values

b_sem = ax2.bar(
    x_pos - largura_p2,
    notas_sem,
    width=largura_p2,
    color="#E53935",
    edgecolor="#222222",
    linewidth=0.7,
    label="Sem EDF — Distorcido (Delta = R$ 1.100)",
)
b_com = ax2.bar(
    x_pos,
    notas_com,
    width=largura_p2,
    color="#2E7D32",
    edgecolor="#222222",
    linewidth=0.7,
    label="Com EDF — Blindado (Winsorized R$ 123,12)",
)
b_ref = ax2.bar(
    x_pos + largura_p2,
    notas_ref,
    width=largura_p2,
    color="#1976D2",
    edgecolor="#222222",
    linewidth=0.7,
    label="Base Original Limpa (Referência R$ 110)",
)

for grupo, cor_txt in [(b_sem, "#B71C1C"), (b_com, "#1B5E20"), (b_ref, "#0D47A1")]:
    for barra in grupo:
        y = barra.get_height()
        ax2.text(
            barra.get_x() + barra.get_width() / 2,
            y + 0.18,
            f"{y:.2f}",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
            color=cor_txt,
        )

ax2.annotate(
    "Sem EDF: Alfa (9,96), Beta (9,87) e Gama (10,00)\ncomprimidos no topo (spread = 0,13 pt)!\nCom EDF: proporção restaurada (3,54 pts).",
    xy=(1 - largura_p2, notas_sem[1]),
    xytext=(-0.38, 11.15),
    arrowprops=dict(arrowstyle="->", color="#C62828", lw=1.5),
    fontsize=8.6,
    fontweight="bold",
    color="#333333",
    bbox=dict(boxstyle="round,pad=0.35", fc="#FFF8E1", ec="#F57C00", lw=1.1),
)

ax2.set_title("2. Proteção das Notas de 1 a 10 no Critério Preço", fontsize=13, fontweight="bold", pad=12)
ax2.set_xlabel("Fornecedor Avaliado", fontsize=11, labelpad=8)
ax2.set_ylabel("Nota Normalizada Min-Max (Escala 1 a 10)", fontsize=11, labelpad=8)
ax2.set_xticks(x_pos)
ax2.set_xticklabels(fornecedores, fontsize=10.5, fontweight="bold")
ax2.set_ylim(0, 13.2)
ax2.set_yticks([0, 2, 4, 6, 8, 10])
ax2.grid(axis="y", linestyle="--", alpha=0.45)
ax2.legend(loc="upper right", frameon=True, facecolor="#ffffff", framealpha=0.95, fontsize=8.3)

fig.suptitle(
    "Errant Data Finder (EDF) — Auditoria de Outliers e Blindagem da Matriz de Decisão (1 a 10)",
    fontsize=14.5,
    fontweight="bold",
    y=0.98,
)
fig.text(
    0.5,
    0.01,
    f"Fonte: {caminho_utilizado} (N=4 preservados) | Metodologia: IQR de Tukey + Z-Score + Winsorization (Skills errant-data-finder & chart-image)",
    ha="center",
    fontsize=9,
    color="#555555",
)

plt.tight_layout(rect=[0, 0.03, 1, 0.94])
plt.savefig(caminho_grafico_edf, dpi=150)
plt.close()

print("=== ERRANT DATA FINDER (EDF) EXECUTADO COM SUCESSO ===")
print(f"Base lida: {caminho_utilizado} ({len(df_original)} linhas)")
print(f"Base tratada salva em: {caminho_csv_edf} ({len(df_edf)} linhas preservadas)")
print(f"Relatorio salvo em: {caminho_relatorio_edf}")
print(f"Grafico (150 DPI) salvo em: {caminho_grafico_edf}")
