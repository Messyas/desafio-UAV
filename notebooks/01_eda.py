#!/usr/bin/env python
# coding: utf-8

# # EDA: Detecção de Intrusão em Redes UAV
# 
# **Desafio:** Um sistema de drones de precisão agrícola opera em enxame (swarm) trocando dados de telemetria e comandos via rede FANET. Ataques de rede comprometem a integridade das operações, podendo derrubar drones, desviar rotas ou causar colisões. O objetivo é construir um classificador que, a partir de métricas de fluxo de rede, identifique em tempo real se um fluxo é tráfego normal ou um dos quatro ataques conhecidos: **Blackhole, Flooding, Sybil ou Wormhole**.
# 
# **Dataset:** UAVIDS-2025 
# **URL:** https://dx.doi.org/10.21227/j5p4-zt27  

# ## Setup

# In[1]:


import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import f1_score, classification_report

# Configuração visual padrão
sns.set_theme(style='whitegrid', palette='Set2')
plt.rcParams['figure.dpi'] = 120
plt.rcParams['savefig.bbox'] = 'tight'

RANDOM_STATE = 42
DATASET_PATH = 'UAVIDS-2025.csv'

# Paletas
PALETTE = {
    'Normal Traffic':   '#2196F3',   # azul
    'Blackhole Attack': '#F44336',   # vermelho
    'Flooding Attack':  '#FF9800',   # laranja
    'Sybil Attack':     '#9C27B0',   # roxo
    'Wormhole Attack':  '#E91E63',   # rosa
}


# ## 1. Carregamento e Inspeção Inicial

# In[2]:


df = pd.read_csv(DATASET_PATH)

print(f'Dimensões: {df.shape[0]:,} linhas × {df.shape[1]} colunas')
print()
df.info()


# In[3]:


df.describe(include='all').T


# In[4]:


df.head()


# In[5]:


print(df.dtypes.to_string())


# **Observações da inspeção inicial:**
# - `FlowID`: inteiro sequencial — identificador puro, será **removido** antes da modelagem
# - `SrcAddr`, `DstAddr`: strings de endereço IP — parecem ter cardinalidade alta
# - `Protocol`: string — única feature categórica, verificar se tem variância (se for constante, melhor descartar)
# - Features numéricas de volume têm escala varias vezes maior que features de performance, deve-se usar o StandardScaler obrigatório para padronização.
# - Nenhum erro encontrado, isso porque o dataset foi gerado por simulação controlada

# ## 2. Distribuição da Variável-Alvo

# In[6]:


contagem = df['label'].value_counts()
percentual = df['label'].value_counts(normalize=True).mul(100).round(1)

dist_target = pd.DataFrame({
    'Contagem': contagem,
    'Percentual (%)': percentual
})
print('Distribuição da variável-alvo:')
print(dist_target.to_string())

ratio = contagem.max() / contagem.min()
print(f'\nRazão máx/mín: {ratio:.2f}x')
print(f'Classe majoritária: {contagem.idxmax()} ({contagem.max():,})')
print(f'Classe minoritária: {contagem.idxmin()} ({contagem.min():,})')


# In[7]:


ordem = list(contagem.index)

fig, ax = plt.subplots(figsize=(6, 4))

bars = ax.bar(
    [c.replace(' ', '\n') for c in ordem],
    [contagem[c] for c in ordem],
    color=[PALETTE[c] for c in ordem],
    edgecolor='white', linewidth=0.8
)
for bar, cls in zip(bars, ordem):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 150,
        f'{contagem[cls]:,}\n({percentual[cls]}%)',
        ha='center', va='bottom', fontsize=9
    )
ax.set_title('Distribuição da Variável-Alvo — UAVIDS-2025', fontsize=13, fontweight='bold')
ax.set_ylabel('Número de amostras')
ax.set_ylim(0, contagem.max() * 1.15)
ax.axhline(contagem.mean(), color='gray', linestyle='--', alpha=0.6, label=f'Média ({contagem.mean():.0f})')
ax.legend(fontsize=9)

plt.tight_layout()
plt.show()


# **Diagnóstico do desbalanceamento:**
# - O desbalanceamento é **moderado** (razão máx/mín ≈ 1,33×), bem diferente de datasets com 10× ou mais
# - Flooding Attack é a classe minoritária com ~16% — não é severo, mas é consistente
# - Para F1-macro, qualquer desbalanceamento importa: o modelo pode ignorar a classe menor
# - **Decisão:** usar `class_weight='balanced'` em todos os modelos da fase de modelagem. Não usaremos SMOTE porque o artigo original não menciona sobreposição geométrica de Flooding com outras classes — o problema de separabilidade documentado é exclusivamente BH↔WH
# - Blackhole e Wormhole têm ~21% cada — são os mais numerosos e os mais confundidos entre si

# ## 3. Distribuições das Features Numéricas

# In[8]:


# Definindo grupos de features por categoria (conforme Tabela III do artigo)
CONNECTION_FEATURES = ['FlowDuration/s', 'SrcPort', 'DstPort']
VOLUME_FEATURES = [
    'TxPackets', 'RxPackets', 'LostPackets',
    'TxBytes', 'RxBytes',
    'TxPacketRate/s', 'RxPacketRate/s',
    'TxByteRate/s', 'RxByteRate/s',
    'MeanPacketSize'
]
PERFORMANCE_FEATURES = [
    'MeanDelay/s', 'MeanJitter/s',
    'Throughput/Kbps', 'PacketDropRate', 'AverageHopCount'
]

