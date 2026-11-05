# Monta os arquivos da pasta data a partir dos JSON brutos da API
# Para rodar: python build_dataset.py

import json
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import poisson, ttest_1samp

# Pastas dos dados brutos e dos arquivos gerados
BASE = Path(__file__).parent
RAW = BASE / "extracted" / "raw_json"
OUT = BASE / "data"
OUT.mkdir(exist_ok=True)


# Junta os arquivos de uma base, como matches_finished.json e matches_finished_2025.json
def load_json_glob(stem: str):
    files = []
    base = RAW / f"{stem}.json"
    if base.exists():
        files.append(base)
    for p in sorted(RAW.glob(f"{stem}_*.json")):
        suffix = p.stem.replace(stem + "_", "")
        if suffix.isdigit() and len(suffix) == 4:
            files.append(p)

    if not files:
        raise FileNotFoundError(f"Nenhum arquivo {stem}.json em {RAW}")

    combined = []
    combined_dict = {}
    is_list = None
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, dict) and "data" in obj:
            obj = obj["data"]
        if is_list is None:
            is_list = isinstance(obj, list)
        if isinstance(obj, list):
            combined.extend(obj)
        elif isinstance(obj, dict):
            combined_dict.update(obj)
    return combined if is_list else combined_dict


# Lê os jogos finalizados e padroniza os nomes das colunas
matches = load_json_glob("matches_finished")
df_matches = pd.json_normalize(matches)

df_matches = df_matches.rename(columns={
    "id": "match_id",
    "home_team.name": "home_team",
    "away_team.name": "away_team",
    "home_team.id": "home_team_id",
    "away_team.id": "away_team_id",
    "score.home": "goals_home",
    "score.away": "goals_away",
    "_competition_name": "competition_name",
})

df_matches["utc_date"] = pd.to_datetime(df_matches["utc_date"], errors="coerce", utc=True)
df_matches["season_year"] = df_matches["utc_date"].dt.year.astype("Int64")

# Lê o resumo de xG de cada jogo
xg = load_json_glob("xg_summaries")
df_xg = pd.DataFrame(xg)

# Lê as estatísticas de cada jogo: xG, posse, chutes e grandes chances
stats = load_json_glob("match_stats")
rows = []
for s in stats:
    d = s.get("data", s) if isinstance(s, dict) else {}
    mid = d.get("match_id")
    ov = d.get("overview", {})
    # Pega os valores de mandante e visitante de uma estatística
    def get_home_away(key, sub="all"):
        node = ov.get(key, {}).get(sub, {})
        return node.get("home"), node.get("away")
    xgh, xga = get_home_away("expected_goals")
    posh, posa = get_home_away("ball_possession")
    sh_h, sh_a = get_home_away("total_shots")
    sot_h, sot_a = get_home_away("shots_on_target")
    bc_h, bc_a = get_home_away("big_chances")
    rows.append({
        "match_id": mid,
        "xg_home": xgh,
        "xg_away": xga,
        "possession_home": posh,
        "possession_away": posa,
        "shots_home": sh_h,
        "shots_away": sh_a,
        "shots_on_target_home": sot_h,
        "shots_on_target_away": sot_a,
        "big_chances_home": bc_h,
        "big_chances_away": bc_a,
    })
df_stats = pd.DataFrame(rows)

# Junta tudo e mantém só os jogos com xG dos dois times
df = df_matches.merge(df_xg, on="match_id", how="left")
df = df.merge(df_stats, on="match_id", how="left")
df = df[df["xg_home"].notna() & df["xg_away"].notna()].copy()


# Calcula os pontos esperados de um jogo, com os gols em distribuição de Poisson
def xpoints_from_xg(xh, xa, max_goals=10):
    h = np.array([poisson.pmf(k, xh) for k in range(max_goals + 1)])
    a = np.array([poisson.pmf(k, xa) for k in range(max_goals + 1)])
    mat = np.outer(h, a)
    p_home = np.tril(mat, -1).sum()
    p_away = np.triu(mat, 1).sum()
    p_draw = np.trace(mat)
    return 3 * p_home + p_draw, 3 * p_away + p_draw, p_home, p_draw, p_away


# Aplica o cálculo de pontos esperados em todos os jogos
xp = []
for _, r in df.iterrows():
    xh, xa = float(r["xg_home"]), float(r["xg_away"])
    xp.append(xpoints_from_xg(xh, xa))
df[["xpts_home", "xpts_away", "p_home", "p_draw", "p_away"]] = pd.DataFrame(xp, index=df.index)


# Devolve os pontos reais de mandante e visitante
def real_points(gh, ga):
    if gh > ga: return 3, 0
    if gh < ga: return 0, 3
    return 1, 1


