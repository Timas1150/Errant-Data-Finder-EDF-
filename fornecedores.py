import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Configuração de estilo geral para publicação (seguindo a skill chart-image)
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8

# 1. Carregando os dados de entrada
caminho_dados = os.path.join("dados", "fornecedores.csv")
df = pd.read_csv(caminho_dados)

# 2. Definindo os pesos dos critérios (soma = 100%)
pesos = {
    "preco_unitario": 0.30,   # Preço: 30% (menor é melhor)
    "prazo_dias": 0.20,       # Prazo de entrega: 20% (menor é melhor)
    "defeitos_pct": 0.30,     # Qualidade/Defeitos: 30% (menor é melhor)
    "suporte_nota": 0.20      # Atendimento/Suporte: 20% (maior é melhor)
}

# 3. Normalização das notas para escala de 1 a 10 (onde 10 é a melhor nota)
def normalizar_menor_melhor(serie):
    min_val, max_val = serie.min(), serie.max()
    if max_val == min_val:
        return pd.Series(10.0, index=serie.index)
    return 1.0 + 9.0 * (max_val - serie) / (max_val - min_val)

def normalizar_maior_melhor(serie):
    min_val, max_val = serie.min(), serie.max()
    if max_val == min_val:
        return pd.Series(10.0, index=serie.index)
    return 1.0 + 9.0 * (serie - min_val) / (max_val - min_val)

df_notas = pd.DataFrame()
df_notas["fornecedor"] = df["fornecedor"]
df_notas["nota_preco"] = normalizar_menor_melhor(df["preco_unitario"])
df_notas["nota_prazo"] = normalizar_menor_melhor(df["prazo_dias"])
df_notas["nota_defeitos"] = normalizar_menor_melhor(df["defeitos_pct"])
df_notas["nota_suporte"] = normalizar_maior_melhor(df["suporte_nota"])

# 4. Cálculo da pontuação final ponderada
df_notas["pontuacao_final"] = (
    df_notas["nota_preco"] * pesos["preco_unitario"] +
    df_notas["nota_prazo"] * pesos["prazo_dias"] +
    df_notas["nota_defeitos"] * pesos["defeitos_pct"] +
    df_notas["nota_suporte"] * pesos["suporte_nota"]
)

df_ranking = df_notas.sort_values(by="pontuacao_final", ascending=False).reset_index(drop=True)
melhor = df_ranking.iloc[0]

print("=== RANKING FINAL DOS FORNECEDORES ===")
for i, linha in df_ranking.iterrows():
    print(f"{i+1} Lugar: {linha['fornecedor']} - Pontuacao: {linha['pontuacao_final']:.2f}")

print(f"\nMelhor Fornecedor Recomendado: {melhor['fornecedor']} com nota {melhor['pontuacao_final']:.2f}")

os.makedirs("resultados", exist_ok=True)