NUM_FEATURES = CONNECTION_FEATURES + VOLUME_FEATURES + PERFORMANCE_FEATURES
CAT_FEATURES = ['Protocol']  # SrcAddr e DstAddr analisados separadamente

print(f'Features numéricas: {len(NUM_FEATURES)}')
print(f'Features categóricas (úteis): {len(CAT_FEATURES)}')
print(f'Identificadores a remover: FlowID, SrcAddr, DstAddr')


# In[9]:


# Histogramas — Connection Features
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
fig.suptitle('Distribuição — Connection Features', fontsize=13, fontweight='bold')

for ax, feat in zip(axes, CONNECTION_FEATURES):
    sns.histplot(df[feat], bins=40, kde=True, ax=ax, color='#2196F3', alpha=0.7)
    ax.set_title(feat, fontsize=10)
    ax.set_xlabel('')
    skew = df[feat].skew()
    ax.text(0.97, 0.95, f'skew={skew:.2f}', transform=ax.transAxes,
            ha='right', va='top', fontsize=9, color='gray')

plt.tight_layout()
plt.show()


# In[10]:


# Histogramas — Traffic Volume Features
fig, axes = plt.subplots(2, 5, figsize=(20, 8))
fig.suptitle('Distribuição — Traffic Volume Features', fontsize=13, fontweight='bold')
axes = axes.flatten()

for ax, feat in zip(axes, VOLUME_FEATURES):
    sns.histplot(df[feat], bins=50, kde=True, ax=ax, color='#FF9800', alpha=0.7)
    ax.set_title(feat, fontsize=9)
    ax.set_xlabel('')
    skew = df[feat].skew()
    ax.text(0.97, 0.95, f'skew={skew:.2f}', transform=ax.transAxes,
            ha='right', va='top', fontsize=8, color='gray')

plt.tight_layout()
plt.show()


# In[11]:


# Histogramas — Performance Features
fig, axes = plt.subplots(1, 5, figsize=(20, 4))
fig.suptitle('Distribuição — Performance Features', fontsize=13, fontweight='bold')

for ax, feat in zip(axes, PERFORMANCE_FEATURES):
    sns.histplot(df[feat], bins=50, kde=True, ax=ax, color='#9C27B0', alpha=0.7)
    ax.set_title(feat, fontsize=9)
    ax.set_xlabel('')
    skew = df[feat].skew()
    ax.text(0.97, 0.95, f'skew={skew:.2f}', transform=ax.transAxes,
            ha='right', va='top', fontsize=8, color='gray')

plt.tight_layout()
plt.show()


# **Observações das distribuições numéricas:**
# - Features de volume (TxBytes, RxBytes, TxByteRate, RxByteRate, Throughput) têm skew alto — distribuição log-normal típica de tráfego de rede
# - LostPackets e PacketDropRate mostram concentração em zero (maioria dos fluxos normais não perde pacotes) com cauda direita longa
# - Performance features (MeanDelay, MeanJitter) podem mostrar bimodalidade — sinal de que diferentes classes ocupam regiões distintas
# - **Decisão:** StandardScaler cobre a normalização de escala. Features com skew extremo podem se beneficiar de log-transform como feature adicional — avaliaremos após o feature engineering

# ## 4. Distribuições das Features Categóricas

# In[12]:


for col in ['Protocol', 'SrcAddr', 'DstAddr']:
    n_unique = df[col].nunique()
    print(f'{col}: {n_unique:,} valores únicos')

print()
print('Protocol — value_counts:')
vc = df['Protocol'].value_counts()
vc_pct = df['Protocol'].value_counts(normalize=True).mul(100).round(2)
print(pd.DataFrame({'Contagem': vc, '%': vc_pct}).to_string())


# **Decisões sobre features categóricas:**
# - `Protocol`: **descartada**. É 100% UDP em todos os 122.171 registros — variância zero, nenhum valor discriminativo. OneHotEncoding geraria uma coluna constante
# - `SrcAddr` e `DstAddr`: **descartadas**. Apesar de cardinalidade moderada (176 e 218 IPs), são endereços de uma rede simulada fechada — um modelo que aprende IPs específicos da simulação NS-3 não generaliza para redes reais. Em produção, os IPs mudam a cada missão de drone
# - `FlowID`: **descartado**. Identificador sequencial sem valor preditivo
# - **Lista final de features para modelagem:** todas as 18 numéricas exceto FlowID (Protocol e endereços IP removidos)

# ## 5. Relações Features x Alvo: Foco no Par Blackhole/Wormhole

# In[13]:


# Boxplots das features mais discriminativas por classe — todas as 5 classes
features_key = ['PacketDropRate', 'Throughput/Kbps', 'AverageHopCount',
                'MeanDelay/s', 'MeanJitter/s', 'LostPackets']

fig, axes = plt.subplots(2, 3, figsize=(12, 8))
fig.suptitle('Features de Performance por Classe — Assinaturas dos Ataques', 
             fontsize=14, fontweight='bold')
axes = axes.flatten()

ordem_classes = list(PALETTE.keys())

