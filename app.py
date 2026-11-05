import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from pathlib import Path

# Configuração da página
st.set_page_config(
    page_title="Eficiência xG no Brasileirão",
    layout="wide",
)
# Pasta dos dados
DATA = Path(__file__).parent / "data"


# Lê os três arquivos gerados pelo build_dataset.py
# @st.cache_data guarda na memória para não reler a cada clique
@st.cache_data
def load_data():
    matches = pd.read_csv(DATA / "matches_xg.csv", parse_dates=["utc_date"])
    teams = pd.read_csv(DATA / "team_summary.csv")
    long = pd.read_csv(DATA / "team_games_long.csv", parse_dates=["utc_date"])
    return matches, teams, long


matches, teams, long = load_data()

# Título
st.title("Eficiência ou Ineficiência?")
st.markdown(
    "**Análise de Expected Goals (xG) no Brasileirão:** "
    "Quem aproveita as oportunidades que cria e quem as desperdiça?"
)

# Filtros da barra lateral
st.sidebar.header("Filtros")
anos_disp = sorted(matches["season_year"].dropna().astype(int).unique().tolist())
anos_label = ["Todas"] + [str(a) for a in anos_disp]
ano_sel = st.sidebar.selectbox("Temporada", anos_label, index=len(anos_label) - 1)

comps_disp = ["Todas"] + sorted(matches["competition_name"].dropna().unique().tolist())
comp_sel = st.sidebar.selectbox("Competição", comps_disp)

# Aplica os filtros nas três tabelas
matches_f = matches.copy()
teams_f = teams.copy()
long_f = long.copy()
if ano_sel != "Todas":
    matches_f = matches_f[matches_f["season_year"] == int(ano_sel)]
    teams_f = teams_f[teams_f["season_year"] == int(ano_sel)]
    long_f = long_f[long_f["season_year"] == int(ano_sel)]
if comp_sel != "Todas":
    matches_f = matches_f[matches_f["competition_name"] == comp_sel]
    teams_f = teams_f[teams_f["competition_name"] == comp_sel]
    long_f = long_f[long_f["competition_name"] == comp_sel]

# Interrompe o app se a combinação de filtros não tiver jogos
if len(matches_f) == 0:
    st.warning("Nenhum jogo encontrado com esses filtros.")
    st.stop()

# Mostra até quando vão os dados
ultimo_jogo = matches_f["utc_date"].max().strftime("%d/%m/%Y")
st.caption(f"{len(matches_f)} jogos analisados, até {ultimo_jogo}.")

# Abas
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Visão Geral",
    "⚡ Eficiência (Top)",
    "👥 Análise por Time",
    "🎯 Análise por Jogo",
    "🔬 Validação Estatística",
])