# 5.1. Atualizando o Relatório em Markdown
caminho_relatorio = os.path.join("resultados", "relatorio_fornecedores.md")
with open(caminho_relatorio, "w", encoding="utf-8") as f:
    f.write("# Relatório de Seleção de Fornecedores - Decision Matrix & Chart-Image\n\n")
    f.write("## 1. Contexto e Alternativas\n")
    f.write("Análise comparativa multicritério entre os 4 fornecedores avaliados:\n\n")
    f.write("| Fornecedor | Preço Unitário (R$) | Prazo (dias) | Defeitos (%) | Suporte (nota 0-10) |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- |\n")
    for _, row in df.iterrows():
        f.write(f"| {row['fornecedor']} | R$ {row['preco_unitario']:.2f} | {row['prazo_dias']} | {row['defeitos_pct']}% | {row['suporte_nota']} |\n")
    
    f.write("\n## 2. Critérios e Pesos\n")
    f.write("- **Preço Unitário:** 30% (menor custo = maior nota)\n")
    f.write("- **Prazo de Entrega:** 20% (menor prazo = maior nota)\n")
    f.write("- **Taxa de Defeitos:** 30% (menor índice de defeitos = maior nota)\n")
    f.write("- **Nota de Suporte:** 20% (melhor atendimento = maior nota)\n\n")
    
    f.write("## 3. Matriz de Decisão (Notas de 1 a 10 e Pontuação Final)\n\n")
    f.write("| Posição | Fornecedor | Nota Preço | Nota Prazo | Nota Defeitos | Nota Suporte | Pontuação Final |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
    for i, row in df_ranking.iterrows():
        destaque = " ⭐ **Vencedor**" if i == 0 else ""
        f.write(f"| {i+1}º | **{row['fornecedor']}**{destaque} | {row['nota_preco']:.2f} | {row['nota_prazo']:.2f} | {row['nota_defeitos']:.2f} | {row['nota_suporte']:.2f} | **{row['pontuacao_final']:.2f}** |\n")
    
    f.write(f"\n## 4. Gráficos Gerados na Pasta `resultados/`\n")
    f.write("1. `grafico_fornecedores.png`: Visão comparativa dupla (Ranking ponderado + detalhamento por critério).\n")
    f.write("2. `grafico_tradeoff_custo_qualidade.png`: Dispersão de Preço x Defeitos com zonas de decisão.\n")
    f.write("3. `grafico_radar_fornecedores.png`: Gráfico radar mostrando o perfil multicritério de cada fornecedor.\n")

print(f"Relatório atualizado em: {caminho_relatorio}")

# 5.2. Salvando o arquivo específico com o resultado do melhor fornecedor
caminho_melhor = os.path.join("resultados", "melhor_fornecedor.txt")
with open(caminho_melhor, "w", encoding="utf-8") as f:
    f.write(f"=== MELHOR FORNECEDOR RECOMENDADO ===\n")
    f.write(f"Fornecedor: {melhor['fornecedor']}\n")
    f.write(f"Pontuacao Final Ponderada: {melhor['pontuacao_final']:.2f} (de 10.0)\n")
    f.write(f"Preco Unitario: R$ {df.loc[df['fornecedor'] == melhor['fornecedor'], 'preco_unitario'].values[0]:.2f}\n")
    f.write(f"Prazo de Entrega: {df.loc[df['fornecedor'] == melhor['fornecedor'], 'prazo_dias'].values[0]} dias\n")
    f.write(f"Taxa de Defeitos: {df.loc[df['fornecedor'] == melhor['fornecedor'], 'defeitos_pct'].values[0]}%\n")
    f.write(f"Nota de Suporte: {df.loc[df['fornecedor'] == melhor['fornecedor'], 'suporte_nota'].values[0]}\n")
    f.write(f"Criterio de Decisao: Maior equilibrio multicriterio ponderado (Decision Matrix)\n")
print(f"Resultado do melhor fornecedor salvo em: {caminho_melhor}")

# ==============================================================================
# GRÁFICO 1: Comparativo Aprimorado (Ranking Geral + Comparação por Critério)
# ==============================================================================
caminho_grafico_1 = os.path.join("resultados", "grafico_fornecedores.png")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Painel 1: Ranking Geral Ponderado
cores_ranking = ["#2E7D32" if f == melhor["fornecedor"] else "#1976D2" for f in df_ranking["fornecedor"]]
barras = ax1.bar(df_ranking["fornecedor"], df_ranking["pontuacao_final"], color=cores_ranking, width=0.55, edgecolor="#222222", linewidth=0.7)
ax1.set_title("1. Pontuação Final Ponderada (Ranking Geral)", fontsize=13, fontweight="bold", pad=12)
ax1.set_xlabel("Fornecedor", fontsize=11, labelpad=8)
ax1.set_ylabel("Pontuação Ponderada (Escala 1 a 10)", fontsize=11, labelpad=8)
ax1.set_ylim(0, 10.5)
ax1.grid(axis="y", linestyle="--", alpha=0.5)

for barra in barras:
    yval = barra.get_height()
    ax1.text(barra.get_x() + barra.get_width() / 2, yval + 0.25, f"{yval:.2f}", ha="center", va="bottom", fontsize=11, fontweight="bold")

ax1.axhline(melhor["pontuacao_final"], color="#2E7D32", linestyle=":", linewidth=1.8, label=f"Vencedor: {melhor['fornecedor']} ({melhor['pontuacao_final']:.2f})")
ax1.legend(loc="upper right", frameon=True, facecolor="#ffffff")

# Painel 2: Comparação por Critério
criterios = ["Preço\n(30%)", "Prazo\n(20%)", "Defeitos\n(30%)", "Suporte\n(20%)"]
colunas_criterios = ["nota_preco", "nota_prazo", "nota_defeitos", "nota_suporte"]

fornecedores_lista = df["fornecedor"].tolist()
x = np.arange(len(criterios))
largura = 0.18
paleta_fornec = ["#D32F2F", "#2E7D32", "#F57C00", "#7B1FA2"]  # Alfa, Beta, Gama, Delta

for i, forn in enumerate(fornecedores_lista):
    dados_forn = df_notas[df_notas["fornecedor"] == forn][colunas_criterios].values[0]
    posicao = x + (i - 1.5) * largura
    barras_crit = ax2.bar(posicao, dados_forn, largura, label=forn, color=paleta_fornec[i], edgecolor="#333333", linewidth=0.6)
    for b in barras_crit:
        y = b.get_height()
        ax2.text(b.get_x() + b.get_width() / 2, y + 0.2, f"{y:.1f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

ax2.set_title("2. Notas Detalhadas por Critério (Escala 1 a 10)", fontsize=13, fontweight="bold", pad=12)
ax2.set_xlabel("Critério Avaliado", fontsize=11, labelpad=8)
ax2.set_ylabel("Nota Normalizada (1 a 10)", fontsize=11, labelpad=8)
ax2.set_xticks(x)
ax2.set_xticklabels(criterios, fontsize=10)
ax2.set_ylim(0, 11.5)
ax2.grid(axis="y", linestyle="--", alpha=0.5)
ax2.legend(title="Fornecedor", loc="upper right", frameon=True, facecolor="#ffffff")

fig.suptitle("Análise Comparativa de Fornecedores - Decision Matrix", fontsize=15, fontweight="bold", y=0.98)
fig.text(0.5, 0.01, "Fonte: dados/fornecedores.csv | Metodologia: Skill Decision Matrix + Chart-Image", ha="center", fontsize=9, color="#555555")
plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig(caminho_grafico_1, dpi=150)
plt.close()
print(f"Gráfico 1 salvo em: {caminho_grafico_1}")

# ==============================================================================
# GRÁFICO 2: Trade-off Custo x Taxa de Defeitos (Qualidade)
# ==============================================================================
caminho_grafico_2 = os.path.join("resultados", "grafico_tradeoff_custo_qualidade.png")
fig, ax = plt.subplots(figsize=(9, 6))

for i, row in df.iterrows():
    ax.scatter(row["preco_unitario"], row["defeitos_pct"], color=paleta_fornec[i], s=250, edgecolor="#111111", linewidth=1.2, zorder=5)
    ax.annotate(
        f"{row['fornecedor']}\n(R$ {row['preco_unitario']:.0f} | {row['defeitos_pct']}% def.)",
        (row["preco_unitario"], row["defeitos_pct"]),
        textcoords="offset points",
        xytext=(10, 8),
        fontsize=10,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="#ffffff", ec=paleta_fornec[i], alpha=0.9)
    )

media_preco = df["preco_unitario"].mean()
media_defeitos = df["defeitos_pct"].mean()

ax.axvline(media_preco, color="#888888", linestyle="--", linewidth=1, label=f"Preço Médio (R$ {media_preco:.1f})")
ax.axhline(media_defeitos, color="#888888", linestyle=":", linewidth=1, label=f"Taxa Média de Defeitos ({media_defeitos:.1f}%)")

ax.text(82, 0.3, "Zona Ideal\n(Baixo Preço & Poucos Defeitos)", fontsize=9, color="#2E7D32", fontweight="bold", bbox=dict(boxstyle="square", fc="#E8F5E9", ec="#81C784"))
ax.text(101, 3.7, "Zona Desfavorável\n(Alto Preço & Muitos Defeitos)", fontsize=9, color="#C62828", fontweight="bold", bbox=dict(boxstyle="square", fc="#FFEBEE", ec="#E57373"))

ax.set_title("Trade-off: Preço Unitário vs Taxa de Defeitos", fontsize=13, fontweight="bold", pad=12)
ax.set_xlabel("Preço Unitário (R$) - Menor é melhor", fontsize=11, labelpad=8)
ax.set_ylabel("Taxa de Defeitos (%) - Menor é melhor", fontsize=11, labelpad=8)
ax.set_xlim(80, 115)
ax.set_ylim(0, 4.5)
ax.grid(True, linestyle="--", alpha=0.5)
ax.legend(loc="upper left", frameon=True, facecolor="#ffffff")

fig.text(0.5, 0.01, "Fonte: dados/fornecedores.csv | Skill Chart-Image", ha="center", fontsize=9, color="#555555")
plt.tight_layout(rect=[0, 0.03, 1, 0.96])
plt.savefig(caminho_grafico_2, dpi=150)
plt.close()
print(f"Gráfico 2 salvo em: {caminho_grafico_2}")

# ==============================================================================
# GRÁFICO 3: Perfil Radar Multicritério dos Fornecedores
# ==============================================================================
caminho_grafico_3 = os.path.join("resultados", "grafico_radar_fornecedores.png")

categorias_radar = ["Preço", "Prazo", "Qualidade (Defeitos)", "Suporte"]
num_vars = len(categorias_radar)

angulos = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
angulos += angulos[:1]  # Fechar o círculo

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

for i, forn in enumerate(fornecedores_lista):
    valores = df_notas[df_notas["fornecedor"] == forn][colunas_criterios].values[0].tolist()
    valores += valores[:1]  # Fechar o polígono
    
    linha_estilo = "-" if forn == melhor["fornecedor"] else "--"
    largura_linha = 2.5 if forn == melhor["fornecedor"] else 1.5
    
    ax.plot(angulos, valores, color=paleta_fornec[i], linewidth=largura_linha, linestyle=linha_estilo, label=forn)
    ax.fill(angulos, valores, color=paleta_fornec[i], alpha=0.15)

ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)

ax.set_xticks(angulos[:-1])
ax.set_xticklabels(categorias_radar, fontsize=11, fontweight="bold")

ax.set_rlabel_position(0)
plt.yticks([2, 4, 6, 8, 10], ["2", "4", "6", "8", "10"], color="#666666", size=9)
plt.ylim(0, 10.5)

plt.title("Perfil Multicritério dos Fornecedores (Gráfico Radar)", size=14, fontweight="bold", y=1.08)
plt.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), title="Fornecedores", frameon=True)

fig.text(0.5, 0.02, "Fonte: dados/fornecedores.csv | Escala de 1 a 10 (10 = melhor desempenho)", ha="center", fontsize=9, color="#555555")
plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig(caminho_grafico_3, dpi=150)
plt.close()
print(f"Gráfico 3 salvo em: {caminho_grafico_3}")