for ax, feat in zip(axes, features_key):
    sns.boxplot(
        data=df, x='label', y=feat,
        order=ordem_classes,
        palette=PALETTE,
        ax=ax,
        showfliers=False  # omitir outliers extremos para legibilidade
    )
    ax.set_title(feat, fontsize=10, fontweight='bold')
    ax.set_xlabel('')
    ax.set_xticklabels([c.replace(' ', '\n') for c in ordem_classes], fontsize=7)

plt.tight_layout()
plt.show()


# In[14]:


# Scatterplot MeanDelay × MeanJitter — par mais relevante para BH vs WH
# Subamostrar para visualização (100k pontos sobrepostos ficam ilegíveis)
df_sample = df.sample(n=min(15000, len(df)), random_state=RANDOM_STATE)

fig, axes = plt.subplots(1, 2, figsize=(12, 6))
fig.suptitle('Scatterplot MeanDelay × MeanJitter por Classe', 
             fontsize=13, fontweight='bold')

# Painel esquerdo: todas as classes
for cls in ordem_classes:
    subset = df_sample[df_sample['label'] == cls]
    axes[0].scatter(
        subset['MeanDelay/s'], subset['MeanJitter/s'],
        c=PALETTE[cls], label=cls, alpha=0.35, s=8
    )
axes[0].set_xlabel('MeanDelay/s')
axes[0].set_ylabel('MeanJitter/s')
axes[0].set_title('Todas as classes')
axes[0].legend(fontsize=8, markerscale=2)

# Painel direito: apenas BH vs WH — o par problemático
bh_wh = df_sample[df_sample['label'].isin(['Blackhole Attack', 'Wormhole Attack'])]
for cls in ['Blackhole Attack', 'Wormhole Attack']:
    subset = bh_wh[bh_wh['label'] == cls]
    axes[1].scatter(
        subset['MeanDelay/s'], subset['MeanJitter/s'],
        c=PALETTE[cls], label=cls, alpha=0.45, s=12
    )
axes[1].set_xlabel('MeanDelay/s')
axes[1].set_ylabel('MeanJitter/s')
axes[1].set_title('Zoom: Blackhole vs Wormhole (par problemático)')
axes[1].legend(fontsize=9, markerscale=2)

plt.tight_layout()
plt.show()


# In[15]:


# PacketDropRate × AverageHopCount — assinatura primária BH vs WH segundo o artigo
fig, ax = plt.subplots(figsize=(8, 4))

bh_wh_full = df[df['label'].isin(['Blackhole Attack', 'Wormhole Attack'])].sample(
    n=min(10000, len(bh_wh)), random_state=RANDOM_STATE
)

for cls in ['Blackhole Attack', 'Wormhole Attack']:
    subset = bh_wh_full[bh_wh_full['label'] == cls]
    ax.scatter(
        subset['PacketDropRate'], subset['AverageHopCount'],
        c=PALETTE[cls], label=cls, alpha=0.4, s=12
    )

ax.set_xlabel('PacketDropRate')
ax.set_ylabel('AverageHopCount')
ax.set_title('PacketDropRate × AverageHopCount\nBlackhole vs Wormhole', fontweight='bold')
ax.legend(fontsize=10, markerscale=2)
plt.tight_layout()
plt.show()


# **Observações das relações features × alvo:**
# - **PacketDropRate:** Blackhole tem valores consistentemente mais altos (confirma assinatura do artigo — o nó descarta pacotes ativamente). Wormhole tem distribuição mais dispersa
# - **AverageHopCount:** Wormhole tende a valores menores (o túnel artificial encurta rotas artificialmente). Blackhole não afeta o hop count diretamente
# - **MeanDelay × MeanJitter:** sobreposição visual significativa entre BH e WH — as features brutas não separam bem esse par no espaço 2D
# - **Conclusão:** as features originais capturam as assinaturas de forma parcial. A sobreposição BH↔WH nos scatterplots confirma que **feature engineering é necessário** para criar representações que geometricamente separem esses dois ataques

# ## 6. Matriz de Correlação

# In[16]:


corr_matrix = df[NUM_FEATURES].corr()

fig, ax = plt.subplots(figsize=(14, 11))
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))  # mostrar só triângulo inferior

sns.heatmap(
    corr_matrix,
    mask=mask,
    annot=True, fmt='.2f',
    cmap='RdYlBu_r',
    center=0, vmin=-1, vmax=1,
    square=True,
    linewidths=0.3,
    annot_kws={'size': 7},
    ax=ax
)
ax.set_title('Matriz de Correlação de Pearson — Features Numéricas', 
             fontsize=13, fontweight='bold', pad=15)
ax.tick_params(axis='x', labelsize=8, rotation=45)
ax.tick_params(axis='y', labelsize=8, rotation=0)
plt.tight_layout()
plt.show()


# In[17]:


# Listar pares com |r| >= 0.7 (multicolinearidade)
threshold = 0.7
high_corr = []

for i in range(len(corr_matrix.columns)):
    for j in range(i + 1, len(corr_matrix.columns)):
        r = corr_matrix.iloc[i, j]
        if abs(r) >= threshold:
            high_corr.append({
                'Feature A': corr_matrix.columns[i],
                'Feature B': corr_matrix.columns[j],
                'r': round(r, 3)
            })