# Aba 1: panorama, explicação do xG e distribuição dos gols
with tab1:
    st.subheader("Panorama")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jogos analisados", f"{len(matches_f)}")
    c2.metric("Gols (total)", f"{int(matches_f['goals_home'].sum() + matches_f['goals_away'].sum())}")
    c3.metric("xG total", f"{(matches_f['xg_home'].sum() + matches_f['xg_away'].sum()):.1f}")
    pct_mandante = (matches_f["result"] == "H").mean() * 100
    c4.metric("% Vitória mandante", f"{pct_mandante:.1f}%")

    st.markdown("---")
    st.markdown("### O que é xG (Expected Goals)?")
    st.markdown(
        "**xG** mede a **qualidade** estatística de cada finalização (ângulo, distância, tipo de chute, defensores ao redor). "
        "A soma do xG de uma equipe numa partida representa quantos gols a equipe "
        "**deveria** ter marcado dada a qualidade média de chutes na história do futebol.\n\n"
        "- **Gols > xG** ao longo de vários jogos → time **Eficiente** (aproveita oportunidades, finalizadores acima da média).\n"
        "- **Gols < xG** ao longo de vários jogos → time **Ineficiente** (desperdiça oportunidades, finalização ruim).\n\n"
        "Essa qualidade pode ser **persistente** (jogador que finaliza muito bem) ou **variar** (forma momentânea). "
        "A aba de **Validação Estatística** testa essa persistência."
    )

    st.markdown("---")
    st.markdown("### Distribuição: Gols reais vs xG")
    col1, col2 = st.columns(2)
    with col1:
        gols_total = pd.concat([matches_f["goals_home"], matches_f["goals_away"]])
        xg_total = pd.concat([matches_f["xg_home"], matches_f["xg_away"]])
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=gols_total, name="Gols reais",
            opacity=0.65, nbinsx=8,
            marker_color="#3498db", marker_line=dict(width=1, color="#1f618d"),
        ))
        fig.add_trace(go.Histogram(
            x=xg_total, name="xG",
            opacity=0.65, nbinsx=20,
            marker_color="#e67e22", marker_line=dict(width=1, color="#a04000"),
        ))
        fig.update_layout(
            barmode="overlay",
            title="Distribuição de gols vs xG (por equipe/jogo)",
            xaxis_title="Quantidade", yaxis_title="Frequência", height=400,
        )
        st.plotly_chart(fig, width="stretch")
    with col2:
        agg = matches_f.copy()
        agg["total_goals"] = agg["goals_home"] + agg["goals_away"]
        agg["total_xg"] = agg["xg_home"] + agg["xg_away"]
        grp = agg.groupby("competition_name")[["total_goals", "total_xg"]].mean().reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=grp["competition_name"], y=grp["total_goals"],
            name="Gols/jogo (real)", marker_color="#3498db",
            text=grp["total_goals"].round(2), textposition="outside",
        ))
        fig.add_trace(go.Bar(
            x=grp["competition_name"], y=grp["total_xg"],
            name="xG/jogo (esperado)", marker_color="#e67e22",
            text=grp["total_xg"].round(2), textposition="outside",
        ))
        fig.update_layout(
            barmode="group",
            bargap=0.4,        # espaço entre grupos (Série A vs Série B)
            bargroupgap=0.15,  # espaço entre as barras do mesmo grupo
            title="Média de gols por jogo: real vs esperado",
            yaxis_title="Por jogo", height=400,
        )
        st.plotly_chart(fig, width="stretch")

# Aba 2: ranking e tabela de eficiência dos times
with tab2:
    st.subheader("Times Eficientes × Ineficientes")
    st.markdown(
        "**Métrica:** média por jogo de `Gols feitos − xG feito`. "
        "Um time **Eficiente** marca, jogo após jogo, mais do que o xG previa. "
        "Um time **Ineficiente** desperdiça as chances que cria."
    )
    st.caption(
        "Classificação por teste t one-sample (α = 0.10): "
        "verificamos se a diferença média (gols − xG) é estatisticamente diferente de zero. "
        "Times com poucos jogos ficam como 'Amostra pequena'."
    )

    df_plot = teams_f.copy().sort_values("off_diff_per_game", ascending=True)
    color_map = {
        "Eficiente": "#27ae60",
        "Ineficiente": "#c0392b",
        "Neutro": "#f1c40f",         # amarelo (semáforo)
        "Amostra pequena": "#7f8c8d",
    }
    fig = px.bar(
        df_plot,
        x="off_diff_per_game",
        y="team",
        color="classificacao",
        orientation="h",
        color_discrete_map=color_map,
        title="Eficiência ofensiva: Gols feitos − xG feito (média por jogo)",
        labels={
            "off_diff_per_game": "Diferença média por jogo (gols)",
            "team": "Time",
            "classificacao": "Classificação",
            "games": "Jogos",
            "goals_for": "Gols feitos",
            "xg_for": "xG feito",
            "pct_overperform": "% de jogos acima do xG",
            "p_value": "p-valor",
        },
        hover_data={"games": True, "goals_for": True, "xg_for": ":.2f",
                    "pct_overperform": ":.0%", "p_value": ":.3f",
                    "off_diff_per_game": False, "classificacao": False},
    )
    fig.update_layout(height=max(450, 25 * len(df_plot)), yaxis_title="")
    fig.update_yaxes(categoryorder="total ascending")  # maior diferença no topo
    fig.add_vline(x=0, line_dash="dot", line_color="black")
    st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown("### Tabela completa")
    cols = ["season_year", "competition_name", "team", "games",
            "goals_for", "xg_for", "off_diff_per_game",
            "pct_overperform", "p_value", "classificacao"]
    display = teams_f[cols].sort_values("off_diff_per_game", ascending=False).reset_index(drop=True)
    display.columns = ["Ano", "Liga", "Time", "Jogos", "Gols feitos", "Expectativa de gols feitos",
                       "Média da diferença por jogo", "% de jogos acima do esperado", "p-valor", "Classificação"]
    display["Ano"] = display["Ano"].astype(int)
    display["Jogos"] = display["Jogos"].astype(int)
    display["Gols feitos"] = display["Gols feitos"].astype(int)
    display["Expectativa de gols feitos"] = display["Expectativa de gols feitos"].round(2)
    display["Média da diferença por jogo"] = display["Média da diferença por jogo"].round(3)
    display["% de jogos acima do esperado"] = (display["% de jogos acima do esperado"] * 100).round(1).astype(str) + "%"
    display["p-valor"] = display["p-valor"].round(3)

    # Pinta a linha com a cor da classificação do time
    def color_row_by_class(row):
        cls = row["Classificação"]
        if cls == "Eficiente":
            bg = "background-color: rgba(39,174,96,0.20)"
        elif cls == "Ineficiente":
            bg = "background-color: rgba(192,57,43,0.20)"
        elif cls == "Neutro":
            bg = "background-color: rgba(241,196,15,0.20)"
        else:
            bg = "background-color: rgba(127,140,141,0.20)"
        return [bg] * len(row)

    styled = display.style.apply(color_row_by_class, axis=1).format(precision=3)
    st.dataframe(styled, width="stretch", hide_index=True)
    st.info(
        "🟢 **Eficiente:** diferença é estatisticamente significativa (p < 0.10) e positiva. "
        "Pode indicar que o time tem **finalizadores acima da média**.\n\n"
        "🔴 **Ineficiente:** diferença significativa e negativa. "
        "O time **cria, mas desperdiça** as chances.\n\n"
        "🟡 **Neutro:** diferença não é estatisticamente significativa, gols ≈ xG."
    )

