# Relatório de Qualidade de Dados (conferir-csv)

**Arquivo auditado:** `dados\fornecedores.csv`
**Finalidade:** Seleção do melhor fornecedor através da Matriz de Decisão multicritério.

## 1. Estrutura dos Dados
- **Total de linhas:** 4
- **Total de colunas:** 5 (`fornecedor, preco_unitario, prazo_dias, defeitos_pct, suporte_nota`)
- **Linhas duplicadas:** 0
- **Tipos de dados:**
  - `fornecedor`: str
  - `preco_unitario`: int64
  - `prazo_dias`: int64
  - `defeitos_pct`: float64
  - `suporte_nota`: float64

## 2. Auditoria de Valores Ausentes
Status: **Nenhum valor ausente encontrado!** Todas as 4 linhas e 5 colunas estão 100% preenchidas.

## 3. Tratamento e Validação
- **Arquivo original:** `dados/fornecedores.csv` preservado intacto conforme as regras do projeto.
- **Arquivo verificado:** `resultados/fornecedores_corrigido.csv` gerado com sucesso e 100% íntegro para a matriz de decisão.