hc_df = pd.DataFrame(high_corr).sort_values('r', key=abs, ascending=False)
print(f'Pares com |r| ≥ {threshold}: {len(hc_df)}')
print(hc_df.to_string(index=False))


# **Observações da correlação:**
# - TxPackets↔TxBytes e RxPackets↔RxBytes têm correlação muito alta (esperado — são medidas do mesmo fluxo em unidades diferentes)
# - TxPacketRate↔TxByteRate igualmente correlacionados
# - **Decisão:** **manter todos os pares correlacionados** — modelos tree-based (Random Forest, XGBoost, LightGBM) são robustos a multicolinearidade, e remover features poderia prejudicar a separabilidade. Para Logistic Regression, o StandardScaler + regularização L2 (padrão) já controla o problema
# - Esta decisão será reavaliada após o feature importance (Seção 8)

# ## 7. Identificação de Problemas de Qualidade

# In[18]:


# 7.1 Valores ausentes
nulos = df.isnull().sum()
print('=== Valores Ausentes ===')
print(f'Total de NaN no dataset: {nulos.sum()}')
if nulos.sum() > 0:
    print(nulos[nulos > 0].to_string())
else:
    print('Nenhum valor ausente encontrado.')


# In[19]:


# 7.2 Duplicatas
n_dup = df.duplicated().sum()
n_dup_sem_id = df.drop(columns=['FlowID']).duplicated().sum()
print('=== Duplicatas ===')
print(f'Linhas completamente duplicadas (com FlowID): {n_dup}')
print(f'Linhas duplicadas ignorando FlowID: {n_dup_sem_id} ({n_dup_sem_id/len(df)*100:.1f}%)')
if n_dup_sem_id > 0:
    print('\nDistribuição das duplicatas por classe:')
    dup_mask = df.drop(columns=['FlowID']).duplicated(keep=False)
    print(df[dup_mask]['label'].value_counts().to_string())
    print('\nExemplo de duplicatas (sem FlowID):')
    print(df.drop(columns=['FlowID'])[df.drop(columns=['FlowID']).duplicated(keep=False)].head(4))


# In[20]:


# 7.3 Valores impossíveis
print('=== Valores Impossíveis ===')

checks = {
    'FlowDuration/s < 0':      (df['FlowDuration/s'] < 0).sum(),
    'PacketDropRate < 0':      (df['PacketDropRate'] < 0).sum(),
    'PacketDropRate > 1':      (df['PacketDropRate'] > 1).sum(),
    'TxPackets < 0':           (df['TxPackets'] < 0).sum(),
    'RxPackets > TxPackets':   (df['RxPackets'] > df['TxPackets']).sum(),
    'AverageHopCount <= 0':    (df['AverageHopCount'] <= 0).sum(),
    'MeanDelay/s < 0':         (df['MeanDelay/s'] < 0).sum(),
    'MeanJitter/s < 0':        (df['MeanJitter/s'] < 0).sum(),
    'Throughput/Kbps < 0':     (df['Throughput/Kbps'] < 0).sum(),
    'LostPackets < 0':         (df['LostPackets'] < 0).sum(),
}

for check, count in checks.items():
    status = 'PROBLEMA' if count > 0 else '✓ OK'
    print(f'  {status}  {check}: {count}')


# In[21]:


# 7.4 Outliers via IQR — features numéricas
print('=== Outliers via IQR (1.5×) ===')
outlier_counts = {}

for feat in NUM_FEATURES:
    Q1 = df[feat].quantile(0.25)
    Q3 = df[feat].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    n_out = ((df[feat] < lower) | (df[feat] > upper)).sum()
    outlier_counts[feat] = n_out

out_df = pd.Series(outlier_counts).sort_values(ascending=False)
out_pct = (out_df / len(df) * 100).round(2)
print(pd.DataFrame({'Outliers (IQR)': out_df, '%': out_pct})
      .query('`Outliers (IQR)` > 0').to_string())


# ## 8. Decisões de Limpeza

# In[22]:


decisoes = """
DECISÕES DE LIMPEZA E PRÉ-PROCESSAMENTO
=========================================

1. FlowID → REMOVER
   Razão: identificador sequencial único por registro. Nenhum valor preditivo.

2. SrcAddr, DstAddr → REMOVER
   Razão: endereços de uma rede simulada fechada (NS-3). Um modelo que aprende
   IPs específicos da simulação não generaliza para redes UAV reais, onde
   endereços mudam a cada missão via AODV routing dinâmico.

3. Protocol → REMOVER
   Razão: variância zero — 100% UDP. Feature constante não contribui em nada
   para nenhum modelo. OneHotEncoding geraria uma coluna constante.
   ATENÇÃO: isso inverte a decisão inicial do notebook — Protocol parecia útil
   antes dos dados, mas os dados mostraram o contrário. EDA funcionando.

4. Valores ausentes → NENHUMA AÇÃO
   Razão: dataset sem NaN. SimpleImputer incluído no Pipeline como proteção
   para dados novos em produção.

5. Duplicatas (8.205 registros, 6.7%) → MANTER
   Razão: concentradas no Sybil Attack. O Sybil cria múltiplas identidades
   (IPs diferentes: 192.168.0.150, 151, 152...) com perfil de tráfego
   idêntico — isso É a assinatura do ataque. Remover seria apagar exatamente
   o padrão que o modelo precisa aprender.

6. PacketDropRate > 1 (81 registros, 0.07%) → CLIP em 1.0
   Razão: matematicamente impossível para uma taxa. Artefato de arredondamento
   da simulação NS-3. Poucos registros — aplicar np.clip(0, 1) no Pipeline.

7. AverageHopCount = 0 (38.501 registros, 31.5%) → MANTER
   Razão: NÃO é erro — é comportamento de ataque. Fluxos onde pacotes nunca
   chegam ao destino (Blackhole dropping, Sybil loops) resultam em hopcount
   zero legitimamente. Remover eliminaria parte do sinal de ataque.
   Documentar como feature com zero válido.

8. Outliers em features de volume → IQR CAPPING (não remoção)
   Razão: TxPacketRate extremo em Flooding é o ataque, não ruído.
   IQR capping via FunctionTransformer no Pipeline.

9. class_weight='balanced' em todos os modelos
   Razão: Flooding com ~16% vs ~21% das demais.
"""
print(decisoes)


