import geopandas as gpd
import plotly.express as px
import json

# Caminho do GeoJSON simplificado
caminho_geojson = "dados/municipios_norte_simplificado.geojson"

# Leitura do GeoJSON
with open(caminho_geojson, "r", encoding="utf-8") as f:
    geojson = json.load(f)

gdf = gpd.read_file(caminho_geojson)
gdf["NM_MUN"] = gdf["NM_MUN"].str.upper().str.strip()

# Criar uma coluna fictícia para plotar
gdf["VALOR"] = 1

# Plotar o mapa
fig = px.choropleth_mapbox(
    gdf,
    geojson=geojson,
    locations="NM_MUN",
    featureidkey="properties.NM_MUN",
    color="VALOR",
    mapbox_style="carto-positron",
    zoom=4.5,
    center={"lat": -3.8, "lon": -52.4},
    opacity=0.6
)

fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
fig.show()
