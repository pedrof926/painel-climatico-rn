import geopandas as gpd

# Caminho completo para o shapefile (.shp)
shapefile = r"C:\Users\Pedro\Downloads\painel_climatico_rn\dados\Municipios_Regiao_Norte_2024.shp"

# Caminho onde será salvo o arquivo GeoJSON
saida_geojson = r"C:\Users\Pedro\Downloads\painel_climatico_rn\dados\municipios_norte.geojson"

# Leitura do shapefile
gdf = gpd.read_file(shapefile)

# Exportar como GeoJSON
gdf.to_file(saida_geojson, driver="GeoJSON")

print("✅ GeoJSON exportado com sucesso em:")
print(saida_geojson)
