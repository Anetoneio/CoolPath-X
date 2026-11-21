try:
    import osmnx
    print("osmnx: available")
except ImportError:
    print("osmnx: NOT available")

try:
    import rasterio
    print("rasterio: available")
except ImportError:
    print("rasterio: NOT available")

try:
    import geopandas
    print("geopandas: available")
except ImportError:
    print("geopandas: NOT available")

try:
    import shapely
    print("shapely: available")
except ImportError:
    print("shapely: NOT available")

try:
    import jsonschema
    print("jsonschema: available")
except ImportError:
    print("jsonschema: NOT available")