# Pontos, resultado e diferença entre o real e o esperado
df[["pts_home", "pts_away"]] = df.apply(
    lambda r: pd.Series(real_points(r["goals_home"], r["goals_away"])), axis=1
)
df["result"] = np.where(df["goals_home"] > df["goals_away"], "H",
                np.where(df["goals_home"] < df["goals_away"], "A", "D"))

df["goal_diff_home"] = df["goals_home"] - df["xg_home"]
df["goal_diff_away"] = df["goals_away"] - df["xg_away"]
df["pts_diff_home"] = df["pts_home"] - df["xpts_home"]
df["pts_diff_away"] = df["pts_away"] - df["xpts_away"]

# Salva a tabela de jogos
df.to_csv(OUT / "matches_xg.csv", index=False)
print(f"matches_xg.csv salvo com {len(df)} jogos | temporadas: {sorted(df['season_year'].dropna().unique().tolist())}")

# Monta a tabela com uma linha por time em cada jogo
home = df[[
    "season_year", "competition_name", "home_team", "home_team_id",
    "goals_home", "goals_away", "xg_home", "xg_away",
    "pts_home", "xpts_home", "utc_date",
]].rename(columns={
    "home_team": "team", "home_team_id": "team_id",
    "goals_home": "goals_for", "goals_away": "goals_against",
    "xg_home": "xg_for", "xg_away": "xg_against",
    "pts_home": "pts", "xpts_home": "xpts",
})
home["venue"] = "home"
away = df[[
    "season_year", "competition_name", "away_team", "away_team_id",
    "goals_away", "goals_home", "xg_away", "xg_home",
    "pts_away", "xpts_away", "utc_date",
]].rename(columns={
    "away_team": "team", "away_team_id": "team_id",
    "goals_away": "goals_for", "goals_home": "goals_against",
    "xg_away": "xg_for", "xg_home": "xg_against",
    "pts_away": "pts", "xpts_away": "xpts",
})
away["venue"] = "away"
long = pd.concat([home, away], ignore_index=True)

long.to_csv(OUT / "team_games_long.csv", index=False)


# Resume um time: totais, diferença média e teste t da diferença entre gols e xG
def agg_team(g):
    diffs = (g["goals_for"] - g["xg_for"]).values
    n = len(diffs)
    pct_over = float((diffs > 0).mean()) if n > 0 else np.nan
    if n >= 3 and np.std(diffs) > 1e-9:
        t_stat, p_val = ttest_1samp(diffs, 0.0)
    else:
        t_stat, p_val = np.nan, np.nan
    return pd.Series({
        "games": n,
        "goals_for": g["goals_for"].sum(),
        "xg_for": g["xg_for"].sum(),
        "goals_against": g["goals_against"].sum(),
        "xg_against": g["xg_against"].sum(),
        "pts": g["pts"].sum(),
        "xpts": g["xpts"].sum(),
        "off_diff": float(diffs.sum()),
        "off_diff_per_game": float(diffs.mean()),
        "pct_overperform": pct_over,
        "t_stat": float(t_stat) if pd.notna(t_stat) else np.nan,
        "p_value": float(p_val) if pd.notna(p_val) else np.nan,
    })


# Calcula o resumo de cada time em cada temporada
team_summary = (
    long.groupby(["season_year", "competition_name", "team", "team_id"], dropna=False)
        .apply(agg_team, include_groups=False)
        .reset_index()
)


# Classifica o time pelo p-valor e pelo sinal da diferença média
def classify(row, alpha=0.10):
    if pd.isna(row["p_value"]) or row["games"] < 4:
        return "Amostra pequena"
    if row["p_value"] < alpha:
        return "Eficiente" if row["off_diff_per_game"] > 0 else "Ineficiente"
    return "Neutro"


team_summary["classificacao"] = team_summary.apply(classify, axis=1)

# Calcula as médias por jogo
for c in ["xg_for", "xg_against", "goals_for", "goals_against", "pts", "xpts"]:
    team_summary[f"{c}_per_game"] = (team_summary[c] / team_summary["games"]).round(3)

# Ordena e salva o resumo dos times
team_summary = team_summary.sort_values(["season_year", "off_diff_per_game"], ascending=[True, False])
team_summary.to_csv(OUT / "team_summary.csv", index=False)
print(f"team_summary.csv salvo com {len(team_summary)} linhas (temporada × time)")

# Mostra no terminal os times mais e menos eficientes
print("\n--- Top 5 EFICIENTES (média de gols feitos − xG feito por jogo) ---")
print(team_summary.sort_values("off_diff_per_game", ascending=False).head(5)[
    ["season_year", "competition_name", "team", "games", "goals_for", "xg_for",
     "off_diff_per_game", "p_value", "classificacao"]
].to_string(index=False))

print("\n--- Top 5 INEFICIENTES ---")
print(team_summary.sort_values("off_diff_per_game", ascending=True).head(5)[
    ["season_year", "competition_name", "team", "games", "goals_for", "xg_for",
     "off_diff_per_game", "p_value", "classificacao"]
].to_string(index=False))
