import pandas as pd
import geopandas as gpd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc

# ========== LER DADOS BASE ==========
df = pd.read_excel("dados/previsao_diaria_com_ehf.xlsx")
df_lim = pd.read_excel("dados/limiares_climaticos_norte.xlsx")
df_geo = pd.read_excel("dados/geoses_norte.xlsx")
gdf_mapa = gpd.read_file("dados/Municipios_Regiao_Norte_2024.shp")

# ========== AJUSTES ==========
df["Data"] = pd.to_datetime(df["Data"]).dt.date
df["Municipio"] = df["Municipio"].str.strip().str.upper()
df_lim["Municipio"] = df_lim["Municipio"].str.strip().str.upper()
df_geo["municipio"] = df_geo["municipio"].str.strip().str.upper()
gdf_mapa["NM_MUN"] = gdf_mapa["NM_MUN"].str.strip().str.upper()

# ========== MERGE GERAL ==========
df = df.merge(df_lim, on="Municipio", how="left")
df = df.merge(df_geo, left_on="Municipio", right_on="municipio", how="left")

# ========== CLASSIFICAÇÕES ==========
def classificar_ehf(row):
    if pd.isna(row["EHF"]) or pd.isna(row["ehf_p85"]) or pd.isna(row["ehf_p95"]):
        return None
    if row["EHF"] < row["ehf_p85"]:
        return "Normal"
    elif row["EHF"] < row["ehf_p95"]:
        return "Calor Severo"
    else:
        return "Calor Extremo"

def classificar_umidade(row):
    if pd.isna(row["urmax_p80"]) or pd.isna(row["urmax_p95"]):
        return None
    if row["Umax"] >= row["urmax_p80"] and row["Umax"] < row["urmax_p95"]:
        return "Umidade Alta Severa"
    elif row["Umax"] >= row["urmax_p95"]:
        return "Umidade Alta Extrema"
    return "Normal"

def classificar_precipitacao(row):
    if pd.isna(row["precip_p80"]) or pd.isna(row["precip_p95"]):
        return None
    if row["Precipitacao"] >= row["precip_p80"] and row["Precipitacao"] < row["precip_p95"]:
        return "Chuva Alta Severa"
    elif row["Precipitacao"] >= row["precip_p95"]:
        return "Chuva Extrema"
    return "Normal"

df["Situacao_Calor"] = df.apply(classificar_ehf, axis=1)
df["Classificacao_Umidade"] = df.apply(classificar_umidade, axis=1)
df["Classificacao_Precipitacao"] = df.apply(classificar_precipitacao, axis=1)

# ========== DASH APP ==========
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H2("Painel de Previsão Climática - Região Norte", className="text-center my-4"),

    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id="variavel",
                options=[
                    {"label": "Temperatura Máxima (Tmax)", "value": "Tmax"},
                    {"label": "Temperatura Mínima (Tmin)", "value": "Tmin"},
                    {"label": "Temperatura Média (Tmed)", "value": "Tmed"},
                    {"label": "Umidade Máxima (Umax)", "value": "Umax"},
                    {"label": "Umidade Mínima (Umin)", "value": "Umin"},
                    {"label": "Precipitação (mm)", "value": "Precipitacao"},
                    {"label": "Situação de Calor Excessivo", "value": "Situacao_Calor"},
                    {"label": "Classificação da Umidade", "value": "Classificacao_Umidade"},
                    {"label": "Classificação da Precipitação", "value": "Classificacao_Precipitacao"},
                ],
                value="Tmax",
                clearable=False
            )
        ], md=6),

        dbc.Col([
            dcc.Dropdown(
                id="data",
                options=[{"label": str(d), "value": str(d)} for d in sorted(df["Data"].unique())],
                value=str(sorted(df["Data"].unique())[0]),
                clearable=False
            )
        ], md=6),
    ]),

    dcc.Graph(id="mapa_previsao", style={"height": "80vh"})
], fluid=True)

@app.callback(
    Output("mapa_previsao", "figure"),
    Input("variavel", "value"),
    Input("data", "value")
)
def atualizar_mapa(variavel, data):
    dados_dia = df[df["Data"].astype(str) == data]
    gdf = gdf_mapa.merge(dados_dia, left_on="NM_MUN", right_on="Municipio", how="left")

    if variavel == "Situacao_Calor":
        cor_map = {"Normal": "green", "Calor Severo": "yellow", "Calor Extremo": "red"}
        ordem = ["Normal", "Calor Severo", "Calor Extremo"]
    elif variavel == "Classificacao_Umidade":
        cor_map = {"Normal": "green", "Umidade Alta Severa": "yellow", "Umidade Alta Extrema": "red"}
        ordem = ["Normal", "Umidade Alta Severa", "Umidade Alta Extrema"]
    elif variavel == "Classificacao_Precipitacao":
        cor_map = {"Normal": "green", "Chuva Alta Severa": "yellow", "Chuva Extrema": "red"}
        ordem = ["Normal", "Chuva Alta Severa", "Chuva Extrema"]
    else:
        cor_map = None
        ordem = None

    fig = px.choropleth_mapbox(
        gdf,
        geojson=gdf.geometry,
        locations=gdf.index,
        color=variavel,
        hover_name="NM_MUN",
        mapbox_style="carto-positron",
        center={"lat": -3.8, "lon": -60},
        zoom=4.5,
        opacity=0.75,
        color_discrete_map=cor_map if cor_map else None,
        category_orders={variavel: ordem} if ordem else None,
        color_continuous_scale="RdBu_r" if "Umin" in variavel else "Reds" if "Tmax" in variavel else "Blues" if "Tmin" in variavel else "Viridis"
    )

    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig

server = app.server

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)

