# Virginia Property Search - GIS Data

This directory contains GIS parcel data for property search in Virginia counties.

## Counties Covered

### 1. Bedford County
- **Data Source**: [Bedford County GIS Open Data Portal](https://geohub-bedfordvagis.opendata.arcgis.com/)
- **REST API**: `https://webgis.bedfordcountyva.gov/arcgis/rest/services/OpenData/OpenDataProperty/MapServer/0`
- **Total Parcels**: ~50,688
- **Directory**: `bedford/`
- **File**: `bedford/parcels_complete.geojson`
- **Status**: ✓ Downloaded
- **Last Updated**: February 2026

### 2. Campbell County
- **Data Source**: [Campbell County GIS Hub](https://data1-campbellva.hub.arcgis.com/)
- **REST API**: `https://gis.co.campbell.va.us/arcgis/rest/services/Open_Data/Parcel_Lines/MapServer/0`
- **Total Parcels**: ~37,826
- **Directory**: `campbell/`
- **File**: `campbell/parcels_complete.geojson`
- **Status**: ✓ Downloaded
- **Last Updated**: February 2026

### 3. Amherst County
- **Data Source**: [Timmons Group GIS Portal](https://www.amherstgis.timmons.com/)
- **Public REST API**: ❌ Not Available
- **Total Parcels**: ~27,182
- **Status**: ⚠️ No public API available

**Amherst County Data Access Options:**

Since Amherst County does not provide a public REST API for bulk downloads, you have the following options:

1. **Contact County Directly**
   - Planning and Zoning Department: (434) 946-9303
   - Request parcel data export

2. **Third-Party Data Vendors**
   - **Regrid** (Free tier available): https://app.regrid.com/us/va/amherst
   - **Dynamo Spatial**: https://www.dynamospatial.com/c/amherst-county-va/parcel-data
   - **Mapping Solutions GIS**: https://www.mappingsolutionsgis.com/amherst-county-virginia-gis-parcel-data/
   - **Equator Studios**: https://gis.equatorstudios.com/virginia_amherst/

3. **Manual Export from GIS Viewer**
   - Use the web interface at https://www.amherstgis.timmons.com/
   - May require contacting the vendor for export capabilities

## Data Format

All downloaded parcel data is in **GeoJSON** format, which is compatible with:
- QGIS
- ArcGIS
- Python (GeoPandas, Shapely)
- JavaScript mapping libraries (Leaflet, Mapbox, OpenLayers)
- PostGIS and other spatial databases

## File Structure

```
House_Search_GIS/
├── README.md                      # This file
├── download_parcels.sh            # Download script
├── download_parcels.py            # Alternative Python download script
├── bedford/
│   └── parcels_complete.geojson   # Bedford County parcels
├── campbell/
│   └── parcels_complete.geojson   # Campbell County parcels
└── amherst/                       # (To be added when data is obtained)
```

## Using the Data

### View in QGIS
1. Open QGIS
2. Layer → Add Layer → Add Vector Layer
3. Select the GeoJSON file
4. The parcels will display on the map

### Python Example
```python
import geopandas as gpd

# Load parcels
bedford = gpd.read_file('bedford/parcels_complete.geojson')
campbell = gpd.read_file('campbell/parcels_complete.geojson')

# Filter by criteria (example)
large_parcels = bedford[bedford.geometry.area > 43560]  # > 1 acre in sq ft

# Spatial query (example)
from shapely.geometry import Point
point = Point(-79.5, 37.3)
nearby = bedford[bedford.distance(point) < 0.01]
```

### JavaScript/Web Mapping Example
```javascript
// Load with Leaflet
fetch('bedford/parcels_complete.geojson')
  .then(response => response.json())
  .then(data => {
    L.geoJSON(data, {
      onEachFeature: (feature, layer) => {
        layer.bindPopup(feature.properties.OWNER);
      }
    }).addTo(map);
  });
```

## Downloading/Updating Data

To refresh the data or download again:

```bash
./download_parcels.sh campbell   # Download Campbell County
./download_parcels.sh bedford    # Download Bedford County
./download_parcels.sh            # Download all available counties
```

## Data Attributes

Each parcel typically includes:
- **Parcel ID/PIN**: Unique identifier
- **Owner Information**: Owner name, mailing address
- **Location**: Street address
- **Tax Information**: Assessment values, tax map reference
- **Land Use**: Zoning, land use classification
- **Geometry**: Polygon boundaries
- **Acreage**: Land area

(Specific attributes vary by county - use QGIS or `ogrinfo` to inspect)

## Coordinate Reference System

- **Bedford County**: EPSG:2284 (NAD83 / Virginia South, US Survey Feet)
- **Campbell County**: EPSG:2284 (NAD83 / Virginia South, US Survey Feet)

To reproject to WGS84 (lat/lon) for web mapping:
```bash
ogr2ogr -t_srs EPSG:4326 output.geojson input.geojson
```

## Resources

### Official GIS Portals
- [Bedford County GIS Open Data Portal](https://geohub-bedfordvagis.opendata.arcgis.com/)
- [Campbell County GIS Hub](https://data1-campbellva.hub.arcgis.com/)
- [Amherst County GIS](https://www.amherstgis.timmons.com/)

### Virginia State Resources
- [Virginia Geographic Information Network (VGIN)](https://vgin.vdem.virginia.gov/)
- [Virginia Open Data Portal](https://data.virginia.gov/)

## Next Steps

To use this data for property searching, you'll need to:

1. **Define Your Search Criteria**
   - Acreage requirements
   - Price range
   - Zoning requirements
   - Distance from roads/utilities
   - Topography preferences

2. **Obtain Additional Layers** (if needed)
   - Roads/highways
   - Utilities (water, sewer, electric)
   - Topography/elevation data
   - Flood zones
   - Conservation easements

3. **Set Up Analysis Tools**
   - Install QGIS or use Python with GeoPandas
   - Create spatial queries and filters
   - Visualize results on maps

4. **Cross-Reference with Real Estate Data**
   - Zillow, Realtor.com listings
   - County assessor databases
   - For-sale-by-owner listings

## Contact

For questions about:
- **Bedford County GIS**: gis@bedfordcountyva.gov | (540) 587-5678
- **Campbell County GIS**: gisweb@campbellcountyva.gov
- **Amherst County GIS**: Planning & Zoning (434) 946-9303

---

*Last updated: February 6, 2026*
