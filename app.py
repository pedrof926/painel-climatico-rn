import pandas as pd
import geopandas as gpd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import json

# Caminhos dos arquivos
df_prev = pd.read_excel("dados/previsao_diaria_com_ehf.xlsx")
df_lim = pd.read_excel("dados/limiares_climaticos_norte.xlsx")
df_geo = pd.read_excel("dados/geoses_norte.xlsx")
gdf = gpd.read_file("dados/municipios_norte_simplificado.geojson")

# Padronizar nomes de municípios
df_prev["NM_MUN"] = df_prev["NM_MUN"].str.upper().str.strip()
df_lim["NM_MUN"] = df_lim["NM_MUN"].str.upper().str.strip()
df_geo["NM_MUN"] = df_geo["NM_MUN"].str.upper().str.strip()
gdf["NM_MUN"] = gdf["NM_MUN"].str.upper().str.strip()

# Juntar os dados
df = df_prev.merge(df_lim.drop(columns=["UF"]), on="NM_MUN", how="left")
df = df.merge(df_geo, on="NM_MUN", how="left")

# Classificações
def classificar_ehf(row):
    if pd.isna(row["EHF"]) or pd.isna(row["EHF_p85"]) or pd.isna(row["EHF_p95"]):
        return None
    if row["EHF"] < row["EHF_p85"]:
        return "Normal"
    elif row["EHF"] < row["EHF_p95"]:
        return "Calor Severo"
    else:
        return "Calor Extremo"

def classificar_umidade(row):
    if pd.isna(row["Umid_max_p85"]) or pd.isna(row["Umid_max_p95"]):
        return None
    if row["Umid_Max"] >= row["Umid_max_p85"] and row["Umid_Max"] < row["Umid_max_p95"]:
        return "Umidade Alta Severa"
    elif row["Umid_Max"] >= row["Umid_max_p95"]:
        return "Umidade Alta Extrema"
    return "Normal"

def classificar_precip(row):
    if pd.isna(row["Prec_p80"]) or pd.isna(row["Prec_p95"]):
        return None
    if row["Prec_Acumulada"] >= row["Prec_p80"] and row["Prec_Acumulada"] < row["Prec_p95"]:
        return "Chuva Alta Severa"
    elif row["Prec_Acumulada"] >= row["Prec_p95"]:
        return "Chuva Extrema"
    return "Normal"

def risco_combinado(row):
    if row["Situacao_Calor"] in ["Calor Severo", "Calor Extremo"] and row["Classificacao_Precipitacao"] in ["Chuva Alta Severa", "Chuva Extrema"]:
        return "Calor e Chuva"
    if row["Situacao_Calor"] in ["Calor Severo", "Calor Extremo"]:
        return "Apenas Calor"
    if row["Classificacao_Precipitacao"] in ["Chuva Alta Severa", "Chuva Extrema"]:
        return "Apenas Chuva"
    return "Sem Risco"

# Aplicar classificações
df["Situacao_Calor"] = df.apply(classificar_ehf, axis=1)
df["Classificacao_Umidade"] = df.apply(classificar_umidade, axis=1)
df["Classificacao_Precipitacao"] = df.apply(classificar_precip, axis=1)
df["Risco_Combinado"] = df.apply(risco_combinado, axis=1)

# GeoJSON simplificado
with open("dados/municipios_norte_simplificado.geojson", "r", encoding="utf-8") as f:
    geojson = json.load(f)

# Aplicativo Dash
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    html.H2("Painel de Previsão Climática - Região Norte", className="text-center my-4"),
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id="variavel",
                options=[
                    {"label": "Temperatura Máxima", "value": "Temp_Max"},
                    {"label": "Temperatura Mínima", "value": "Temp_Min"},
                    {"label": "Temperatura Média", "value": "Temp_Media"},
                    {"label": "Umidade Máxima", "value": "Umid_Max"},
                    {"label": "Umidade Mínima", "value": "Umid_Min"},
                    {"label": "Precipitação", "value": "Prec_Acumulada"},
                    {"label": "Situação de Calor Excessivo", "value": "Situacao_Calor"},
                    {"label": "Classificação da Umidade", "value": "Classificacao_Umidade"},
                    {"label": "Classificação da Precipitação", "value": "Classificacao_Precipitacao"},
                    {"label": "Risco Combinado", "value": "Risco_Combinado"},
                    {"label": "GeoSES", "value": "geoses"}
                ],
                value="Temp_Max",
                clearable=False
            )
        ], md=6),
        dbc.Col([
            dcc.Dropdown(
                id="data",
                options=[{"label": str(d), "value": str(d)} for d in sorted(df["Data"].astype(str).unique())],
                value=str(sorted(df["Data"].unique())[0]),
                clearable=False
            )
        ], md=6)
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
    gdf_merged = gdf.merge(dados_dia, on="NM_MUN", how="left")

    if variavel in ["Situacao_Calor", "Classificacao_Umidade", "Classificacao_Precipitacao", "Risco_Combinado"]:
        cor_mapas = {
            "Situacao_Calor": {"Normal": "green", "Calor Severo": "yellow", "Calor Extremo": "red"},
            "Classificacao_Umidade": {"Normal": "green", "Umidade Alta Severa": "yellow", "Umidade Alta Extrema": "red"},
            "Classificacao_Precipitacao": {"Normal": "green", "Chuva Alta Severa": "yellow", "Chuva Extrema": "red"},
            "Risco_Combinado": {"Sem Risco": "green", "Apenas Calor": "orange", "Apenas Chuva": "blue", "Calor e Chuva": "red"}
        }
        fig = px.choropleth_mapbox(
            gdf_merged,
            geojson=geojson,
            locations="NM_MUN",
            color=variavel,
            hover_name="NM_MUN",
            mapbox_style="carto-positron",
            center={"lat": -3.8, "lon": -52.4},
            zoom=4.5,
            opacity=0.75,
            color_discrete_map=cor_mapas[variavel]
        )
    else:
        cor_especial = {
            "Temp_Max": "Reds",
            "Temp_Min": "Blues",
            "Temp_Media": "Oranges",
            "Umid_Min": "Reds_r",
            "Umid_Max": "Blues",
            "Prec_Acumulada": "Viridis",
            "geoses": "cividis"
        }
        fig = px.choropleth_mapbox(
            gdf_merged,
            geojson=geojson,
            locations="NM_MUN",
            color=variavel,
            hover_name="NM_MUN",
            mapbox_style="carto-positron",
            center={"lat": -3.8, "lon": -52.4},
            zoom=4.5,
            opacity=0.75,
            color_continuous_scale=cor_especial.get(variavel, "Viridis")
        )

    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig


















