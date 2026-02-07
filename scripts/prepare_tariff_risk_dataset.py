"""
TariffShock Dataset Preparation Script
======================================
This script processes Canadian trade data to create a unified dataset 
for the TariffShock risk engine, supporting:
- Sector Risk Leaderboard
- Scenario Simulation Engine
- Explainability Panel

Based on PRD v2 requirements.
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = DATA_DIR / "processed"

# HS2 Code to Sector Mapping (based on Harmonized System)
HS2_SECTOR_MAP = {
    '01': 'Live animals',
    '02': 'Meat and edible meat offal',
    '03': 'Fish and seafood',
    '04': 'Dairy, eggs, honey',
    '05': 'Products of animal origin',
    '06': 'Live trees and plants',
    '07': 'Vegetables',
    '08': 'Fruits and nuts',
    '09': 'Coffee, tea, spices',
    '10': 'Cereals',
    '11': 'Milling products',
    '12': 'Oil seeds',
    '13': 'Lac, gums, resins',
    '14': 'Vegetable plaiting materials',
    '15': 'Fats and oils',
    '16': 'Meat preparations',
    '17': 'Sugars',
    '18': 'Cocoa',
    '19': 'Cereal preparations',
    '20': 'Vegetable preparations',
    '21': 'Miscellaneous food',
    '22': 'Beverages',
    '23': 'Food waste, animal feed',
    '24': 'Tobacco',
    '25': 'Salt, sulfur, stone, cement',
    '26': 'Ores and slag',
    '27': 'Mineral fuels and oils',
    '28': 'Inorganic chemicals',
    '29': 'Organic chemicals',
    '30': 'Pharmaceuticals',
    '31': 'Fertilizers',
    '32': 'Tanning and dye extracts',
    '33': 'Essential oils, cosmetics',
    '34': 'Soap, waxes',
    '35': 'Albuminoidal substances',
    '36': 'Explosives',
    '37': 'Photographic goods',
    '38': 'Miscellaneous chemicals',
    '39': 'Plastics',
    '40': 'Rubber',
    '41': 'Raw hides and skins',
    '42': 'Leather articles',
    '43': 'Furskins',
    '44': 'Wood',
    '45': 'Cork',
    '46': 'Straw and basketware',
    '47': 'Wood pulp',
    '48': 'Paper and paperboard',
    '49': 'Printed books and newspapers',
    '50': 'Silk',
    '51': 'Wool',
    '52': 'Cotton',
    '53': 'Vegetable textile fibers',
    '54': 'Man-made filaments',
    '55': 'Man-made staple fibers',
    '56': 'Wadding and felt',
    '57': 'Carpets',
    '58': 'Special woven fabrics',
    '59': 'Impregnated textiles',
    '60': 'Knitted fabrics',
    '61': 'Knitted apparel',
    '62': 'Woven apparel',
    '63': 'Other textile articles',
    '64': 'Footwear',
    '65': 'Headgear',
    '66': 'Umbrellas',
    '67': 'Feather articles',
    '68': 'Stone and cement articles',
    '69': 'Ceramic products',
    '70': 'Glass',
    '71': 'Precious metals and jewelry',
    '72': 'Iron and steel',
    '73': 'Iron and steel articles',
    '74': 'Copper',
    '75': 'Nickel',
    '76': 'Aluminum',
    '77': 'Reserved',
    '78': 'Lead',
    '79': 'Zinc',
    '80': 'Tin',
    '81': 'Other base metals',
    '82': 'Tools and cutlery',
    '83': 'Miscellaneous metal articles',
    '84': 'Machinery',
    '85': 'Electrical machinery',
    '86': 'Railway equipment',
    '87': 'Vehicles',
    '88': 'Aircraft',
    '89': 'Ships and boats',
    '90': 'Optical and medical instruments',
    '91': 'Clocks and watches',
    '92': 'Musical instruments',
    '93': 'Arms and ammunition',
    '94': 'Furniture',
    '95': 'Toys and games',
    '96': 'Miscellaneous manufactured articles',
    '97': 'Works of art',
    '98': 'Special classification provisions',
    '99': 'Special imports'
}

# Country code mapping for key trading partners
COUNTRY_NAMES = {
    'US': 'United States',
    'CN': 'China',
    'MX': 'Mexico',
    'JP': 'Japan',
    'DE': 'Germany',
    'GB': 'United Kingdom',
    'FR': 'France',
    'KR': 'South Korea',
    'IT': 'Italy',
    'NL': 'Netherlands',
    'BE': 'Belgium',
    'BR': 'Brazil',
    'IN': 'India',
    'AU': 'Australia',
    'ES': 'Spain',
    'CH': 'Switzerland',
    'TW': 'Taiwan',
    'SG': 'Singapore',
    'HK': 'Hong Kong',
    'SE': 'Sweden'
}


def load_export_data():
    """Load and process export data at HS2 level."""
    print("Loading export data...")
    export_path = DATA_DIR / "2024_EXP_HS2" / "2024_EXP_HS2.csv"
    
    df = pd.read_csv(export_path)
    df.columns = ['year_month', 'hs2', 'country', 'state', 'value']
    
    # Clean data
    df['hs2'] = df['hs2'].astype(str).str.zfill(2)
    df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
    
    # Extract year and month
    df['year'] = df['year_month'].astype(str).str[:4].astype(int)
    df['month'] = df['year_month'].astype(str).str[4:6].astype(int)
    
    # Map sector names
    df['sector'] = df['hs2'].map(HS2_SECTOR_MAP).fillna('Other')
    
    # Aggregate exports by HS2 and country (ignoring state)
    exports_agg = df.groupby(['hs2', 'sector', 'country', 'year']).agg({
        'value': 'sum'
    }).reset_index()
    exports_agg.rename(columns={'value': 'export_value'}, inplace=True)
    
    print(f"  Loaded {len(exports_agg)} export records")
    return exports_agg


def load_import_data():
    """Load and process import data at HS2 level."""
    print("Loading import data...")
    import_path = DATA_DIR / "2024_IMP_HS2" / "2024_IMP_HS2.csv"
    
    df = pd.read_csv(import_path)
    df.columns = ['year_month', 'hs2', 'country', 'province', 'state', 'value']
    
    # Clean data
    df['hs2'] = df['hs2'].astype(str).str.zfill(2)
    df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)
    
    # Extract year
    df['year'] = df['year_month'].astype(str).str[:4].astype(int)
    
    # Map sector names
    df['sector'] = df['hs2'].map(HS2_SECTOR_MAP).fillna('Other')
    
    # Aggregate imports by HS2 and country (ignoring province/state)
    imports_agg = df.groupby(['hs2', 'sector', 'country', 'year']).agg({
        'value': 'sum'
    }).reset_index()
    imports_agg.rename(columns={'value': 'import_value'}, inplace=True)
    
    print(f"  Loaded {len(imports_agg)} import records")
    return imports_agg


def load_supplier_change_data():
    """Load and process business supplier change data."""
    print("Loading supplier change data...")
    supplier_path = DATA_DIR / "Business_Supplier_Change_Data.csv"
    
    df = pd.read_csv(supplier_path)
    
    # Filter for "Yes" responses only (businesses that changed suppliers)
    df_yes = df[df['Business or organization changed suppliers as a result of tariffs imposed by either Canada or the United States over the last three months'].str.contains('Yes', na=False)]
    
    # Extract NAICS code from business characteristics
    df_yes = df_yes.copy()
    df_yes['naics_code'] = df_yes['Business characteristics'].str.extract(r'\[(\d+(?:-\d+)?)\]')
    df_yes['industry'] = df_yes['Business characteristics'].str.replace(r'\s*\[.*\]', '', regex=True)
    
    # Rename for clarity
    supplier_data = df_yes[['GEO', 'industry', 'naics_code', 'VALUE']].copy()
    supplier_data.columns = ['geography', 'industry', 'naics_code', 'pct_changed_suppliers']
    supplier_data['pct_changed_suppliers'] = pd.to_numeric(supplier_data['pct_changed_suppliers'], errors='coerce')
    
    print(f"  Loaded {len(supplier_data)} supplier change records")
    return supplier_data


def calculate_sector_metrics(exports_df, imports_df):
    """Calculate sector-level trade metrics."""
    print("Calculating sector metrics...")
    
    # Aggregate by sector
    sector_exports = exports_df.groupby(['hs2', 'sector']).agg({
        'export_value': 'sum'
    }).reset_index()
    
    sector_imports = imports_df.groupby(['hs2', 'sector']).agg({
        'import_value': 'sum'
    }).reset_index()
    
    # Merge exports and imports
    sector_trade = sector_exports.merge(sector_imports, on=['hs2', 'sector'], how='outer').fillna(0)
    
    # Calculate trade balance
    sector_trade['trade_balance'] = sector_trade['export_value'] - sector_trade['import_value']
    sector_trade['total_trade'] = sector_trade['export_value'] + sector_trade['import_value']
    
    # Calculate export/import ratio
    sector_trade['export_ratio'] = sector_trade['export_value'] / (sector_trade['total_trade'] + 1)
    
    print(f"  Calculated metrics for {len(sector_trade)} sectors")
    return sector_trade


def calculate_partner_exposure(exports_df):
    """Calculate exposure to trading partners for each sector."""
    print("Calculating partner exposure...")
    
    # Total exports by sector
    sector_totals = exports_df.groupby(['hs2', 'sector'])['export_value'].sum().reset_index()
    sector_totals.rename(columns={'export_value': 'total_sector_exports'}, inplace=True)
    
    # Exports by sector and country
    partner_exports = exports_df.groupby(['hs2', 'sector', 'country'])['export_value'].sum().reset_index()
    
    # Merge to calculate exposure percentages
    partner_exposure = partner_exports.merge(sector_totals, on=['hs2', 'sector'])
    partner_exposure['partner_share'] = partner_exposure['export_value'] / (partner_exposure['total_sector_exports'] + 1)
    
    # Pivot to get exposure to key partners
    key_partners = ['US', 'CN', 'MX', 'JP', 'DE', 'GB']
    
    exposure_wide = partner_exposure[partner_exposure['country'].isin(key_partners)].pivot_table(
        index=['hs2', 'sector'],
        columns='country',
        values='partner_share',
        aggfunc='sum'
    ).reset_index().fillna(0)
    
    # Rename columns
    exposure_wide.columns = ['hs2', 'sector'] + [f'exposure_{c.lower()}' for c in exposure_wide.columns[2:]]
    
    print(f"  Calculated partner exposure for {len(exposure_wide)} sector-partner pairs")
    return exposure_wide


def calculate_concentration(exports_df):
    """Calculate export concentration (Herfindahl-Hirschman Index)."""
    print("Calculating export concentration...")
    
    # Total exports by sector
    sector_totals = exports_df.groupby(['hs2', 'sector'])['export_value'].sum().reset_index()
    sector_totals.rename(columns={'export_value': 'total_sector_exports'}, inplace=True)
    
    # Exports by sector and country
    partner_exports = exports_df.groupby(['hs2', 'sector', 'country'])['export_value'].sum().reset_index()
    
    # Merge
    partner_exports = partner_exports.merge(sector_totals, on=['hs2', 'sector'])
    partner_exports['partner_share'] = partner_exports['export_value'] / (partner_exports['total_sector_exports'] + 1)
    
    # Calculate HHI (sum of squared shares)
    partner_exports['share_squared'] = partner_exports['partner_share'] ** 2
    concentration = partner_exports.groupby(['hs2', 'sector'])['share_squared'].sum().reset_index()
    concentration.rename(columns={'share_squared': 'hhi_concentration'}, inplace=True)
    
    # Get top partner for each sector
    top_partners = partner_exports.loc[partner_exports.groupby(['hs2', 'sector'])['partner_share'].idxmax()]
    top_partners = top_partners[['hs2', 'sector', 'country', 'partner_share']].copy()
    top_partners.columns = ['hs2', 'sector', 'top_partner', 'top_partner_share']
    
    # Merge
    concentration = concentration.merge(top_partners, on=['hs2', 'sector'])
    
    print(f"  Calculated concentration for {len(concentration)} sectors")
    return concentration


def calculate_risk_score(sector_data, w_exposure=0.4, w_concentration=0.3, w_us_dependency=0.3):
    """
    Calculate Tariff Risk Score (0-100) based on PRD formula:
    Risk = (Exposure × w1 + Concentration × w2) × Shock
    
    For baseline, we use US exposure as proxy for tariff shock risk.
    """
    print("Calculating risk scores...")
    
    df = sector_data.copy()
    
    # Normalize exposure to US (0-1)
    if 'exposure_us' in df.columns:
        df['us_exposure_norm'] = df['exposure_us'] / df['exposure_us'].max()
    else:
        df['us_exposure_norm'] = 0.5  # Default if no US exposure data
    
    # Normalize HHI (already 0-1)
    df['hhi_norm'] = df['hhi_concentration'] / df['hhi_concentration'].max()
    
    # Normalize top partner share
    df['top_partner_norm'] = df['top_partner_share']
    
    # Calculate base risk score (0-100)
    df['risk_score'] = (
        (df['us_exposure_norm'] * w_exposure +
         df['hhi_norm'] * w_concentration +
         df['top_partner_norm'] * w_us_dependency)
    ) * 100
    
    # Clip to 0-100
    df['risk_score'] = df['risk_score'].clip(0, 100)
    
    print(f"  Calculated risk scores for {len(df)} sectors")
    return df


def simulate_tariff_scenario(sector_data, tariff_pct=10, target_partner='US'):
    """
    Simulate the impact of a tariff increase on risk scores.
    
    Parameters:
    - tariff_pct: Tariff increase percentage (0-25%)
    - target_partner: Target trading partner
    """
    df = sector_data.copy()
    
    # Shock multiplier based on tariff percentage
    shock_multiplier = 1 + (tariff_pct / 100)
    
    # Partner exposure column
    exposure_col = f'exposure_{target_partner.lower()}'
    
    if exposure_col in df.columns:
        # Calculate shocked risk score
        df['shocked_risk_score'] = df['risk_score'] * (1 + df[exposure_col] * (shock_multiplier - 1))
        df['risk_delta'] = df['shocked_risk_score'] - df['risk_score']
        df['affected_export_value'] = df['export_value'] * df[exposure_col] * (tariff_pct / 100)
    else:
        df['shocked_risk_score'] = df['risk_score']
        df['risk_delta'] = 0
        df['affected_export_value'] = 0
    
    # Clip shocked scores
    df['shocked_risk_score'] = df['shocked_risk_score'].clip(0, 100)
    
    return df


def create_final_dataset(exports_df, imports_df, supplier_df):
    """Create the final unified dataset for TariffShock."""
    print("\nCreating final dataset...")
    
    # Calculate all metrics
    sector_trade = calculate_sector_metrics(exports_df, imports_df)
    partner_exposure = calculate_partner_exposure(exports_df)
    concentration = calculate_concentration(exports_df)
    
    # Merge all sector-level data
    final_df = sector_trade.merge(partner_exposure, on=['hs2', 'sector'], how='left')
    final_df = final_df.merge(concentration, on=['hs2', 'sector'], how='left')
    
    # Fill NaN values
    final_df = final_df.fillna(0)
    
    # Calculate risk scores
    final_df = calculate_risk_score(final_df)
    
    # Add scenario simulation columns (baseline = 10% US tariff)
    final_df = simulate_tariff_scenario(final_df, tariff_pct=10, target_partner='US')
    
    # Map top partner names
    final_df['top_partner_name'] = final_df['top_partner'].map(COUNTRY_NAMES).fillna(final_df['top_partner'])
    
    # Reorder columns for clarity
    column_order = [
        'hs2', 'sector', 
        'export_value', 'import_value', 'trade_balance', 'total_trade', 'export_ratio',
        'exposure_us', 'exposure_cn', 'exposure_mx', 'exposure_jp', 'exposure_de', 'exposure_gb',
        'hhi_concentration', 'top_partner', 'top_partner_name', 'top_partner_share',
        'risk_score', 'shocked_risk_score', 'risk_delta', 'affected_export_value'
    ]
    
    # Only keep columns that exist
    final_columns = [c for c in column_order if c in final_df.columns]
    final_df = final_df[final_columns]
    
    # Sort by risk score
    final_df = final_df.sort_values('risk_score', ascending=False).reset_index(drop=True)
    
    print(f"  Final dataset has {len(final_df)} sectors and {len(final_df.columns)} features")
    return final_df


def main():
    """Main execution function."""
    print("=" * 60)
    print("TariffShock Dataset Preparation")
    print("=" * 60)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load data
    exports_df = load_export_data()
    imports_df = load_import_data()
    supplier_df = load_supplier_change_data()
    
    # Create final dataset
    final_df = create_final_dataset(exports_df, imports_df, supplier_df)
    
    # Save datasets
    print("\nSaving datasets...")
    
    # Main risk dataset
    risk_output = OUTPUT_DIR / "sector_risk_dataset.csv"
    final_df.to_csv(risk_output, index=False)
    print(f"  Saved: {risk_output}")
    
    # Partner-level trade data (for visualizations)
    partner_exports = exports_df.groupby(['hs2', 'sector', 'country']).agg({
        'export_value': 'sum'
    }).reset_index()
    partner_exports['country_name'] = partner_exports['country'].map(COUNTRY_NAMES).fillna(partner_exports['country'])
    partner_output = OUTPUT_DIR / "partner_trade_data.csv"
    partner_exports.to_csv(partner_output, index=False)
    print(f"  Saved: {partner_output}")
    
    # Supplier change data (for industry-level insights)
    supplier_output = OUTPUT_DIR / "supplier_change_data.csv"
    supplier_df.to_csv(supplier_output, index=False)
    print(f"  Saved: {supplier_output}")
    
    # Summary statistics
    print("\n" + "=" * 60)
    print("Dataset Summary")
    print("=" * 60)
    print(f"Total sectors: {len(final_df)}")
    print(f"Total export value: ${final_df['export_value'].sum():,.0f}")
    print(f"Total import value: ${final_df['import_value'].sum():,.0f}")
    print(f"Average risk score: {final_df['risk_score'].mean():.1f}")
    print(f"Max risk score: {final_df['risk_score'].max():.1f}")
    print(f"\nTop 5 highest risk sectors:")
    print(final_df[['sector', 'risk_score', 'top_partner_name', 'top_partner_share']].head(5).to_string(index=False))
    
    print("\n" + "=" * 60)
    print("Dataset preparation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
