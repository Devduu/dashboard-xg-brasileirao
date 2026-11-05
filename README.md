# ⚽ Eficiência ou Ineficiência? Análise de Expectativa de Gols no Brasileirão

> **Projeto da disciplina de Data Science e Statistical Computing · FIAP**
> Análise estatística que identifica quais times do Brasileirão **aproveitam** as oportunidades que criam e quais **desperdiçam**, usando **Expectativa de Gols (xG)** como referência objetiva.

**Aplicação publicada:** https://dashboard-xg-brasileirao.streamlit.app/

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.66.1-FF4B4B?logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-3.1.1-150458?logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-7.1.0-3F4F75?logo=plotly&logoColor=white)

---

## 🚀 Como rodar

```bash
git clone https://github.com/Devduu/dashboard-xg-brasileirao.git
cd dashboard-xg-brasileirao
pip install -r requirements.txt
streamlit run app.py
```

O app abre em [http://localhost:8501](http://localhost:8501).

---

## 📊 O que o app mostra

| Aba | Conteúdo |
|-----|----------|
| **Visão Geral** | KPIs do campeonato, distribuição de gols vs expectativa |
| **Eficiência (Top)** | Ranking de times Eficientes 🟢, Ineficientes 🔴 e Neutros 🟡 |
| **Análise por Time** | Eficiência jogo a jogo, com média móvel e cumulativo |
| **Análise por Jogo** | Dispersão de expectativa mandante × visitante e jogos com inversão estatística |
| **Validação Estatística** | Correlações, regressão linear e teste de persistência |

---

## 📐 Metodologia

Para cada time, calculamos a diferença por jogo: `Δᵢ = gols_feitos − expectativa_de_gols`.

Aplicamos um **teste t one-sample** com `H₀: média(Δ) = 0`:

- menos de 4 jogos → ⚪ **Amostra pequena**
- p-valor < 0.10 e média(Δ) > 0 → 🟢 **Eficiente**
- p-valor < 0.10 e média(Δ) < 0 → 🔴 **Ineficiente**
- caso contrário → 🟡 **Neutro**

A validação estatística usa correlação linear (Pearson), correlação por postos (Spearman) e regressão linear para verificar se a Expectativa de Gols ajuda a prever os gols reais.

---

## 🛠️ Stack

pandas · numpy · scipy.stats · statsmodels · plotly · streamlit
