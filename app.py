import pandas as pd
import geopandas as gpd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc

# === Carregando os dados ===
df_prev = pd.read_excel("dados/previsao_diaria_com_ehf.xlsx")
df_limiares = pd.read_excel("dados/limiares_climaticos_norte.xlsx")
df_geoses = pd.read_excel("dados/geoses_norte.xlsx")
gdf = gpd.read_file("dados/Municipios_Regiao_Norte_2024.shp")

# Padronizando nomes
df_prev['Municipio'] = df_prev['Municipio'].str.upper().str.strip()
df_limiares['Municipio'] = df_limiares['Municipio'].str.upper().str.strip()
df_geoses['municipio'] = df_geoses['municipio'].str.upper().str.strip()
gdf['NM_MUN'] = gdf['NM_MUN'].str.upper().str.strip()

# Merge geral com limiares e GeoSES
df = df_prev.merge(df_limiares, on='Municipio', how='left')
df = df.merge(df_geoses, left_on='Municipio', right_on='municipio', how='left')

# Classificações com base nos limiares
def classificar_ehf(row):
    if pd.isna(row['EHF']):
        return 'Sem dado'
    elif row['EHF'] <= row['EHF_p85']:
        return 'Normal'
    elif row['EHF'] <= row['EHF_p95']:
        return 'Severo'
    else:
        return 'Extremo'

def classificar_umidade(row):
    if pd.isna(row['Umid_Min']) or pd.isna(row['Umid_Max']):
        return 'Sem dado'
    elif row['Umid_Max'] > row['Umid_max_p95']:
        return 'Alta extrema'
    elif row['Umid_Max'] > row['Umid_max_p85']:
        return 'Alta severa'
    else:
        return 'Normal'

def classificar_precipitacao(row):
    if pd.isna(row['Prec_Acumulada']):
        return 'Sem dado'
    elif row['Prec_Acumulada'] > row['Prec_p95']:
        return 'Alta extrema'
    elif row['Prec_Acumulada'] > row['Prec_p80']:
        return 'Alta severa'
    else:
        return 'Normal'

# Aplicando as classificações
df['Classificacao_EHF'] = df.apply(classificar_ehf, axis=1)
df['Classificacao_Umidade'] = df.apply(classificar_umidade, axis=1)
df['Classificacao_Precipitacao'] = df.apply(classificar_precipitacao, axis=1)

# Inicia o app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Painel Climático Norte"

# Layout
app.layout = dbc.Container([
    html.H1("Painel Climático da Região Norte", className="text-center my-4"),

    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='variavel',
                options=[
                    {'label': 'Calor Excessivo (EHF)', 'value': 'Classificacao_EHF'},
                    {'label': 'Umidade Relativa', 'value': 'Classificacao_Umidade'},
                    {'label': 'Precipitação', 'value': 'Classificacao_Precipitacao'}
                ],
                value='Classificacao_EHF',
                clearable=False
            )
        ], width=6),

        dbc.Col([
            dcc.DatePickerSingle(
                id='data',
                date=df['Data'].max(),
                min_date_allowed=df['Data'].min(),
                max_date_allowed=df['Data'].max(),
                display_format='DD/MM/YYYY'
            )
        ], width=6),
    ], className="mb-4"),

    dcc.Graph(id='mapa')
])

# Callback
@app.callback(
    Output('mapa', 'figure'),
    Input('variavel', 'value'),
    Input('data', 'date')
)
def atualizar_mapa(variavel, data):
    data = pd.to_datetime(data)
    df_filtro = df[df['Data'] == data]

    gdf_mapa = gdf.merge(df_filtro, left_on='NM_MUN', right_on='Municipio', how='left')

    fig = px.choropleth_mapbox(
        gdf_mapa,
        geojson=gdf_mapa.geometry,
        locations=gdf_mapa.index,
        color=variavel,
        hover_name='Municipio',
        mapbox_style="carto-positron",
        zoom=3.5, center={"lat": -4.5, "lon": -61},
        opacity=0.7
    )

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig

# Para Render funcionar
server = app.server

if __name__ == '__main__':
    app.run_server(debug=True)