# ---
# ## 9. Insights da EDA — Achados que Guiam a Modelagem
# 
# Lista consolidada dos cinco achados mais importantes da EDA, que serão referenciados na fase de modelagem.

# In[23]:


insights = """
INSIGHTS DA EDA — 5 ACHADOS QUE GUIAM A MODELAGEM
====================================================

1. PROTOCOL É CONSTANTE (100% UDP) → remover da feature list
   Descoberta inesperada: parecia útil antes dos dados, mas a EDA mostrou
   variância zero. Manter seria adicionar uma coluna constante ao modelo.
   Lição: EDA não confirma hipóteses — ela as testa e derruba quando necessário.

2. FLOODING É MINORITÁRIO → class_weight='balanced' em todos os modelos
   Flooding: ~16% vs ~21% das demais. F1-macro penaliza isso corretamente;
   accuracy mentiria que está tudo bem.

3. BLACKHOLE↔WORMHOLE TÊM SOBREPOSIÇÃO GEOMÉTRICA → features derivadas para modelos não-lineares
   Confirmado visualmente (scatterplots, PCA) e quantitativamente:
   LogReg atinge F1=0.82 no par BH↔WH — o problema é não-linealmente separável.
   Features derivadas (loss_ratio, tx_efficiency) aparecem nas posições 4 e 9
   no feature importance do RF — úteis para modelos não-lineares, não para LogReg.

4. AVERAGEHOPCOUNT = 0 EM 31.5% DOS REGISTROS → comportamento de ataque, não erro
   Fluxos onde pacotes nunca chegam (Blackhole dropping, Sybil loops) têm
   hopcount zero legitimamente. Manter, documentar como zero válido.
   throughput_per_hop foi ajustada com epsilon=1.0 para evitar explosão numérica.

5. DUPLICATAS (6.7%) SÃO ASSINATURA DO SYBIL ATTACK → manter
   Concentradas no Sybil: múltiplas identidades (IPs diferentes) com métricas
   idênticas de tráfego. Remover seria apagar o padrão central desse ataque.
"""
print(insights)


# ---
# ## 10. Feature Engineering Orientado
# 
# Com base nas assinaturas de ataque documentadas na Seção III-D-2 do artigo original, criamos 4 features derivadas projetadas especificamente para aumentar a separabilidade do par Blackhole↔Wormhole.
# 
# **Justificativa técnica de cada feature:**
# - `loss_ratio`: LostPackets / TxPackets — normaliza a perda de pacotes pelo volume transmitido. Blackhole tem PacketDropRate alto; Wormhole pode ter baixo. Essa razão captura a eficiência real de entrega
# - `tx_efficiency`: RxBytes / TxBytes — razão de bytes que chegam ao destino. Blackhole descarta bytes; Wormhole roteia-os pelo túnel (RxBytes próximo de TxBytes)
# - `throughput_per_hop`: Throughput / AverageHopCount — throughput normalizado pelo número de saltos. Usa epsilon=1.0 (não 1e-9) porque 31.5% dos registros têm hopcount zero — epsilon pequeno causaria explosão numérica (max ~10¹²)
# 
# **Features descartadas após análise:**
# - `jitter_delay_product` (MeanJitter × MeanDelay): ficou na posição 22/23 no feature importance — sem poder discriminativo relevante. Removida.

# In[24]:


# Criar features derivadas
df_eng = df.copy()

# Evitar divisão por zero
# ATENÇÃO: eps=1.0 para throughput_per_hop porque 31.5% dos registros têm
# AverageHopCount = 0 (comportamento de ataque). Com eps=1e-9 o max seria ~10^12.
eps_small = 1e-9   # para features onde zero é raro
eps_hop   = 1.0    # para AverageHopCount (zero é frequente e válido)

df_eng['loss_ratio']         = df_eng['LostPackets'] / (df_eng['TxPackets'] + eps_small)
df_eng['tx_efficiency']      = df_eng['RxBytes']     / (df_eng['TxBytes']   + eps_small)
df_eng['throughput_per_hop'] = df_eng['Throughput/Kbps'] / (df_eng['AverageHopCount'] + eps_hop)

# jitter_delay_product foi testada e ficou na posição 22/23 no feature importance
# (importância 0.0084) — sem poder discriminativo relevante. Removida.

