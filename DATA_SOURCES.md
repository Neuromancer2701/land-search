# GIS Data Sources for Virginia Counties

## Summary

This document details the GIS data sources discovered for Bedford, Campbell, and Amherst counties in Virginia.

---

## Bedford County, Virginia

### Official GIS Portal
- **Open Data Hub**: https://geohub-bedfordvagis.opendata.arcgis.com/
- **Contact**: gis@bedfordcountyva.gov | (540) 587-5678
- **Address**: 122 E Main St., Suite 202

### REST API Endpoints

**Primary Parcel Service:**
```
Service: OpenDataProperty MapServer
Base URL: https://webgis.bedfordcountyva.gov/arcgis/rest/services/OpenData/OpenDataProperty/MapServer
Parcels Layer: Layer 0 (County Parcels)
Query Endpoint: https://webgis.bedfordcountyva.gov/arcgis/rest/services/OpenData/OpenDataProperty/MapServer/0/query
```

**Available Layers in OpenDataProperty Service:**
- Layer 0: County Parcels (Polygon)
- Layer 1: Future Land Use (Polygon)
- Layer 2: Zoning Overlay (Polygon)
- Layer 3: Zoning (Polygon)
- Layer 4: Tax Grid (Polygon)
- Layer 5: Subdivision (Polygon)
- Table 6: Real Estate Improvements

**Service Capabilities:**
- Max Record Count: 1,000 per request
- Coordinate System: EPSG:2284 (NAD83 / Virginia South, US Survey Feet)
- Supported Formats: JSON, GeoJSON, PBF
- Total Parcels: ~50,688

**All OpenData Services Available:**
```
https://webgis.bedfordcountyva.gov/arcgis/rest/services/OpenData/
  ├── OpenDataCountyProperty
  ├── OpenDataEnvironmental
  ├── OpenDataFacilities
  ├── OpenDataHydrology
  ├── OpenDataProperty (Parcels)
  ├── OpenDataPublicSafety
  ├── OpenDataRecreation
  ├── OpenDataReference
  ├── OpenDataSchools
  ├── OpenDataTownofBedford
  ├── OpenDataTransportation
  └── OpenDataVoting
```

**Example Query:**
```bash
# Get count
curl "https://webgis.bedfordcountyva.gov/arcgis/rest/services/OpenData/OpenDataProperty/MapServer/0/query?where=1%3D1&returnCountOnly=true&f=json"

# Download parcels (paginated)
curl "https://webgis.bedfordcountyva.gov/arcgis/rest/services/OpenData/OpenDataProperty/MapServer/0/query?where=1%3D1&outFields=*&f=geojson&resultOffset=0&resultRecordCount=1000"
```

---

## Campbell County, Virginia

### Official GIS Portal
- **ArcGIS Hub**: https://data1-campbellva.hub.arcgis.com/
- **County GIS Page**: https://www.co.campbell.va.us/630/GIS-Maps
- **Contact**: gisweb@campbellcountyva.gov

### REST API Endpoints

**Primary Parcel Service:**
```
Service: Parcel Lines MapServer
Base URL: https://gis.co.campbell.va.us/arcgis/rest/services/Open_Data/Parcel_Lines/MapServer
Parcels Layer: Layer 0 (Parcels)
Query Endpoint: https://gis.co.campbell.va.us/arcgis/rest/services/Open_Data/Parcel_Lines/MapServer/0/query
```

**Service Capabilities:**
- Max Record Count: 2,000 per request
- Coordinate System: EPSG:2284 (NAD83 / Virginia South, US Survey Feet)
- Supported Formats: JSON, GeoJSON, PBF
- Total Parcels: ~37,826
- Description: Parcel lines and associated Real Estate data for Campbell County, Virginia

**Service Metadata:**
- Copyright: Campbell County GIS Office
- Service Description: Parcel lines and associated Real Estate data for Campbell County, Virginia
- Geometry Type: esriGeometryPolygon

