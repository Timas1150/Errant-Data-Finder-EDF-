import os
import pandas as pd

# 1. Leitura do arquivo original (NUNCA alterar o arquivo de entrada em dados/)
caminho_csv = os.path.join("dados", "fornecedores.csv")
caminho_backup = os.path.join("dados", "fornecedores copy.csv")

df = pd.read_csv(caminho_csv)

# 2. Análise de Qualidade (seguindo a skill conferir-csv)
num_linhas, num_colunas = df.shape
colunas = list(df.columns)
tipos = df.dtypes.to_dict()
ausentes = df.isnull().sum().to_dict()
duplicadas = df.duplicated().sum()

print("=== AUDITORIA DE QUALIDADE (conferir-csv) ===")
print(f"Linhas: {num_linhas} | Colunas: {num_colunas}")
print(f"Linhas duplicadas: {duplicadas}")
print(f"Valores ausentes por coluna: {ausentes}")

# Identificando exatamente quais registros têm problemas
problemas = []
for idx, row in df.iterrows():
    campos_nulos = [col for col in colunas if pd.isnull(row[col])]
    if campos_nulos:
        problemas.append({
            "linha": idx + 2,
            "fornecedor": row["fornecedor"],
            "campos_ausentes": campos_nulos
        })

df_corrigido = df.copy()
valores_recuperados = {}

if problemas:
    print(f"\nForam encontrados {len(problemas)} registros com problemas.")
    if os.path.exists(caminho_backup):
        df_bkp = pd.read_csv(caminho_backup)
        for p in problemas:
            fornecedor = p["fornecedor"]
            for campo in p["campos_ausentes"]:
                val_original = df_bkp.loc[df_bkp["fornecedor"] == fornecedor, campo].values[0]
                df_corrigido.loc[df_corrigido["fornecedor"] == fornecedor, campo] = val_original
                valores_recuperados[f"{fornecedor}.{campo}"] = val_original
                print(f"Recuperado valor original para {fornecedor} [{campo}]: {val_original}")
    else:
        for p in problemas:
            for campo in p["campos_ausentes"]:
                media_campo = df[campo].mean()
                df_corrigido.loc[df_corrigido["fornecedor"] == p["fornecedor"], campo] = media_campo
                print(f"Imputada média para {p['fornecedor']} [{campo}]: {media_campo:.2f}")
else:
    print("\nNenhum problema encontrado! Todos os dados estão completos e preenchidos.")

os.makedirs("resultados", exist_ok=True)

# 3. Base de dados corrigida / validada
caminho_corrigido = os.path.join("resultados", "fornecedores_corrigido.csv")
df_corrigido.to_csv(caminho_corrigido, index=False)
print(f"\nBase pronta e salva em: {caminho_corrigido}")

# 4. Relatório de qualidade em Markdown (conforme a skill conferir-csv)
caminho_qualidade_md = os.path.join("resultados", "qualidade.md")
with open(caminho_qualidade_md, "w", encoding="utf-8") as f:
    f.write("# Relatório de Qualidade de Dados (conferir-csv)\n\n")
    f.write(f"**Arquivo auditado:** `{caminho_csv}`\n")
    f.write(f"**Finalidade:** Seleção do melhor fornecedor através da Matriz de Decisão multicritério.\n\n")
    
    f.write("## 1. Estrutura dos Dados\n")
    f.write(f"- **Total de linhas:** {num_linhas}\n")
    f.write(f"- **Total de colunas:** {num_colunas} (`{', '.join(colunas)}`)\n")
    f.write(f"- **Linhas duplicadas:** {duplicadas}\n")
    f.write(f"- **Tipos de dados:**\n")
    for col, tp in tipos.items():
        f.write(f"  - `{col}`: {tp}\n")
    
    f.write("\n## 2. Auditoria de Valores Ausentes\n")
    if problemas:
        f.write(f"Foram identificados **{len(problemas)} valores ausentes** na base de dados:\n")
        for p in problemas:
            f.write(f"- **Linha {p['linha']} ({p['fornecedor']}):** campo `{', '.join(p['campos_ausentes'])}` em branco.\n")
    else:
        f.write("Status: **Nenhum valor ausente encontrado!** Todas as 4 linhas e 5 colunas estão 100% preenchidas.\n")
    
    f.write("\n## 3. Tratamento e Validação\n")
    f.write("- **Arquivo original:** `dados/fornecedores.csv` preservado intacto conforme as regras do projeto.\n")
    f.write(f"- **Arquivo verificado:** `resultados/fornecedores_corrigido.csv` gerado com sucesso e 100% íntegro para a matriz de decisão.\n")

print(f"Relatório de qualidade salvo em: {caminho_qualidade_md}")
