# Relatório de Auditoria Estatística — Errant Data Finder (EDF)

- **Arquivo de entrada auditado:** `resultados\fornecedores_corrigido.csv`
- **Total de registros (fornecedores):** `4` linhas (`Alfa, Beta, Gama, Delta`)
- **Total de registros após o EDF:** `4` linhas (**0 linhas removidas** — preservação de 100% dos candidatos)
- **Política de tratamento:** *Winsorization / Clipping* nos limites estatísticos $[LI, LS]$ para proteger a escala de 1 a 10 da Matriz de Decisão.

---

## 1. Identificação Automática de Colunas e Direção dos Critérios

### 1.1. Colunas Auditadas (Numéricas)

| Coluna | Tipo Original | Unidade | Direção Inferida | Peso na Matriz | Revisão Humana de Direção |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `preco_unitario` | `int64` | R$ | **Menor é melhor (minimização)** | 30% | Não (inferência segura) |
| `prazo_dias` | `int64` | dias | **Menor é melhor (minimização)** | 20% | Não (inferência segura) |
| `defeitos_pct` | `float64` | % | **Menor é melhor (minimização)** | 30% | Não (inferência segura) |
| `suporte_nota` | `float64` | nota (0-10) | **Maior é melhor (maximização)** | 20% | Não (inferência segura) |

### 1.2. Colunas Ignoradas

| Coluna | Tipo Original | Motivo da Exclusão da Auditoria Numérica |
| :--- | :--- | :--- |
| `fornecedor` | `str` | Identificador nominal do candidato (coluna textual/categórica) |

---

## 2. Diagnóstico Estatístico da Base Original (`fornecedores_corrigido.csv`)

Na inspeção inicial das 4 linhas da base original, compara-se a **Média ($\mu$)** com a **Mediana ($Q_2$)** e verificam-se os limites de Tukey ($LI = Q_1 - 1,5\cdot\text{IQR}$ e $LS = Q_3 + 1,5\cdot\text{IQR}$) e os escores $Z$:

| Coluna | Média ($\mu$) | Mediana ($Q_2$) | Divergência ($|\mu-Q_2|/Q_2$) | Desvio Padrão ($\sigma$) | $Q_1$ | $Q_3$ | $\text{IQR}$ | Limite Inf. ($LI$) | Limite Sup. ($LS$) | $\max(|Z|)$ | Outliers Detectados |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `preco_unitario` | 96.25 | 95.00 | 1.32% | 11.09 | 88.75 | 102.50 | 13.75 | 68.12 | 123.12 | 1.24 | **0 (Base limpa)** |
| `prazo_dias` | 7.25 | 6.50 | 11.54% | 3.59 | 4.75 | 9.00 | 4.25 | -1.62 | 15.38 | 1.32 | **0 (Base limpa)** |
| `defeitos_pct` | 1.88 | 1.50 | 25.00% | 1.55 | 0.88 | 2.50 | 1.62 | -1.56 | 4.94 | 1.37 | **0 (Base limpa)** |
| `suporte_nota` | 8.12 | 8.50 | 4.41% | 1.55 | 7.50 | 9.12 | 1.62 | 5.06 | 11.56 | 1.37 | **0 (Base limpa)** |

> **Conclusão da Base Original:** Todas as 4 colunas (`preco_unitario`, `prazo_dias`, `defeitos_pct` e `suporte_nota`) encontram-se dentro dos limites interquartis $[LI, LS]$ e não apresentam anomalias severas de Z-Score.

---

## 3. Cenário de Estresse Demonstrativo (Injeção de Dado Errante em Memória)

Como a tabela original possui apenas $N = 4$ fornecedores e está limpa, foi executado em memória (sem alterar `resultados\fornecedores_corrigido.csv`) um cenário de estresse que simula um **erro de digitação realista**: um zero a mais no preço unitário do fornecedor **Delta**, alterando `preco_unitario` de **R$ 110.00** para **R$ 1100.00**.

### 3.1. Assimetria e Limites Estatísticos Antes vs. Depois do EDF (`preco_unitario`)

