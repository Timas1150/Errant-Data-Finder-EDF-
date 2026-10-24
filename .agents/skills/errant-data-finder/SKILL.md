---
name: errant-data-finder
description: Auditoria estatística e blindagem contra dados errantes (outliers e anomalias) em bases CSV ou séries numéricas via diagnóstico de assimetria (Média vs. Mediana), detecção dupla (IQR de Tukey e Z-Score) e tratamento não-destrutivo por Winsorization/Clipping para proteger normalizações multicritério na escala de 1 a 10.
---

# Errant Data Finder (EDF) — Auditoria e Blindagem Estatística

Você é um auditor de qualidade estatística responsável por executar a skill **Errant Data Finder (EDF)**: uma camada de blindagem contra valores errantes (outliers, erros de digitação e anomalias de ordem de grandeza) em tabelas de decisão e séries numéricas.

## 1. Contexto e Posicionamento no Pipeline

- **Ordem no fluxo:** executada após a validação estrutural (`conferir-csv`) e imediatamente antes da Matriz de Decisão (`decision-matrix`).
- **Regra de ouro (Preservação de Registros):** **nenhuma linha pode ser excluída**. Em matrizes de decisão com poucos candidatos (como listas de $N = 4$ fornecedores), cada linha representa uma alternativa real sob avaliação. Remover uma linha equivale a desclassificar sumariamente um fornecedor por um possível erro de digitação.
- **Entrada com fallback:** carregue `resultados/fornecedores_corrigido.csv`; caso não exista, utilize `dados/fornecedores.csv` como fallback, declarando explicitamente no relatório qual arquivo foi lido.

---

## 2. Identificação Automática de Colunas e Direção dos Critérios

1. **Detecção automática de colunas auditáveis:**
   - Inspecione todas as colunas da tabela e selecione aquelas de tipo numérico (ou texto integralmente conversível para número).
   - Ignore colunas identificadoras ou categóricas (como `fornecedor`, `id`, `nome`), documentando no relatório todas as colunas auditadas e as ignoradas com a respectiva justificativa.
2. **Inferência da direção do critério:**
   - **Menor é melhor (`minimize`):** custos, preços (`preco_unitario`), prazos (`prazo_dias`), taxas de defeito (`defeitos_pct`), retrabalho, risco.
   - **Maior é melhor (`maximize`):** notas de suporte (`suporte_nota`), qualidade, satisfação, SLA, disponibilidade.
   - Quando a direção de uma coluna não puder ser inferida com segurança pelo nome e contexto, sinalize-a para confirmação humana no relatório.

---

## 3. Regras de Auditoria Estatística

### 3.1. Diagnóstico Descritivo e Comparação Média vs. Mediana (Indicador de Assimetria)
Para cada coluna numérica auditada, calcule:
- **Métricas paramétricas:** Média ($\mu$), Desvio Padrão amostral ($\sigma$, $ddof=1$) e populacional ($\sigma_p$, $ddof=0$), Mínimo ($x_{\min}$) e Máximo ($x_{\max}$).
- **Métricas de ordem (robustas):** Primeiro Quartil ($Q_1$, percentil 25), Mediana ($Q_2$, percentil 50), Terceiro Quartil ($Q_3$, percentil 75) e Intervalo Interquartil ($\text{IQR} = Q_3 - Q_1$).
- **Índice de Divergência Média vs. Mediana (%):**
  $$\text{Divergência (\%)} = \frac{|\mu - Q_2|}{|Q_2|} \times 100$$
  - Enquanto a mediana ($Q_2$) possui ponto de ruptura de 50% e permanece estável diante de um valor extremo, a média ($\mu$) é fortemente deslocada na direção da anomalia.
  - Divergências elevadas (ex.: $> 15\%$) funcionam como **alerta primário de assimetria** induzida por valores errantes.

### 3.2. Detecção Dupla de Outliers (Z-Score + IQR de Tukey)
Aplique dois critérios complementares para capturar anomalias:

1. **Critério 1 — Intervalo Interquartil de Tukey (IQR):**
   $$\text{IQR} = Q_3 - Q_1$$
   $$LI = Q_1 - 1{,}5 \cdot \text{IQR} \qquad \text{e} \qquad LS = Q_3 + 1{,}5 \cdot \text{IQR}$$
   - Marque como errante todo valor $x < LI$ ou $x > LS$.
   - *Nota técnica para micro-amostras ($N \le 5$):* Na interpolação linear padrão (`method='linear'`), o cálculo de $Q_3$ em $N=4$ atribui peso de 25% ao valor máximo ($Q_3 = 0{,}75 x_{(3)} + 0{,}25 x_{(4)}$), permitindo contaminação parcial do próprio limite superior pelo outlier. Por isso, documente tanto os limites de Tukey lineares da amostra quanto os limites de Tukey robustos (baseados na distribuição de referência / quartis de ordem internos não contaminados).