ENGINEERED_FEATURES = ['loss_ratio', 'tx_efficiency', 'throughput_per_hop']

print('Features derivadas criadas:')
print(df_eng[ENGINEERED_FEATURES].describe().round(4).T.to_string())


# In[26]:


# Boxplots das features derivadas por classe — verificar separabilidade BH vs WH
fig, axes = plt.subplots(1, 4, figsize=(20, 5))
fig.suptitle('Features Derivadas por Classe — Separabilidade BH↔WH', 
             fontsize=13, fontweight='bold')

for ax, feat in zip(axes, ENGINEERED_FEATURES):
    sns.boxplot(
        data=df_eng, x='label', y=feat,
        order=ordem_classes,
        palette=PALETTE,
        ax=ax,
        showfliers=False
    )
    ax.set_title(feat, fontsize=10, fontweight='bold')
    ax.set_xlabel('')
    ax.set_xticklabels([c.replace(' ', '\n') for c in ordem_classes], fontsize=7)

plt.tight_layout()
plt.show()


# In[27]:


# Scatterplot das features derivadas: tx_efficiency × loss_ratio, apenas BH vs WH
bh_wh_eng = df_eng[df_eng['label'].isin(['Blackhole Attack', 'Wormhole Attack'])].sample(
    n=min(10000, len(df_eng)), random_state=RANDOM_STATE
)

fig, axes = plt.subplots(1, 2, figsize=(12, 6))
fig.suptitle('Features Derivadas — Separabilidade BH↔WH vs Features Originais',
             fontsize=13, fontweight='bold')

# Antes: PacketDropRate × AverageHopCount (features originais)
for cls in ['Blackhole Attack', 'Wormhole Attack']:
    sub = bh_wh_eng[bh_wh_eng['label'] == cls]
    axes[0].scatter(sub['PacketDropRate'], sub['AverageHopCount'],
                    c=PALETTE[cls], label=cls, alpha=0.35, s=10)
axes[0].set_title('ANTES — Features Originais\nPacketDropRate × AverageHopCount', fontsize=10)
axes[0].set_xlabel('PacketDropRate')
axes[0].set_ylabel('AverageHopCount')
axes[0].legend(fontsize=8, markerscale=2)

# Depois: tx_efficiency × loss_ratio (features derivadas)
for cls in ['Blackhole Attack', 'Wormhole Attack']:
    sub = bh_wh_eng[bh_wh_eng['label'] == cls]
    axes[1].scatter(sub['tx_efficiency'], sub['loss_ratio'],
                    c=PALETTE[cls], label=cls, alpha=0.35, s=10)
axes[1].set_title('DEPOIS — Features Derivadas\ntx_efficiency × loss_ratio', fontsize=10)
axes[1].set_xlabel('tx_efficiency (RxBytes / TxBytes)')
axes[1].set_ylabel('loss_ratio (LostPackets / TxPackets)')
axes[1].legend(fontsize=8, markerscale=2)

plt.tight_layout()
plt.show()


# ## 11. Análise de Separabilidade via PCA — Antes e Depois do Feature Engineering

# In[28]:


# Preparar features para PCA
FEATURES_ORIGINAIS = [f for f in NUM_FEATURES]  # só numéricas
FEATURES_COM_ENG = FEATURES_ORIGINAIS + ENGINEERED_FEATURES

# Subamostrar para agilidade visual
df_pca = df_eng.sample(n=min(20000, len(df_eng)), random_state=RANDOM_STATE)
labels_pca = df_pca['label'].values

# Features de volume com skew extremo (>50) dominam os componentes principais
# mesmo após StandardScaler, porque outliers extremos (Flooding) puxam a variância.
# Solução: aplicar log1p nas features de volume antes do PCA.
# Isso é APENAS para visualização — o Pipeline de modelagem usa StandardScaler direto.
VOLUME_LOG = [
    'TxPackets', 'RxPackets', 'LostPackets', 'TxBytes', 'RxBytes',
    'TxPacketRate/s', 'RxPacketRate/s', 'TxByteRate/s', 'RxByteRate/s',
    'Throughput/Kbps'
]

def preparar_pca(df_in, features):
    X = df_in[features].copy().fillna(0)
    for col in VOLUME_LOG:
        if col in X.columns:
            X[col] = np.log1p(X[col])
    return StandardScaler().fit_transform(X)

# PCA — features originais (com log1p nas de volume)
X_orig = preparar_pca(df_pca, FEATURES_ORIGINAIS)
pca_orig = PCA(n_components=2, random_state=RANDOM_STATE)
X_pca_orig = pca_orig.fit_transform(X_orig)

# PCA — features + derivadas (com log1p nas de volume)
X_eng = preparar_pca(df_pca, FEATURES_COM_ENG)
pca_eng = PCA(n_components=2, random_state=RANDOM_STATE)
X_pca_eng = pca_eng.fit_transform(X_eng)

print('Log1p aplicado nas features de volume para visualização PCA.')
print(f'Variância explicada — originais: PC1={pca_orig.explained_variance_ratio_[0]:.1%}, PC2={pca_orig.explained_variance_ratio_[1]:.1%}, Total={sum(pca_orig.explained_variance_ratio_):.1%}')
print(f'Variância explicada — com eng:   PC1={pca_eng.explained_variance_ratio_[0]:.1%}, PC2={pca_eng.explained_variance_ratio_[1]:.1%}, Total={sum(pca_eng.explained_variance_ratio_):.1%}')