# Aba 3: eficiência de um time ao longo dos jogos analisados
with tab3:
    st.subheader("Análise individual")
    times_disp = sorted(teams_f["team"].unique().tolist())
    time_sel = st.selectbox("Escolha um time:", times_disp)
    info = teams_f[teams_f["team"] == time_sel].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jogos", int(info["games"]))
    c2.metric("Gols feitos", int(info["goals_for"]),
              f"{info['goals_for'] - info['xg_for']:+.2f} vs xG")
    c3.metric("Eficiência (Diferença/jogo)", f"{info['off_diff_per_game']:+.2f}")
    c4.metric("Classificação", info["classificacao"])

    hist = long_f[long_f["team"] == time_sel].sort_values("utc_date").reset_index(drop=True)
    hist["rodada"] = range(1, len(hist) + 1)
    hist["diff_goals_xg"] = hist["goals_for"] - hist["xg_for"]
    hist["diff_acum"] = hist["diff_goals_xg"].cumsum()
    if len(hist) >= 3:
        hist["rolling_3"] = hist["diff_goals_xg"].rolling(3, min_periods=1).mean()

    st.markdown(f"### Eficiência do **{time_sel}** ao longo da temporada")
    fig = go.Figure()
    bar_colors = np.where(
        hist["diff_goals_xg"] > 0.1, "#27ae60",
        np.where(hist["diff_goals_xg"] < -0.1, "#c0392b", "#f1c40f"),
    )
    fig.add_trace(go.Bar(
        x=hist["rodada"], y=hist["diff_goals_xg"],
        name="Diferença por jogo (gols − xG)",
        marker_color=bar_colors,
    ))
    fig.add_trace(go.Scatter(
        x=hist["rodada"], y=hist["diff_acum"],
        mode="lines+markers", name="Diferença acumulada",
        line=dict(color="#2c3e50", width=3),
        yaxis="y2",
    ))
    if "rolling_3" in hist.columns:
        fig.add_trace(go.Scatter(
            x=hist["rodada"], y=hist["rolling_3"],
            mode="lines", name="Média móvel (3 jogos)",
            line=dict(color="#3498db", width=2, dash="dot"),
        ))
    fig.update_layout(
        title=f"{time_sel}: gols − xG por jogo e cumulativo",
        xaxis_title="Jogo (ordem cronológica)",
        yaxis=dict(title="Diferença por jogo"),
        yaxis2=dict(title="Diferença acumulada", overlaying="y", side="right"),
        height=450, hovermode="x unified",
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    st.plotly_chart(fig, width="stretch")

    st.markdown("### Detalhamento jogo a jogo")
    show = hist[["rodada", "venue", "goals_for", "goals_against",
                 "xg_for", "xg_against", "pts", "xpts", "diff_goals_xg"]].copy()
    show["xg_for"] = show["xg_for"].round(2)
    show["xg_against"] = show["xg_against"].round(2)
    show["xpts"] = show["xpts"].round(2)
    show["diff_goals_xg"] = show["diff_goals_xg"].round(2)
    show["venue"] = show["venue"].map({"home": "Casa", "away": "Fora"}).fillna(show["venue"])
    show.columns = ["Jogo", "Local", "Gols feitos", "Gols sofridos",
                    "Expectativa de gols feitos", "Expectativa de gols sofridos",
                    "Pontos", "Expectativa de pontos", "Diferença (Gols − Expectativa)"]

    # Pinta a linha conforme a diferença entre gols e expectativa
    def color_row_by_diff(row):
        v = row["Diferença (Gols − Expectativa)"]
        if v > 0.1:
            return ["background-color: rgba(39,174,96,0.20)"] * len(row)
        if v < -0.1:
            return ["background-color: rgba(192,57,43,0.20)"] * len(row)
        return ["background-color: rgba(241,196,15,0.20)"] * len(row)

    styled_show = show.style.apply(color_row_by_diff, axis=1).format(precision=2)
    st.dataframe(styled_show, width="stretch", hide_index=True)
    st.info(
        "🟢 **Verde:** o time marcou **mais** que a expectativa no jogo, indicando **eficiência positiva** naquela partida.\n\n"
        "🔴 **Vermelho:** o time marcou **menos** que a expectativa, ou seja, **desperdiçou as chances** que criou.\n\n"
        "🟡 **Amarelo:** **diferença pequena** entre gols e expectativa (entre −0.1 e +0.1): jogo dentro do esperado."
    )

# Aba 4: comparação entre mandante e visitante em cada jogo
with tab4:
    st.subheader("Jogo a jogo: Expectativa de gols do mandante vs do visitante")
    st.markdown("Cada bolinha = um jogo. Cor = resultado real. Tamanho = total de gols.")
    plot_df = matches_f.copy()
    plot_df["total_goals"] = plot_df["goals_home"] + plot_df["goals_away"]
    plot_df["tamanho"] = plot_df["total_goals"].clip(lower=0.5)  # 0x0 também aparece
    plot_df["resultado"] = plot_df["result"].map({
        "H": "Vitória Mandante", "D": "Empate", "A": "Vitória Visitante"
    })
    plot_df["label"] = (plot_df["home_team"] + " " + plot_df["goals_home"].astype(str)
                       + " x " + plot_df["goals_away"].astype(str) + " " + plot_df["away_team"])

    fig = px.scatter(
        plot_df, x="xg_home", y="xg_away",
        color="resultado", size="tamanho", size_max=20,
        hover_name="label",
        hover_data={"xg_home": ":.2f", "xg_away": ":.2f", "total_goals": True,
                    "resultado": False, "tamanho": False},
        color_discrete_map={
            "Vitória Mandante": "#27ae60", "Empate": "#f39c12", "Vitória Visitante": "#c0392b"
        },
        title="Expectativa de gols: Mandante × Visitante",
        labels={
            "xg_home": "Expectativa de gols do Mandante",
            "xg_away": "Expectativa de gols do Visitante",
            "total_goals": "Total de gols",
            "resultado": "Resultado",
        },
    )
    max_v = max(plot_df["xg_home"].max(), plot_df["xg_away"].max()) + 0.2
    fig.add_shape(type="line", x0=0, y0=0, x1=max_v, y1=max_v,
                  line=dict(color="gray", dash="dot"))
    fig.update_layout(height=550)
    st.plotly_chart(fig, width="stretch")

    st.info(
        "**Como ler o gráfico:**\n\n"
        "A **linha pontilhada na diagonal** representa o **equilíbrio**: jogos onde os dois times criaram a mesma quantidade de chances.\n\n"
        "• Bolinhas **abaixo da linha** → o **mandante** criou MAIS chances\n\n"
        "• Bolinhas **acima da linha** → o **visitante** criou MAIS chances\n\n"
        "• 🟢 Verde = Vitória do Mandante\n\n"
        "• 🔴 Vermelho = Vitória do Visitante\n\n"
        "• 🟡 Amarelo = Empate\n\n"
        "• **Tamanho da bolinha** = total de gols na partida"
    )

    st.markdown("---")
    st.markdown("### Vitórias com menos Expectativa de gols que o adversário (jogos 'pegados')")
    # Vitórias de quem criou bem menos chances que o adversário
    plot_df["xg_diff"] = plot_df["xg_home"] - plot_df["xg_away"]
    pega_mand = plot_df[(plot_df["result"] == "H") & (plot_df["xg_diff"] < -0.5)].nsmallest(5, "xg_diff")
    pega_vis = plot_df[(plot_df["result"] == "A") & (plot_df["xg_diff"] > 0.5)].nlargest(5, "xg_diff")
    pega = pd.concat([pega_mand, pega_vis])
    sh = pega[["label", "xg_home", "xg_away", "xg_diff"]].copy()
    for c in ["xg_home", "xg_away", "xg_diff"]:
        sh[c] = sh[c].round(2)
    sh.columns = ["Jogo", "Expectativa de gols do Mandante", "Expectativa de gols do Visitante", "Diferença"]
    st.dataframe(sh, width="stretch", hide_index=True)
    st.info(
        "**Como interpretar a coluna Diferença:**\n\n"
        "Calculada como: **Expectativa do Mandante − Expectativa do Visitante**.\n\n"
        "• **Valor negativo (−)** → o **mandante** apresentou menor expectativa de gols, "
        "mas obteve vitória atuando em casa.\n\n"
        "• **Valor positivo (+)** → o **visitante** apresentou menor expectativa de gols, "
        "mas obteve vitória atuando fora.\n\n"
        "Quanto maior o valor absoluto, mais significativa é a **inversão estatística** entre "
        "o desempenho esperado e o resultado obtido."
    )

# Aba 5: testes estatísticos e conclusões
with tab5:
    st.subheader("xG prevê gols? A eficiência persiste?")

    # Correlação e regressão entre xG e gols
    x = pd.concat([matches_f["xg_home"], matches_f["xg_away"]]).values
    y = pd.concat([matches_f["goals_home"], matches_f["goals_away"]]).values
    pearson_r, pearson_p = stats.pearsonr(x, y)
    spearman_r, spearman_p = stats.spearmanr(x, y)
    c1, c2 = st.columns(2)
    c1.metric("Correlação linear (Pearson)", f"{pearson_r:.3f}", f"p-valor: {pearson_p:.2e}")
    c2.metric("Correlação por postos (Spearman)", f"{spearman_r:.3f}", f"p-valor: {spearman_p:.2e}")

    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    st.markdown(f"**Regressão linear:** `Gols = {slope:.3f} × xG + {intercept:.3f}` (R² = {r_value**2:.3f})")
    st.markdown(
        f"A cada **1 unidade a mais** de xG, o modelo prevê em média **{slope:.2f} gol a mais**. "
        "Um coeficiente igual a 1 significaria que os gols acompanham o xG na mesma proporção."
    )

    fig = px.scatter(
        x=x, y=y,
        labels={"x": "xG", "y": "Gols reais"},
        title="Relação xG × Gols reais (por equipe/jogo)",
        trendline="ols", trendline_color_override="red", opacity=0.6,
    )
    fig.add_shape(type="line", x0=0, y0=0, x1=max(x.max(), y.max()),
                  y1=max(x.max(), y.max()), line=dict(color="gray", dash="dot"))
    st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown("### A eficiência **persiste**? Teste split-half")
    st.markdown(
        "Se a eficiência for **habilidade real** (time tem finalizadores acima da média), "
        "ela deve persistir: o time que foi eficiente na **1ª metade** dos jogos analisados "
        "tende a continuar eficiente na **2ª metade**. "
        "\n\n"
        "Se for ruído estatístico, a correlação entre as duas metades é próxima de zero."
    )

    # Calcula a eficiência média de cada time na 1ª e na 2ª metade dos seus jogos
    def split_eff(jogos, times):
        rows = []
        for team in times:
            allg = jogos[jogos["team"] == team].sort_values("utc_date").reset_index(drop=True)
            n = len(allg)
            if n < 4:
                continue
            mid = n // 2
            e1 = (allg.iloc[:mid]["goals_for"] - allg.iloc[:mid]["xg_for"]).mean()
            e2 = (allg.iloc[mid:]["goals_for"] - allg.iloc[mid:]["xg_for"]).mean()
            rows.append({"team": team, "eff_1h": e1, "eff_2h": e2})
        return pd.DataFrame(rows)

    split_df = split_eff(long_f, teams_f["team"].unique())
    if len(split_df) >= 5:
        r_split, p_split = stats.pearsonr(split_df["eff_1h"], split_df["eff_2h"])
        st.metric("Correlação eficiência 1ª × 2ª metade", f"{r_split:.3f}",
                  f"p-valor: {p_split:.3f}")
        if abs(r_split) >= 0.4:
            st.success(
                f"**Correlação relevante ({r_split:.2f}):** a eficiência **persiste** entre as duas metades, "
                f"sugerindo que parte é habilidade real, e não apenas variância amostral."
            )
        elif abs(r_split) <= 0.2:
            st.info(
                f"**Correlação fraca ({r_split:.2f}):** pouca persistência. A eficiência observada pode ter "
                f"componente grande de variância amostral. Amostra ainda é pequena (poucas rodadas)."
            )
        else:
            st.warning(
                f"**Correlação intermediária ({r_split:.2f}):** evidência mista. "
                f"Vale revisitar com mais rodadas / mais temporadas."
            )
        fig = px.scatter(
            split_df, x="eff_1h", y="eff_2h", text="team",
            title="Eficiência 1ª metade × Eficiência 2ª metade",
            labels={
                "eff_1h": "Δ médio por jogo (1ª metade)",
                "eff_2h": "Δ médio por jogo (2ª metade)",
                "team": "Time",
            },
        )
        fig.update_traces(textposition="top center")
        fig.add_hline(y=0, line_dash="dot", line_color="gray")
        fig.add_vline(x=0, line_dash="dot", line_color="gray")
        st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown("### Conclusões principais")
    # Monta as conclusões a partir dos dados filtrados
    top_eff = teams_f[teams_f["classificacao"] == "Eficiente"].sort_values("off_diff_per_game", ascending=False)
    top_inef = teams_f[teams_f["classificacao"] == "Ineficiente"].sort_values("off_diff_per_game")
    bullets = [
        f"**xG ajuda a prever gols**: correlação de Pearson **{pearson_r:.2f}** "
        f"(p-valor = {pearson_p:.2e}), o que apoia o uso da métrica como estimador de qualidade de finalizações.",
    ]
    if len(top_eff) > 0:
        t = top_eff.iloc[0]
        bullets.append(
            f"**Mais eficiente** ({int(t['season_year'])}): **{t['team']}** "
            f"com média de **{t['off_diff_per_game']:.2f}** gols/jogo acima do xG, "
            f"p-valor = {t['p_value']:.3f}."
        )
    if len(top_inef) > 0:
        t = top_inef.iloc[0]
        bullets.append(
            f"**Mais ineficiente** ({int(t['season_year'])}): **{t['team']}** "
            f"com média de **{abs(t['off_diff_per_game']):.2f}** gols/jogo abaixo do xG, "
            f"p-valor = {t['p_value']:.3f}."
        )
    bullets.append(
        "**Importante:** alta eficiência não implica que o time vai necessariamente piorar nas próximas rodadas. "
        "O teste acima mostra o quanto essa eficiência persiste na amostra atual. "
        "Com parte de uma temporada, não dá para concluir sobre prazos maiores."
    )
    for b in bullets:
        st.markdown(f"- {b}")

    with st.expander("Metodologia"):
        st.markdown("""
**Fonte dos dados:** API de futebol coletando jogos finalizados das competições Brasileirão Série A e Série B.
O pipeline (`build_dataset.py`) suporta múltiplas temporadas: basta adicionar arquivos `matches_finished_2025.json`,
`xg_summaries_2025.json` e `match_stats_2025.json` na pasta `extracted/raw_json/` e rodar `python build_dataset.py`.

**Cálculo de xPoints (xPts):**
Para cada jogo, modelamos o número de gols de cada equipe como uma distribuição de Poisson independente
com média igual ao xG observado. Daí derivamos P(vit_mand), P(empate), P(vit_vis) e calculamos
xPts = 3·P(vit) + 1·P(empate).

**Classificação de Eficiência:**
Para cada time numa temporada, calculamos `Δ_jogo = gols_feitos − xG_feito` em cada partida.
Aplicamos um **teste t one-sample** (H₀: média(Δ) = 0) para decidir se a diferença média é
estatisticamente significativa (α = 0.10). Sinal positivo → **Eficiente**; negativo → **Ineficiente**;
não significativo → **Neutro**. Times com menos de 4 jogos: **Amostra pequena**.

**Persistência:** correlação Pearson entre a eficiência média da 1ª metade e da 2ª metade dos jogos analisados.
""")