| Métrica Estatística | Base Original (Limpa) | Cenário de Estresse (Sem EDF) | Pós-Tratamento EDF (Blindado) | Interpretação Técnica |
| :--- | :---: | :---: | :---: | :--- |
| **Valores da Série (R$)** | `[85, 90, 100, 110]` | `[85, 90, 100, 1100]` | `[85, 90, 100, 123.12]` | `Delta` limitado ao teto estatístico $LS$ |
| **Média ($\mu$)** | R$ 96.25 | **R$ 343.75** | R$ 99.53 | Erro inflou a média em +257,14% antes do EDF |
| **Mediana ($Q_2$)** | R$ 95.00 | **R$ 95.00** | R$ 95.00 | Mediana permaneceu 100% imune ao valor extremo |
| **Divergência Média vs. Mediana** | 1.32% | **261.84%** | 4.77% | Salto para 261,84% aciona alerta imediato de assimetria |
| **Desvio Padrão Amostral ($\sigma$, $ddof=1$)** | R$ 11.09 | **R$ 504.21** | R$ 16.92 | Explosão da dispersão amostral sem o EDF |
| **Desvio Padrão Populacional ($\sigma_p$, $ddof=0$)** | R$ 9.60 | **R$ 436.65** | R$ 14.65 | Dispersão populacional reduzida em 96,9% após EDF |
| **Quartis Lineares ($Q_1$ / $Q_3$ / $\text{IQR}$)** | 88,75 / 102,50 / 13,75 | 88,75 / 350,00 / 261,25 | 88,75 / 105,78 / 17,03 | Em $N=4$, $Q_3$ linear absorve 25% do extremo |
| **Limites IQR Lineares ($LI_{\text{lin}}$ / $LS_{\text{lin}}$)** | 68,12 / **123,12** | -303,12 / **741,88** | 63,20 / **131,33** | $1100,00 > 741,88$ (Outlier capturado pelo IQR linear) |
| **Limites IQR Ordem Interna ($LI_{\text{ord}}$ / $LS_{\text{ord}}$)** | 75,00 / **115,00** | 75,00 / **115,00** | 75,00 / **115,00** | Quartis internos ($Q_1=90, Q_3=100$) imunes ao extremo |
| **Limites IQR de Referência ($LI_{\text{ref}}$ / $LS_{\text{ref}}$)** | 68,12 / **123,12** | 68,12 / **123,12** | 68,12 / **123,12** | Limite superior de blindagem aplicado: **R$ 123,12** |

### 3.2. Detecção Dupla por Fornecedor (Z-Score e IQR de Tukey no Cenário de Estresse)

> **Nota Estatística sobre o Z-Score em $N=4$ (Teorema de Shiffler, 1988):** Em uma amostra de tamanho $N=4$, o valor máximo matemático possível para o Z-Score clássico amostral ($ddof=1$) é $Z_{\max} = (N-1)/\sqrt{N} = 3/\sqrt{4} = \mathbf{1,5000}$ (e $\sqrt{N-1} = \mathbf{1,7321}$ para $ddof=0$), pois o próprio outlier infla a média e o desvio padrão simultaneamente. O fornecedor **Delta** atinge $Z = \mathbf{1,5000}$ (**99,99% do teto matemático possível**), além de apresentar **Z-Score Robusto (MAD) = 90,38 (> 2,0)**, sendo flagado de forma inequívoca por ambos os métodos.

| Linha CSV | Fornecedor | Preço no Estresse (R$) | $Z$ Amostral ($ddof=1$) | $Z$ Pop. ($ddof=0$) | $Z$ Robusto (MAD) | Flag Z-Score | Flag IQR Linear ($> 741,88$) | Flag IQR Ref. ($> 123,12$) | Status Final EDF |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 2 | **Alfa** | R$ 90.00 | 0.5033 | 0.5811 | 0.45 | Não | Não | Não | Normal |
| 3 | **Beta** | R$ 100.00 | 0.4834 | 0.5582 | 0.45 | Não | Não | Não | Normal |
| 4 | **Gama** | R$ 85.00 | 0.5132 | 0.5926 | 0.90 | Não | Não | Não | Normal |
| 5 | **Delta** | R$ 1100.00 | 1.4999 | 1.7319 | 90.38 | SIM (Anomalia) | SIM (> LS) | SIM (> LS) | **OUTLIER CAPTURADO** |

### 3.3. Registro de Tratamento por Winsorization / Clipping

| Registro (Fornecedor) | Coluna | Valor Original Limpo | Valor Errante Injetado | Limite Superior ($LS_{\text{ref}}$ / $LS_{\text{ord}}$ / $LS_{\text{lin}}$) | Valor Blindado Aplicado (`fornecedores_edf.csv`) | Método de Detecção |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| Linha 5 (**Delta**) | `preco_unitario` | R$ 110.00 | **R$ 1100.00** | R$ 123.12 / R$ 115.00 / R$ 741.88 | **R$ 123.12** | Ambos (IQR de Tukey + Z-Score) |

---

## 4. Impacto nas Notas Normalizadas de 1 a 10 (Matriz de Decisão)

Para critérios do tipo **menor é melhor** (`preco_unitario`), a normalização Min-Max para a escala de 1 a 10 é dada por:

$$\text{Nota}(x) = 1 + 9 \cdot \frac{x_{\max} - x}{x_{\max} - x_{\min}}$$

- **Sem o EDF (`Delta = R$ 1.100,00`):** a amplitude total $(x_{\max} - x_{\min})$ salta de **R$ 25,00** ($110 - 85$) para **R$ 1.015,00** ($1100 - 85$). Como R$ 1.015,00 divide a diferença de preços, os fornecedores **Gama** (R$ 85), **Alfa** (R$ 90) e **Beta** (R$ 100) ficam comprimidos entre **9,87 e 10,00** (diferença de apenas **0,13 ponto**, destruindo **97,6% da capacidade discriminatória** do critério Preço).
- **Com o EDF (`Delta` limitado por Winsorization):** a amplitude retorna à escala real dos dados, restaurando a diferenciação justa entre Gama, Alfa e Beta sem excluir Delta da tabela.

### 4.1. Comparativo das Notas de Preço (Escala 1 a 10) — Antes vs. Depois

| Fornecedor | Preço Base (R$) | Preço no Estresse (R$) | Preço Blindado EDF (R$) | Nota Base Original (R$ 110) | **Nota SEM EDF (Distorcida — R$ 1.100)** | **Nota COM EDF (Blindada — LS R$ 123,12)** | Nota COM EDF (Ordem Interna — LS R$ 115,00) | Nota COM EDF (IQR Linear — LS R$ 741,88) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Alfa** | R$ 90.00 | R$ 90.00 | R$ 90.00 | 8.20 | **9.96** | **8.82** | 8.50 | 9.93 |
| **Beta** | R$ 100.00 | R$ 100.00 | R$ 100.00 | 4.60 | **9.87** | **6.46** | 5.50 | 9.79 |
| **Gama** | R$ 85.00 | R$ 85.00 | R$ 85.00 | 10.00 | **10.00** | **10.00** | 10.00 | 10.00 |
| **Delta** | R$ 110.00 | R$ 1100.00 | R$ 123.12 | 1.00 | **1.00** | **1.00** | 1.00 | 1.00 |

- **Diferença de nota entre Gama (R$ 85) e Beta (R$ 100):**
  - Base Original: **5.40 pontos** (`10,00` vs `4,60`)
  - Sem EDF (Distorcido): **0.13 ponto** (`10,00` vs `9,87` — notas artificialmente coladas)
  - Com EDF ($LS = \text{R\$ } 123,12$): **3.54 pontos** (`10,00` vs `6,46` — proporção restaurada)
  - Com EDF ($LS = \text{R\$ } 115,00$): **4.50 pontos** (`10,00` vs `5,50` — proporção restaurada)

### 4.2. Impacto na Pontuação Final Ponderada da Matriz de Decisão

Pesos oficiais aplicados: Preço (`30%`), Prazo (`20%`), Defeitos (`30%`) e Suporte (`20%`).

| Fornecedor | Nota Prazo (20%) | Nota Defeitos (30%) | Nota Suporte (20%) | Pontuação Final (Original) | **Pontuação Final SEM EDF (Distorcida)** | **Pontuação Final COM EDF (Blindada)** | Distorção Evitada pelo EDF |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Alfa** | 5.50 | 6.14 | 6.14 | 6.63 | **7.16** (+0.53) | **6.82** | Reduziu inflação artificial de +0.53 para +0.19 pt |
| **Beta** | 8.88 | 8.71 | 8.71 | 7.51 | **9.09** (+1.58) | **8.07** | Reduziu inflação artificial de +1.58 para +0.56 pt |
| **Gama** | 1.00 | 1.00 | 1.00 | 3.70 | **3.70** (+0.00) | **3.70** | Reduziu inflação artificial de +0.00 para +0.00 pt |
| **Delta** | 10.00 | 10.00 | 10.00 | 7.30 | **7.30** (+0.00) | **7.30** | Reduziu inflação artificial de +0.00 para +0.00 pt |

---

## 5. Valores Sinalizados para Revisão Humana

1. **Linha 5 (`Delta` — coluna `preco_unitario`):** valor no cenário de estresse de **R$ 1.100,00** excede em **9,9x** o limite superior de referência ($LS = \text{R\$ } 123,12$) e atinge o teto matemático do Z-Score para $N=4$ ($Z = 1,5000$, $Z_{\text{robusto}} = 90,38$). O valor foi blindado via *Winsorization* para **R$ 123,12** em `resultados/fornecedores_edf.csv`. Recomenda-se confirmação junto ao comprador se o valor real da proposta comercial de Delta é **R$ 110,00** (erro de digitação com um zero a mais).