# In[29]:


fig, axes = plt.subplots(1, 2, figsize=(18, 7))
fig.suptitle('PCA 2D — Separabilidade das Classes\nAntes e Depois do Feature Engineering (log1p em features de volume)',
             fontsize=13, fontweight='bold')

for ax, X_pca, pca_obj, titulo in [
    (axes[0], X_pca_orig, pca_orig, 'ANTES — Features Originais'),
    (axes[1], X_pca_eng,  pca_eng,  'DEPOIS — Com Features Derivadas')
]:
    for cls in ordem_classes:
        mask = labels_pca == cls
        ax.scatter(
            X_pca[mask, 0], X_pca[mask, 1],
            c=PALETTE[cls], label=cls, alpha=0.35, s=10
        )
    # Limitar eixos ao percentil 1–99 para não deixar outliers extremos
    # esmagar o cluster principal num ponto
    p1_x, p99_x = np.percentile(X_pca[:, 0], [1, 99])
    p1_y, p99_y = np.percentile(X_pca[:, 1], [1, 99])
    margin_x = (p99_x - p1_x) * 0.15
    margin_y = (p99_y - p1_y) * 0.15
    ax.set_xlim(p1_x - margin_x, p99_x + margin_x)
    ax.set_ylim(p1_y - margin_y, p99_y + margin_y)

    var_total = sum(pca_obj.explained_variance_ratio_)
    ax.set_title(f'{titulo}\nVariância explicada: {var_total:.1%}', fontsize=11)
    ax.set_xlabel(f'PC1 ({pca_obj.explained_variance_ratio_[0]:.1%})')
    ax.set_ylabel(f'PC2 ({pca_obj.explained_variance_ratio_[1]:.1%})')
    ax.legend(fontsize=7, markerscale=3, loc='best')
    ax.text(0.02, 0.02, 'Eixos: p1–p99 (outliers extremos omitidos da visualização)',
            transform=ax.transAxes, fontsize=7, color='gray', va='bottom')

plt.tight_layout()
plt.show()


# In[30]:


# Zoom no par BH↔WH antes e depois
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle('PCA 2D — Zoom: Blackhole vs Wormhole\nImpacto do Feature Engineering (eixos p1–p99)',
             fontsize=13, fontweight='bold')

bh_wh_mask = np.isin(labels_pca, ['Blackhole Attack', 'Wormhole Attack'])

for ax, X_pca, titulo in [
    (axes[0], X_pca_orig, 'ANTES — Originais'),
    (axes[1], X_pca_eng,  'DEPOIS — Com Derivadas')
]:
    X_sub = X_pca[bh_wh_mask]
    for cls in ['Blackhole Attack', 'Wormhole Attack']:
        mask = (labels_pca == cls) & bh_wh_mask
        ax.scatter(
            X_pca[mask, 0], X_pca[mask, 1],
            c=PALETTE[cls], label=cls, alpha=0.45, s=14
        )
    # Limitar eixos ao p1-p99 do subconjunto BH+WH
    p1_x, p99_x = np.percentile(X_sub[:, 0], [1, 99])
    p1_y, p99_y = np.percentile(X_sub[:, 1], [1, 99])
    margin_x = (p99_x - p1_x) * 0.15
    margin_y = (p99_y - p1_y) * 0.15
    ax.set_xlim(p1_x - margin_x, p99_x + margin_x)
    ax.set_ylim(p1_y - margin_y, p99_y + margin_y)

    ax.set_title(titulo, fontsize=11)
    ax.set_xlabel('PC1')
    ax.set_ylabel('PC2')
    ax.legend(fontsize=9, markerscale=2)

plt.tight_layout()
plt.show()


# ## 12. Experimento de Separabilidade

# In[31]:


# Filtrar apenas BH e WH
df_bh_wh = df_eng[df_eng['label'].isin(['Blackhole Attack', 'Wormhole Attack'])].copy()
le = LabelEncoder()
y_bh_wh = le.fit_transform(df_bh_wh['label'])

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

def avaliar_separabilidade(X, y, label):
    pipe = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(max_iter=1000, random_state=RANDOM_STATE,
                                   class_weight='balanced'))
    ])
    scores = cross_val_score(pipe, X, y, cv=skf, scoring='f1_macro', n_jobs=-1)
    print(f'{label:40s} F1-macro = {scores.mean():.4f} ± {scores.std():.4f}')
    return scores

print('Experimento: LogisticRegression — Blackhole vs Wormhole (5-fold CV)')
print('=' * 70)

scores_orig = avaliar_separabilidade(
    df_bh_wh[FEATURES_ORIGINAIS].values, y_bh_wh,
    'Features Originais'
)

scores_eng = avaliar_separabilidade(
    df_bh_wh[FEATURES_COM_ENG].values, y_bh_wh,
    'Originais + Features Derivadas'
)

delta = scores_eng.mean() - scores_orig.mean()
sigma_combinado = np.sqrt(scores_orig.std()**2 + scores_eng.std()**2)
print(f'\nDelta: {delta:+.4f} (σ combinado: ±{sigma_combinado:.4f})')
if abs(delta) > sigma_combinado:
    print('Ganho SIGNIFICATIVO (delta > σ combinado)')
    print('As features derivadas melhoram a separabilidade linear do par BH/WH')
