import pandas as pd
import geopandas as gpd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc

# === CAMINHOS ===
caminho_previsao = "dados/previsao_diaria_com_ehf.xlsx"
caminho_limiares = "dados/limiares_climaticos_norte.xlsx"
caminho_geoses = "dados/geoses_norte.xlsx"
caminho_shape = "dados/municipios_norte_simplificado.geojson"  # ou shapefile original se preferir

# === LEITURA DOS DADOS ===
df_prev = pd.read_excel(caminho_previsao)
df_lim = pd.read_excel(caminho_limiares)
df_geo = pd.read_excel(caminho_geoses)

# Padronização
for df in [df_prev, df_lim, df_geo]:
    df.rename(columns={df.columns[0]: "NM_MUN"}, inplace=True)
    df["NM_MUN"] = df["NM_MUN"].str.upper().str.strip()

# Merge
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

# === SHAPE ===
gdf = gpd.read_file(caminho_shape)
gdf["NM_MUN"] = gdf["NM_MUN"].str.upper().str.strip()

# === DASH APP ===
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # isso aqui é essencial para o Render

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
    gdf_merged = gdf.merge(dados_dia, on="NM_MUN", how="left")

    if variavel in ["Situacao_Calor", "Classificacao_Umidade", "Classificacao_Precipitacao"]:
        cor_map = {
            "Situacao_Calor": {"Normal": "green", "Calor Severo": "yellow", "Calor Extremo": "red"},
            "Classificacao_Umidade": {"Normal": "green", "Umidade Alta Severa": "yellow", "Umidade Alta Extrema": "red"},
            "Classificacao_Precipitacao": {"Normal": "green", "Chuva Alta Severa": "yellow", "Chuva Extrema": "red"},
        }
        fig = px.choropleth_mapbox(
            gdf_merged,
            geojson=gdf_merged.geometry,
            locations=gdf_merged.index,
            color=variavel,
            hover_name="NM_MUN",
            mapbox_style="carto-positron",
            center={"lat": -3.8, "lon": -52.4},
            zoom=4.5,
            opacity=0.8,
            color_discrete_map=cor_map[variavel]
        )
    else:
        fig = px.choropleth_mapbox(
            gdf_merged,
            geojson=gdf_merged.geometry,
            locations=gdf_merged.index,
            color=variavel,
            hover_name="NM_MUN",
            mapbox_style="carto-positron",
            center={"lat": -3.8, "lon": -52.4},
            zoom=4.5,
            opacity=0.8,
            color_continuous_scale="Viridis"
        )

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)