2. **Critério 2 — Escore Z (Z-Score):**
   $$Z = \frac{|x - \mu|}{\sigma}$$
   - **Regra geral:** marque como anomalia severa todo valor com $Z > 2{,}0$.
   - **Ajuste e diagnóstico para amostras pequenas ($N = 4$):** pelo Teorema de Shiffler (1988), o valor máximo matemático possível para o Z-Score clássico amostral ($ddof=1$) em uma amostra de tamanho $N$ é:
     $$Z_{\max} = \frac{N - 1}{\sqrt{N}}$$
     Para $N = 4$, o teto absoluto é $Z_{\max} = \frac{3}{\sqrt{4}} = 1{,}5000$ (e $\sqrt{N-1} \approx 1{,}7321$ para $ddof=0$), pois o próprio outlier infla simultaneamente $\mu$ e $\sigma$ (*efeito de mascaramento*). Assim, em $N=4$, complemente o Z-Score clássico com o **Z-Score Modificado/Robusto** baseado no Desvio Absoluto Mediano ($\text{MAD} = \text{mediana}(|x - Q_2|)$):
     $$Z_{\text{rob}} = \frac{0{,}6745 \cdot |x - Q_2|}{\text{MAD}}$$
     Marque o registro se $Z > 2{,}0$, $Z_{\text{rob}} > 2{,}0$ ou se $Z$ atingir $\ge 95\%$ do teto de Shiffler ($Z \ge 1{,}425$ em $N=4$).
   - Registre explicitamente qual critério detectou cada valor (`IQR`, `Z-Score` ou `Ambos`).

### 3.3. Tratamento Não-Destrutivo por Winsorization / Clipping
Para preservar 100% das linhas da tabela:
$$x_{\text{edf}} = \min\big(\max(x, LI),\, LS\big)$$
- Se $x > LS$, substitua $x$ por $LS$ (teto estatístico).
- Se $x < LI$, substitua $x$ por $LI$ (piso estatístico).
- Mantenha a rastreabilidade completa registrando o **Valor Original**, o **Limite Aplicado ($LI$ ou $LS$)** e o **Valor Blindado ($x_{\text{edf}}$)** no relatório de auditoria, sinalizando a célula para revisão humana (para confirmar se trata de erro de digitação ou condição comercial atípica real).

### 3.4. Análise de Impacto na Normalização para a Escala de 1 a 10
A Matriz de Decisão converte cada critério para notas de 1 a 10 via normalização Min-Max linear:
- **Critérios onde menor é melhor (`preco_unitario`, `prazo_dias`, `defeitos_pct`):**
  $$\text{Nota}(x) = 1 + 9 \cdot \frac{x_{\max} - x}{x_{\max} - x_{\min}}$$
- **Critérios onde maior é melhor (`suporte_nota`):**
  $$\text{Nota}(x) = 1 + 9 \cdot \frac{x - x_{\min}}{x_{\max} - x_{\min}}$$

**Por que um valor errante destrói a Matriz de Decisão sem o EDF?**
- Quando um único fornecedor apresenta um erro de ordem de grandeza (ex.: preço digitado como $\text{R\$ } 1.100{,}00$ em vez de $\text{R\$ } 110{,}00$), a amplitude $(x_{\max} - x_{\min})$ explode (de $\text{R\$ } 25{,}00$ para $\text{R\$ } 1.015{,}00$).
- Como $(x_{\max} - x_{\min})$ está no denominador da fórmula, as diferenças reais entre os demais fornecedores ($\text{R\$ } 85$, $\text{R\$ } 90$ e $\text{R\$ } 100$) tornam-se desprezíveis perante o extremo, **comprimindo todas as suas notas próximas a 10,0** (ex.: $10{,}00$, $9{,}96$ e $9{,}87$).
- Isso anula o peso prático do critério para os candidatos regulares e pode inverter ou distorcer a pontuação ponderada final.
- Com o **Clipping (Winsorization)** em $LS$, o extremo continua recebendo a nota mínima ($1{,}00$) naquele critério sem ser eliminado da disputa, mas o denominador $(LS - x_{\min})$ volta a uma ordem de grandeza compatível com a distribuição, **restaurando a proporção e a capacidade discriminatória das notas de 1 a 10**.

---

## 4. Entregáveis Obrigatórios (`errant_finder.py`)

A execução via `.\.venv\Scripts\python.exe errant_finder.py` deve gerar na pasta `resultados/`:
1. `resultados/fornecedores_edf.csv`: base tratada pelo EDF com todas as 4 linhas preservadas.
2. `resultados/relatorio_edf.md`: relatório técnico completo e reproduzível contendo:
   - Identificação do arquivo lido, colunas auditadas/ignoradas e direção dos critérios;
   - Diagnóstico da base original e execução do cenário de estresse em memória;
   - Tabelas de Média vs. Mediana, índice de assimetria, escores Z e limites IQR ($Q_1, Q_3, \text{IQR}, LI, LS$);
   - Tabela de dados errantes capturados (Fornecedor, Coluna, Valor Original, Limite, Valor Blindado, Flags de Detecção);
   - Comparativo numérico das notas de 1 a 10 e da Pontuação Ponderada da Matriz de Decisão **Antes vs. Depois** do tratamento;
   - Lista de itens sinalizados para revisão humana.
3. `resultados/grafico_edf.png`: visualização em **150 DPI** seguindo o padrão editorial da skill `chart-image` (rótulos explícitos, unidades, linha de base adequada, contraste visual e nota de fonte/metodologia), exibindo o dado errante capturado frente aos limites IQR e a restauração das notas de 1 a 10.
