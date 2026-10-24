---
name: conferir-csv
description: Conferir a estrutura e a qualidade de um CSV antes de uma análise ou de treinar um modelo. Use quando receber uma base nova ou quando pedirem uma revisão da qualidade dos dados.
---

# Conferir um CSV

1. Identifique o arquivo e a finalidade da análise. Se a finalidade não foi informada, pergunte.
2. Confira separador, nomes das colunas e o que cada linha representa.
3. Calcule com código: linhas, colunas, tipos, valores ausentes e linhas duplicadas.
4. Textos vazios ou só com espaços contam como ausência. Ausência é diferente de zero.
5. Procure números guardados como texto e valores que não fazem sentido para a coluna.
6. Nunca altere o arquivo original. Não apague nem preencha dados sem explicar a regra.
7. Se a base for usada para prever algo, aponte qual é o alvo e quais colunas poderiam "entregar a resposta".
8. Salve um resumo em resultados/qualidade.md: problemas encontrados, evidências (números) e tratamentos propostos.

Não invente o significado das colunas. Uma amostra de linhas não comprova a qualidade do arquivo inteiro.