else:
    print('Ganho dentro do ruído estatístico para LogReg')
    print('Conclusão: manter as features derivadas: elas ajudarão RF e XGBoost na modelagem')


# ## 13. Feature Importance

# In[32]:


# Preparar dados completos
FEATURES_FINAIS = FEATURES_ORIGINAIS + ENGINEERED_FEATURES
# Adicionar Protocol codificado manualmente só para este experimento de análise
df_model = pd.get_dummies(df_eng[FEATURES_FINAIS + ['Protocol', 'label']],
                           columns=['Protocol'], drop_first=False)

feature_cols = [c for c in df_model.columns if c != 'label']
X_all = df_model[feature_cols].values
y_all = LabelEncoder().fit_transform(df_model['label'])

# RF simples para feature importance (não é o modelo final)
rf_eda = RandomForestClassifier(
    n_estimators=100,
    max_depth=15,
    class_weight='balanced',
    random_state=RANDOM_STATE,
    n_jobs=-1
)
rf_eda.fit(X_all, y_all)

importances = pd.Series(rf_eda.feature_importances_, index=feature_cols)
importances_sorted = importances.sort_values(ascending=False)

print('Top 20 features por importância:')
print(importances_sorted.head(20).round(4).to_string())


# In[33]:


top_n = 20
top_features = importances_sorted.head(top_n)

# Colorir features derivadas diferente
cores = ['#E91E63' if f in ENGINEERED_FEATURES else '#607D8B' for f in top_features.index]

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.barh(range(len(top_features)), top_features.values[::-1],
               color=cores[::-1], alpha=0.85, edgecolor='white')
ax.set_yticks(range(len(top_features)))
ax.set_yticklabels(top_features.index[::-1], fontsize=9)
ax.set_xlabel('Importância (Gini)', fontsize=10)
ax.set_title(f'Top {top_n} Feature Importances — Random Forest (análise EDA)\n'
             'Rosa = features derivadas | Cinza = features originais',
             fontsize=11, fontweight='bold')

# Legenda manual
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#E91E63', label='Features derivadas (novas)'),
    Patch(facecolor='#607D8B', label='Features originais')
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=9)

plt.tight_layout()
plt.show()


# In[34]:


# Verificar posição das features derivadas no ranking
print('Posição das features derivadas no ranking de importância:')
all_ranked = list(importances_sorted.index)
for feat in ENGINEERED_FEATURES:
    pos = all_ranked.index(feat) + 1
    imp = importances_sorted[feat]
    print(f'  {feat:30s} → posição {pos:3d} de {len(all_ranked)} | importância: {imp:.4f}')


# ---
# ## 14. Sumário Final da EDA
# 
# Consolidação de todos os achados e decisões para referência na fase de modelagem.

# In[35]:


print('=' * 65)
print('SUMÁRIO FINAL DA EDA — UAVIDS-2025')
print('=' * 65)

print(f"""
DATASET
  Registros:       {len(df):,}
  Classes:         5 (Normal + 4 tipos de ataque)
  Features brutas: 22 + 1 label
  Features finais: {len(FEATURES_COM_ENG)} numéricas (18 originais + 3 derivadas)
  Sem Protocol (constante), sem FlowID/SrcAddr/DstAddr

QUALIDADE
  Valores ausentes:    0
  Duplicatas:          8.205 (6.7%) — assinatura Sybil Attack, MANTIDAS
  PacketDropRate > 1:  81 registros (0.07%) → clip em 1.0 no Pipeline
  HopCount = 0:        ~38.501 (31.5%) → comportamento de ataque, MANTER

FEATURES REMOVIDAS
  FlowID    → identificador sequencial
  SrcAddr   → IPs de rede simulada, não generalizam
  DstAddr   → idem
  Protocol  → constante 100% UDP, variância zero

FEATURES DERIVADAS MANTIDAS (3 de 4 testadas)
  loss_ratio         = LostPackets / TxPackets
  tx_efficiency      = RxBytes / TxBytes
  throughput_per_hop = Throughput / (AverageHopCount + 1.0)
  [jitter_delay_product descartada: posição 22/23 no importance]

DESBALANCEAMENTO
  Flooding Attack: ~16% (minoritária, razão 1.33x)
  Solução: class_weight='balanced' em todos os modelos

PROBLEMA CRÍTICO IDENTIFICADO
  Blackhole vs Wormhole: sobreposição NÃO-LINEAR confirmada
  LogReg baseline no par: F1=0.82 (sem melhora com features derivadas)
  Features derivadas úteis para RF/XGBoost (pos. 4 e 9 no importance)

PRÓXIMOS PASSOS (notebook 02_modelagem.ipynb)
  1. Pipeline sklearn: 21 features (18 orig + 3 deriv) + clip PacketDropRate
  2. Comparativo 3 modelos no MLflow: LogReg vs RandomForest vs XGBoost
  3. CV 5-fold estratificada, F1-macro, media +/- desvio padrao
  4. Tuning do vencedor com RandomizedSearchCV
  5. Model Registry @production
""")
print('=' * 65)


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




