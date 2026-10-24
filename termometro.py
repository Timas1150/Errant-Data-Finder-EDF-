import os
import matplotlib.pyplot as plt

# Configuração de estilo geral para publicação (seguindo a skill chart-image)
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8

# Definindo os pontos conhecidos: (temperatura em ºC, corrente em mA)
# Ponto 1: (0 ºC, 4 mA)
x1, y1 = 0, 4

# Ponto 2: (100 ºC, 20 mA)
x2, y2 = 100, 20

# Calculando os coeficientes da equação da reta (y = a*x + b)
a = (y2 - y1) / (x2 - x1)
b = y1 - a * x1

# Valor de teste para a temperatura (x)
x_teste = 50
y_resultado = a * x_teste + b

# Exibindo os coeficientes e o resultado do cálculo
print("=== CALIBRAÇÃO DO TERMÔMETRO (TRANSMISSOR 4-20 mA) ===")
print(f"Coeficiente A: {a}")
print(f"Coeficiente B: {b}")
print(f"Equação da reta: y = {a} * x + {b}")
print(f"Para temperatura de {x_teste} ºC, a corrente calculada é: {y_resultado} mA")

# 1. Classificação da temperatura
if x_teste <= 30:
    classificacao = "Baixa"
elif x_teste <= 60:
    classificacao = "Média"
else:
    classificacao = "Alta"

print(f"Classificação da temperatura ({x_teste} ºC): {classificacao}")

# 2. Avisos de limites
if x_teste < 0 or x_teste > 100:
    print(f"[AVISO] A temperatura ({x_teste} ºC) está fora da faixa permitida de 0 a 100 ºC!")

if y_resultado < 4 or y_resultado > 20:
    print(f"[AVISO] A corrente elétrica ({y_resultado} mA) está fora da faixa permitida de 4 a 20 mA!")

# 3. Gerando o gráfico com qualidade editorial (skill chart-image)
temperaturas = [0, 100]
correntes = [a * 0 + b, a * 100 + b]

fig, ax = plt.subplots(figsize=(10, 6))

# 3.1. Faixas de classificação da temperatura no fundo (background)
ax.axvspan(0, 30, color="#E3F2FD", alpha=0.7, label="Faixa Baixa (≤ 30 ºC)")
ax.axvspan(30, 60, color="#FFF9C4", alpha=0.7, label="Faixa Média (31 a 60 ºC)")
ax.axvspan(60, 100, color="#FFEBEE", alpha=0.7, label="Faixa Alta (> 60 ºC)")

# 3.2. Linhas operacionais de limites elétricos (4 a 20 mA)
ax.axhline(4, color="#757575", linestyle=":", linewidth=1.2, label="Limite Mínimo (4 mA)")
ax.axhline(20, color="#757575", linestyle=":", linewidth=1.2, label="Limite Máximo (20 mA)")

# 3.3. Curva linear do transmissor
ax.plot(temperaturas, correntes, label=f"Curva do Sensor: y = {a}x + {b}", color="#1565C0", linewidth=2.5, zorder=4)

# 3.4. Ponto de teste com destaque e anotação explicativa
ax.scatter([x_teste], [y_resultado], color="#D32F2F", s=130, zorder=5, label=f"Ponto de Teste ({x_teste} ºC, {y_resultado} mA)")
ax.annotate(
    f"Ponto de Teste: {x_teste} ºC -> {y_resultado:.1f} mA\n(Classificação: {classificacao})",
    xy=(x_teste, y_resultado),
    xytext=(x_teste - 20, y_resultado + 2.5),
    arrowprops=dict(facecolor="#D32F2F", arrowstyle="->", lw=1.5),
    fontsize=10,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.4", fc="#FFFFFF", ec="#D32F2F", lw=1.2)
)

# Configurações de eixos, títulos e grid
ax.set_title("Calibração e Faixas do Transmissor de Temperatura (4-20 mA)", fontsize=13, fontweight="bold", pad=12)
ax.set_xlabel("Temperatura (ºC)", fontsize=11, labelpad=8)
ax.set_ylabel("Corrente Elétrica (mA)", fontsize=11, labelpad=8)
ax.set_xlim(-5, 105)
ax.set_ylim(2, 22)
ax.grid(True, linestyle="--", alpha=0.5)
ax.legend(loc="lower right", frameon=True, facecolor="#ffffff", framealpha=0.9, fontsize=9)

fig.text(0.5, 0.01, "Fonte: Calibração Linear y = 0.16x + 4.0 | Skill Chart-Image", ha="center", fontsize=9, color="#555555")
plt.tight_layout(rect=[0, 0.03, 1, 0.96])

# Salvando com 150 DPI na pasta resultados/
os.makedirs("resultados", exist_ok=True)
caminho_grafico = os.path.join("resultados", "grafico_termometro.png")
plt.savefig(caminho_grafico, dpi=150)
plt.close()

print(f"Gráfico aprimorado do termômetro salvo em: {caminho_grafico}")
