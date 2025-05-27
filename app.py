import pandas as pd
import geopandas as gpd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import json

# === CAMINHOS ===
caminho_previsao = "dados/previsao_diaria_com_ehf.xlsx"
caminho_limiares = "dados/limiares_climaticos_norte.xlsx"
caminho_geoses = "dados/geoses_norte.xlsx"
caminho_geojson = "dados/municipios_norte_simplificado.geojson"

# === LEITURA DOS DADOS ===
df_prev = pd.read_excel(caminho_previsao)
df_lim = pd.read_excel(caminho_limiares)
df_geo = pd.read_excel(caminho_geoses)

# Padroniza nomes dos municípios
df_prev = df_prev.rename(columns={"Municipio": "NM_MUN"})
df_lim = df_lim.rename(columns={"Municipio": "NM_MUN"})
df_geo = df_geo.rename(columns={"municipio": "NM_MUN"})

for d in [df_prev, df_lim, df_geo]:
    d["NM_MUN"] = d["NM_MUN"].str.upper().str.strip()

# Junta os dados
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

df["Situacao_Calor"] = df.apply(classificar_ehf, axis=1)
df["Classificacao_Umidade"] = df.apply(classificar_umidade, axis=1)
df["Classificacao_Precipitacao"] = df.apply(classificar_precip, axis=1)

# === SHAPEFILE (GEOJSON) ===
with open(caminho_geojson, "r", encoding="utf-8") as f:
    geojson = json.load(f)

gdf = gpd.read_file(caminho_geojson)
gdf["NM_MUN"] = gdf["NM_MUN"].str.upper().str.strip()

# === DASH APP ===
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # Para o Render reconhecer

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
                ],
                value="Temp_Max",
                clearable=False
            )
        ], md=6),
        dbc.Col([
            dcc.Dropdown(
                id="data",
                options=[{"label": str(d), "value": str(d)} for d in sorted(df["Data"].astype(str).unique())],
                value=str(sorted(df["Data"].astype(str).unique())[0]),
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
    gdf_merged = gdf.merge(dados_dia, on="NM_MUN", how="left")

    fig = px.choropleth_mapbox(
        gdf_merged,
        geojson=geojson,
        locations="NM_MUN",
        featureidkey="properties.NM_MUN",
        color=variavel,
        hover_name="NM_MUN",
        mapbox_style="carto-positron",
        center={"lat": -3.8, "lon": -52.4},
        zoom=4.5,
        opacity=0.75,
        category_orders={
            "Situacao_Calor": ["Normal", "Calor Severo", "Calor Extremo"],
            "Classificacao_Umidade": ["Normal", "Umidade Alta Severa", "Umidade Alta Extrema"],
            "Classificacao_Precipitacao": ["Normal", "Chuva Alta Severa", "Chuva Extrema"]
        },
        color_discrete_map={
            "Normal": "green", "Calor Severo": "yellow", "Calor Extremo": "red",
            "Umidade Alta Severa": "yellow", "Umidade Alta Extrema": "red",
            "Chuva Alta Severa": "yellow", "Chuva Extrema": "red"
        } if "Classificacao" in variavel or "Situacao" in variavel else None,
        color_continuous_scale="RdBu_r" if "Min" in variavel else "Reds"
    )

    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
















