#!/bin/bash
# Download parcel data from Virginia county GIS services using curl and jq

download_parcels() {
    local service_url="$1"
    local layer_id="$2"
    local output_dir="$3"
    local batch_size=1000

    echo "============================================================"
    echo "Downloading parcels from: $service_url"
    echo "Layer ID: $layer_id"
    echo "Output directory: $output_dir"
    echo "============================================================"

    # Create output directory
    mkdir -p "$output_dir"

    # Get total count
    local query_url="${service_url}/${layer_id}/query"
    echo "Getting total count..."

    local count=$(curl -s "${query_url}?where=1%3D1&returnCountOnly=true&f=json" | grep -o '"count":[0-9]*' | cut -d':' -f2)

    if [ -z "$count" ]; then
        echo "Error: Could not get feature count"
        return 1
    fi

    echo "Total features: $count"

    # Download in batches
    local offset=0
    local temp_dir="${output_dir}/temp"
    mkdir -p "$temp_dir"

    while [ $offset -lt $count ]; do
        echo "Downloading features $offset to $((offset + batch_size))..."

        local batch_file="${temp_dir}/batch_${offset}.geojson"

        curl -s "${query_url}?where=1%3D1&outFields=*&f=geojson&resultOffset=${offset}&resultRecordCount=${batch_size}" -o "$batch_file"

        # Check if download was successful
        if [ ! -s "$batch_file" ]; then
            echo "Error downloading batch at offset $offset"
            break
        fi

        # Count features in this batch
        local batch_count=$(grep -o '"type":"Feature"' "$batch_file" | wc -l)
        echo "  Downloaded $batch_count features"

        if [ $batch_count -eq 0 ]; then
            echo "  No more features to download"
            break
        fi

        offset=$((offset + batch_count))
    done

    # Merge all batches into a single GeoJSON file
    echo "Merging batches..."
    local output_file="${output_dir}/parcels_complete.geojson"

    # Start with the structure
    echo '{"type":"FeatureCollection","features":[' > "$output_file"

    # Extract features from each batch and append
    local first=true
    for batch_file in "$temp_dir"/*.geojson; do
        if [ -f "$batch_file" ]; then
            # Extract features array content (without the wrapping array brackets)
            local features=$(cat "$batch_file" | grep -o '"features":\[.*\]' | sed 's/"features":\[//' | sed 's/\]$//')

            if [ ! -z "$features" ]; then
                if [ "$first" = true ]; then
                    echo "$features" >> "$output_file"
                    first=false
                else
                    echo ",$features" >> "$output_file"
                fi
            fi
        fi
    done

    echo ']}' >> "$output_file"

    # Clean up temp files
    rm -rf "$temp_dir"

    echo "Saved complete dataset to: $output_file"
    echo "Download complete!"
}

# Main script
case "$1" in
    campbell)
        download_parcels \
            "https://gis.co.campbell.va.us/arcgis/rest/services/Open_Data/Parcel_Lines/MapServer" \
            0 \
            "campbell"
        ;;
    bedford)
        download_parcels \
            "https://webgis.bedfordcountyva.gov/arcgis/rest/services/OpenData/OpenDataProperty/MapServer" \
            0 \
            "bedford"
        ;;
    *)
        echo "Usage: $0 {campbell|bedford}"
        echo "Downloading all counties..."
        $0 campbell
        $0 bedford
        ;;
esac
