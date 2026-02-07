"""
TariffShock Data Loading Module
===============================
Loads and preprocesses static data for the Risk Engine.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import logging

from .schemas import Partner, SectorPartnerExport, SectorSummary

logger = logging.getLogger(__name__)

# Default data directory
DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data" / "processed"


class DataLoader:
    """
    Loads and manages static data for the Risk Engine.
    
    Data is loaded once at startup and cached for reuse.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self._sector_partner_exports: Optional[List[SectorPartnerExport]] = None
        self._sector_summaries: Optional[Dict[str, SectorSummary]] = None
        self._is_loaded = False
    
    def load(self) -> None:
        """Load all static data from CSV files."""
        if self._is_loaded:
            logger.info("Data already loaded, skipping reload")
            return
        
        logger.info(f"Loading data from {self.data_dir}")
        
        # Load sector risk dataset
        sector_file = self.data_dir / "sector_risk_dataset.csv"
        if not sector_file.exists():
            raise FileNotFoundError(f"Sector risk dataset not found: {sector_file}")
        
        sector_df = pd.read_csv(sector_file)
        
        # Load partner trade data
        partner_file = self.data_dir / "partner_trade_data.csv"
        if not partner_file.exists():
            raise FileNotFoundError(f"Partner trade data not found: {partner_file}")
        
        partner_df = pd.read_csv(partner_file)
        
        # Process and cache data
        self._process_sector_data(sector_df)
        self._process_partner_data(partner_df, sector_df)
        
        self._is_loaded = True
        logger.info(f"Loaded {len(self._sector_summaries)} sectors")
    
    def _map_country_to_partner(self, country: str) -> Partner:
        """Map country codes to Partner enum (US, China, EU, Other)."""
        if country == "US":
            return Partner.US
        elif country == "CN":
            return Partner.CHINA
        elif country in ["DE", "FR", "IT", "ES", "NL", "BE", "AT", "PL", "SE", "DK", 
                         "FI", "IE", "PT", "GR", "CZ", "RO", "HU", "SK", "BG", 
                         "HR", "SI", "LT", "LV", "EE", "CY", "LU", "MT"]:
            return Partner.EU
        else:
            return Partner.OTHER
    
    def _process_sector_data(self, df: pd.DataFrame) -> None:
        """Process sector summary data."""
        self._sector_summaries = {}
        
        for _, row in df.iterrows():
            sector_id = str(row['hs2']).zfill(2)
            sector_name = row['sector']
            
            # Build partner shares from exposure columns
            partner_shares = {}
            us_exposure = row.get('exposure_us', 0) or 0
            cn_exposure = row.get('exposure_cn', 0) or 0
            
            # Calculate EU exposure (sum of EU countries)
            eu_cols = ['exposure_de', 'exposure_fr', 'exposure_gb']  # Note: GB is post-Brexit but including for data
            eu_exposure = sum(row.get(col, 0) or 0 for col in eu_cols if col in row.index)
            
            # Other is remainder
            other_exposure = max(0, 1 - us_exposure - cn_exposure - eu_exposure)
            
            # Normalize to sum to 1
            total = us_exposure + cn_exposure + eu_exposure + other_exposure
            if total > 0:
                partner_shares = {
                    "US": us_exposure / total,
                    "China": cn_exposure / total,
                    "EU": eu_exposure / total,
                    "Other": other_exposure / total
                }
            else:
                partner_shares = {"US": 0, "China": 0, "EU": 0, "Other": 1}
            
            # Determine top partner
            top_partner_str = row.get('top_partner', 'US')
            top_partner = self._map_country_to_partner(top_partner_str)
            top_partner_share = min(1.0, row.get('top_partner_share', 0) or 0)
            
            try:
                summary = SectorSummary(
                    sector_id=sector_id,
                    sector_name=sector_name,
                    total_exports=row.get('export_value', 0) or 0,
                    partner_shares=partner_shares,
                    top_partner=top_partner,
                    top_partner_share=top_partner_share
                )
                self._sector_summaries[sector_id] = summary
            except ValueError as e:
                logger.warning(f"Skipping sector {sector_id}: {e}")
    
    def _process_partner_data(self, partner_df: pd.DataFrame, sector_df: pd.DataFrame) -> None:
        """Process sector-partner export data."""
        self._sector_partner_exports = []
        
        # Get sector names from sector_df
        sector_names = dict(zip(
            sector_df['hs2'].astype(str).str.zfill(2),
            sector_df['sector']
        ))
        
        # Aggregate by sector and mapped partner
        partner_df['sector_id'] = partner_df['hs2'].astype(str).str.zfill(2)
        partner_df['mapped_partner'] = partner_df['country'].apply(self._map_country_to_partner)
        
        agg_df = partner_df.groupby(['sector_id', 'mapped_partner']).agg({
            'export_value': 'sum'
        }).reset_index()
        
        for _, row in agg_df.iterrows():
            sector_id = row['sector_id']
            sector_name = sector_names.get(sector_id, f"Sector {sector_id}")
            
            try:
                export = SectorPartnerExport(
                    sector_id=sector_id,
                    sector_name=sector_name,
                    partner=row['mapped_partner'],
                    export_value=row['export_value']
                )
                self._sector_partner_exports.append(export)
            except ValueError as e:
                logger.warning(f"Skipping export record: {e}")
    
    @property
    def sector_summaries(self) -> Dict[str, SectorSummary]:
        """Get all sector summaries."""
        if not self._is_loaded:
            self.load()
        return self._sector_summaries
    
    @property
    def sector_partner_exports(self) -> List[SectorPartnerExport]:
        """Get all sector-partner export records."""
        if not self._is_loaded:
            self.load()
        return self._sector_partner_exports
    
    def get_sector(self, sector_id: str) -> Optional[SectorSummary]:
        """Get a specific sector by ID."""
        if not self._is_loaded:
            self.load()
        return self._sector_summaries.get(sector_id)
    
    def get_all_sector_ids(self) -> List[str]:
        """Get all sector IDs."""
        if not self._is_loaded:
            self.load()
        return list(self._sector_summaries.keys())


# Global data loader instance (singleton pattern)
_data_loader: Optional[DataLoader] = None


def get_data_loader(data_dir: Optional[Path] = None) -> DataLoader:
    """Get or create the global data loader instance."""
    global _data_loader
    if _data_loader is None:
        _data_loader = DataLoader(data_dir)
    return _data_loader


def load_data(data_dir: Optional[Path] = None) -> DataLoader:
    """Load data and return the data loader."""
    loader = get_data_loader(data_dir)
    loader.load()
    return loader
