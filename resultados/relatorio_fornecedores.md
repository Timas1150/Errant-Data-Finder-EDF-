# Relatório de Seleção de Fornecedores - Decision Matrix & Chart-Image

## 1. Contexto e Alternativas
Análise comparativa multicritério entre os 4 fornecedores avaliados:

| Fornecedor | Preço Unitário (R$) | Prazo (dias) | Defeitos (%) | Suporte (nota 0-10) |
| :--- | :--- | :--- | :--- | :--- |
| Alfa | R$ 90.00 | 8 | 2.0% | 8.0 |
| Beta | R$ 100.00 | 5 | 1.0% | 9.0 |
| Gama | R$ 85.00 | 12 | 4.0% | 6.0 |
| Delta | R$ 110.00 | 4 | 0.5% | 9.5 |

## 2. Critérios e Pesos
- **Preço Unitário:** 30% (menor custo = maior nota)
- **Prazo de Entrega:** 20% (menor prazo = maior nota)
- **Taxa de Defeitos:** 30% (menor índice de defeitos = maior nota)
- **Nota de Suporte:** 20% (melhor atendimento = maior nota)

## 3. Matriz de Decisão (Notas de 1 a 10 e Pontuação Final)

| Posição | Fornecedor | Nota Preço | Nota Prazo | Nota Defeitos | Nota Suporte | Pontuação Final |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1º | **Beta** ⭐ **Vencedor** | 4.60 | 8.88 | 8.71 | 8.71 | **7.51** |
| 2º | **Delta** | 1.00 | 10.00 | 10.00 | 10.00 | **7.30** |
| 3º | **Alfa** | 8.20 | 5.50 | 6.14 | 6.14 | **6.63** |
| 4º | **Gama** | 10.00 | 1.00 | 1.00 | 1.00 | **3.70** |

## 4. Gráficos Gerados na Pasta `resultados/`
1. `grafico_fornecedores.png`: Visão comparativa dupla (Ranking ponderado + detalhamento por critério).
2. `grafico_tradeoff_custo_qualidade.png`: Dispersão de Preço x Defeitos com zonas de decisão.
3. `grafico_radar_fornecedores.png`: Gráfico radar mostrando o perfil multicritério de cada fornecedor.
