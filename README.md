# ⚽ Eficiência ou Ineficiência? — Análise de Expectativa de Gols no Brasileirão

> **Trabalho CP3 — Data Science e Statistical Computing · FIAP**
> Análise estatística que identifica quais times do Brasileirão **aproveitam** as oportunidades que criam e quais **desperdiçam**, usando **Expectativa de Gols (xG)** como referência objetiva.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-5.18+-3F4F75?logo=plotly&logoColor=white)

---

## 🚀 Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

O app abre em [http://localhost:8501](http://localhost:8501).

> No Windows, se `python` der erro de Microsoft Store, use `py` no lugar.

---

## 📊 O que o app mostra

| Aba | Conteúdo |
|-----|----------|
| **Visão Geral** | KPIs do campeonato, distribuição de gols vs expectativa |
| **Eficiência (Top)** | Ranking de times Eficientes 🟢, Ineficientes 🔴 e Neutros 🟡 |
| **Análise por Time** | Eficiência rodada a rodada, com média móvel e cumulativo |
| **Análise por Jogo** | Dispersão de expectativa mandante × visitante e jogos com inversão estatística |
| **Validação Estatística** | Correlações, regressão linear e teste de persistência |

---

## 📐 Metodologia

Para cada time, calculamos a diferença por jogo: `Δᵢ = gols_feitos − expectativa_de_gols`.

Aplicamos um **teste t one-sample** com `H₀: média(Δ) = 0`:

- p-valor < 0.10 e média(Δ) > 0 → 🟢 **Eficiente**
- p-valor < 0.10 e média(Δ) < 0 → 🔴 **Ineficiente**
- caso contrário → 🟡 **Neutro**

A validação estatística usa correlação linear (Pearson), correlação por postos (Spearman) e regressão linear para garantir que a Expectativa de Gols é um preditor válido dos gols reais.

---

## 🛠️ Stack

pandas · numpy · scipy.stats · statsmodels · plotly · streamlit

---

## 👥 Grupo

| Nome | RM |
|------|-----|
| Kauê de Almeida Pena | 564211 |
| Eduardo Delorenzo Moraes | 561749 |
| Lucas Rowlands Abat | 562994 |
| Ronaldo Aparecido Monteiro Almeida | 565017 |
| William Queiroz | 565032 |