**Example Query:**
```bash
# Get count
curl "https://gis.co.campbell.va.us/arcgis/rest/services/Open_Data/Parcel_Lines/MapServer/0/query?where=1%3D1&returnCountOnly=true&f=json"

# Download parcels (paginated)
curl "https://gis.co.campbell.va.us/arcgis/rest/services/Open_Data/Parcel_Lines/MapServer/0/query?where=1%3D1&outFields=*&f=geojson&resultOffset=0&resultRecordCount=2000"
```

---

## Amherst County, Virginia

### Official GIS Portal
- **GIS Viewer**: https://www.amherstgis.timmons.com/
- **Mobile Version**: https://www.amherstgis.timmons.com/mobile
- **Hosted By**: Timmons Group
- **Contact**: Planning and Zoning Department | (434) 946-9303
- **Address**: 100 Goodwin St, P.O. Box 719, Amherst, VA 24521

### Data Access Status
⚠️ **No Public REST API Available**

The Amherst County GIS portal is hosted by Timmons Group and does NOT provide public REST API endpoints for bulk data download. The system is viewer-only through the web interface.

### Alternative Data Sources

#### 1. **Direct County Contact** (Recommended)
Contact the Planning and Zoning Department to request parcel data:
- Phone: (434) 946-9303
- They may be able to provide data exports directly

#### 2. **Third-Party Data Vendors**

**Regrid** (Free and Paid Tiers)
- URL: https://app.regrid.com/us/va/amherst
- Free account allows limited access
- Pro account enables export as Shapefile, Spreadsheet, or KML
- Coverage: 27,182+ properties

**Dynamo Spatial** (Commercial)
- URL: https://www.dynamospatial.com/c/amherst-county-va/parcel-data
- Format: ESRI Shapefile (.SHP)
- Coverage: 27,182+ properties
- Features: Parcel boundaries and detailed property ownership

**Mapping Solutions GIS** (Commercial)
- URL: https://www.mappingsolutionsgis.com/amherst-county-virginia-gis-parcel-data/
- Formats: Shapefile (.shp), KML
- Compatible with ESRI ArcGIS and similar software

**ReportAll USA** (Commercial)
- URL: https://reportallusa.com/purchase-shapefiles/Virginia/51009
- Formats: Shapefile, Excel (ESRI and Excel formats)
- County FIPS Code: 51009

**Equator Studios** (Commercial)
- URL: https://gis.equatorstudios.com/virginia_amherst/
- Offers: LiDAR, contours, parcel data, building footprints, DEMs, point clouds
- Multiple GIS formats available

#### 3. **Virginia State Resources**

**Virginia Geographic Information Network (VGIN)**
- May have statewide parcel data including Amherst
- URL: https://vgin.vdem.virginia.gov/

---

## Download Status

| County | Parcels | API Access | Download Status |
|--------|---------|------------|-----------------|
| Bedford | ~50,688 | ✅ Public REST API | ⏳ In Progress |
| Campbell | ~37,826 | ✅ Public REST API | ⏳ In Progress |
| Amherst | ~27,182 | ❌ No public API | ⚠️ Requires alternative source |

---

## Technical Notes

### Coordinate Reference Systems
All three counties use: **EPSG:2284** (NAD83 / Virginia South, US Survey Feet)

To convert to WGS84 (latitude/longitude) for web mapping:
```bash
ogr2ogr -t_srs EPSG:4326 output_wgs84.geojson input_vastate.geojson
```

### Data Update Frequency
- **Bedford County**: Monthly updates (parcel data)
- **Campbell County**: Real estate and parcel data updated regularly
- **Amherst County**: Contact county for update schedule

### Attribution
When using this data, please attribute:
- Bedford County GIS Office
- Campbell County GIS Office
- Amherst County (when data is obtained)

---

## References

- [Bedford County GIS Open Data Portal](https://geohub-bedfordvagis.opendata.arcgis.com/)
- [Campbell County, Virginia ArcGIS Hub](https://data1-campbellva.hub.arcgis.com/)
- [Amherst County Gis - Timmons Group](https://www.amherstgis.timmons.com/)
- [Virginia Open Data Portal](https://data.virginia.gov/)
- [ArcGIS REST APIs Documentation](https://developers.arcgis.com/rest/)

---

*Last Updated: February 6, 2026*
