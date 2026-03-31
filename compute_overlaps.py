"""
Compute spatial overlaps between colonial territory claims and
Indigenous territories from Native Land Digital.

Outputs a CSV mapping each colonial claim (name, sovereign, year)
to the Indigenous territories it overlaps with, including the
Native Land slug as persistent identifier.
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import json
import sys
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path('/home/jic823/canada_geo_evolution/web/data')
NATIVE_LAND = Path('/home/jic823/plato/native_land_territories.geojson')
OUTPUT = Path('/home/jic823/canada_geo_evolution/claim_indigenous_overlaps.csv')

def load_all_colonial():
    """Load all colonial boundaries from individual year GeoJSON files."""
    years_file = DATA_DIR / 'years.json'
    with open(years_file) as f:
        years = json.load(f)

    frames = []
    for year in years:
        fpath = DATA_DIR / f'{year}.geojson'
        if fpath.exists():
            gdf = gpd.read_file(fpath)
            frames.append(gdf)

    colonial = pd.concat(frames, ignore_index=True)
    colonial = gpd.GeoDataFrame(colonial, geometry='geometry', crs='EPSG:4326')

    # Make geometries valid
    colonial['geometry'] = colonial['geometry'].make_valid()

    print(f"Loaded {len(colonial)} colonial polygons across {len(years)} years")
    return colonial


def load_native_land():
    """Load Native Land territories, extract name and slug."""
    print("Loading Native Land territories...")
    native = gpd.read_file(NATIVE_LAND)

    # Extract properties we need
    native['territory_name'] = native['Name']
    native['slug'] = native['Slug']

    # Make geometries valid
    native['geometry'] = native['geometry'].make_valid()

    print(f"Loaded {len(native)} Indigenous territories")
    return native[['territory_name', 'slug', 'geometry']]


def compute_overlaps(colonial, native, min_overlap_km2=100):
    """
    Find all overlaps between colonial claims and Indigenous territories.

    Args:
        min_overlap_km2: minimum overlap area in km² to count as significant
    """
    results = []

    # Get unique colonial claims (name + sovereign + year)
    claims = colonial.groupby(['name', 'sovereign', 'year']).first().reset_index()
    claims = gpd.GeoDataFrame(claims, geometry='geometry', crs='EPSG:4326')

    total = len(claims)
    print(f"\nComputing overlaps for {total} colonial claims against {len(native)} Indigenous territories...")

    # Use spatial index for efficiency
    native_sindex = native.sindex

    for idx, claim in claims.iterrows():
        claim_geom = claim.geometry
        if claim_geom is None or claim_geom.is_empty:
            continue

        # Find candidate overlaps using spatial index
        candidates = list(native_sindex.intersection(claim_geom.bounds))

        if not candidates:
            continue

        for cand_idx in candidates:
            native_row = native.iloc[cand_idx]
            native_geom = native_row.geometry

            if native_geom is None or native_geom.is_empty:
                continue

            try:
                if claim_geom.intersects(native_geom):
                    intersection = claim_geom.intersection(native_geom)
                    if not intersection.is_empty:
                        results.append({
                            'claim_name': claim['name'],
                            'claim_sovereign': claim['sovereign'],
                            'claim_year': int(claim['year']),
                            'indigenous_territory': native_row['territory_name'],
                            'indigenous_slug': native_row['slug'],
                        })
            except Exception as e:
                # Skip topology errors
                continue

        # Progress
        if (idx + 1) % 50 == 0 or idx + 1 == total:
            print(f"  Processed {idx + 1}/{total} claims, {len(results)} overlaps found so far")

    return pd.DataFrame(results)


def main():
    colonial = load_all_colonial()
    native = load_native_land()

    overlaps = compute_overlaps(colonial, native)

    # Deduplicate: same claim name+sovereign can appear in multiple years
    # but overlap with same territory. Keep unique combinations with year range.
    summary = overlaps.groupby(
        ['claim_name', 'claim_sovereign', 'indigenous_territory', 'indigenous_slug']
    ).agg(
        year_min=('claim_year', 'min'),
        year_max=('claim_year', 'max'),
        year_count=('claim_year', 'nunique')
    ).reset_index()

    summary = summary.sort_values(['claim_name', 'claim_sovereign', 'indigenous_territory'])

    summary.to_csv(OUTPUT, index=False)
    print(f"\nWrote {len(summary)} unique claim-territory overlaps to {OUTPUT}")

    # Print summary stats
    print(f"\nSummary:")
    print(f"  Unique colonial claims: {summary[['claim_name', 'claim_sovereign']].drop_duplicates().shape[0]}")
    print(f"  Unique Indigenous territories overlapped: {summary['indigenous_slug'].nunique()}")
    print(f"  Total overlap connections: {len(summary)}")

    # Show a sample
    print(f"\nSample overlaps for 'Rupert\\'s Land':")
    sample = summary[summary['claim_name'] == "Rupert's Land"].head(20)
    for _, row in sample.iterrows():
        print(f"  {row['indigenous_territory']} ({row['indigenous_slug']})")


if __name__ == '__main__':
    main()
