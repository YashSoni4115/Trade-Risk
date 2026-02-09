"""
US Tariffs on Canadian Exports
==============================
This file contains known/simulated tariff rates imposed on Canadian exports
by the United States and other trading partners.

Sources:
- Section 232 tariffs (steel/aluminum): 25% steel, 10% aluminum
- Section 301 tariffs on various goods
- Softwood lumber tariffs: ~20%
- Various agricultural tariffs

Note: These are representative rates for simulation purposes.
"""

# US Tariffs on Canadian Products by HS2 Category
# Format: HS2 code -> tariff rate (%)
US_TARIFFS_ON_CANADA = {
    # Metals - Section 232 tariffs
    "72": 25.0,  # Iron and steel - 25% tariff
    "73": 25.0,  # Iron and steel articles - 25% tariff
    "76": 10.0,  # Aluminum - 10% tariff
    
    # Wood and lumber - Softwood lumber dispute
    "44": 20.0,  # Wood and wood articles - ~20% CVD/AD
    "47": 15.0,  # Wood pulp - 15%
    "48": 10.0,  # Paper and paperboard - 10%
    
    # Agricultural products
    "04": 15.0,  # Dairy products - various tariffs
    "10": 10.0,  # Cereals - 10%
    "02": 5.0,   # Meat - 5%
    "03": 5.0,   # Fish - 5%
    
    # Vehicles and parts - potential tariffs
    "87": 25.0,  # Vehicles - threatened 25% tariff
    "84": 10.0,  # Machinery - 10%
    "85": 10.0,  # Electrical machinery - 10%
    
    # Energy - potential tariffs
    "27": 10.0,  # Mineral fuels and oils - 10%
    
    # Other affected sectors
    "39": 10.0,  # Plastics - 10%
    "40": 10.0,  # Rubber - 10%
    "94": 15.0,  # Furniture - 15%
}

# China Tariffs on Canadian Products (retaliatory)
CHINA_TARIFFS_ON_CANADA = {
    "10": 25.0,  # Cereals (canola) - 25%
    "12": 25.0,  # Oil seeds - 25%
    "02": 25.0,  # Meat - 25%
    "03": 25.0,  # Fish - 25%
    "47": 20.0,  # Wood pulp - 20%
}

# EU Tariffs on Canadian Products
EU_TARIFFS_ON_CANADA = {
    # Generally lower due to CETA agreement
    "72": 5.0,   # Steel - 5%
    "76": 5.0,   # Aluminum - 5%
}

# Default tariff rate for sectors without specific tariffs
DEFAULT_TARIFF_RATE = 0.0

def get_tariff_rate(hs2_code: str, partner: str) -> float:
    """
    Get the tariff rate for a specific HS2 sector and trading partner.
    
    Args:
        hs2_code: 2-digit HS code (e.g., "72" for steel)
        partner: Trading partner ("US", "China", "EU")
        
    Returns:
        Tariff rate as a percentage (0-100)
    """
    hs2 = str(hs2_code).zfill(2)
    
    if partner == "US":
        return US_TARIFFS_ON_CANADA.get(hs2, DEFAULT_TARIFF_RATE)
    elif partner == "China":
        return CHINA_TARIFFS_ON_CANADA.get(hs2, DEFAULT_TARIFF_RATE)
    elif partner == "EU":
        return EU_TARIFFS_ON_CANADA.get(hs2, DEFAULT_TARIFF_RATE)
    else:
        return DEFAULT_TARIFF_RATE

def get_max_tariff_rate(hs2_code: str) -> float:
    """Get the maximum tariff rate across all partners for a sector."""
    hs2 = str(hs2_code).zfill(2)
    rates = [
        US_TARIFFS_ON_CANADA.get(hs2, 0),
        CHINA_TARIFFS_ON_CANADA.get(hs2, 0),
        EU_TARIFFS_ON_CANADA.get(hs2, 0)
    ]
    return max(rates)

def get_all_tariffed_sectors() -> dict:
    """Get all sectors with non-zero tariffs."""
    all_sectors = {}
    
    for hs2, rate in US_TARIFFS_ON_CANADA.items():
        if hs2 not in all_sectors:
            all_sectors[hs2] = {"US": 0, "China": 0, "EU": 0}
        all_sectors[hs2]["US"] = rate
    
    for hs2, rate in CHINA_TARIFFS_ON_CANADA.items():
        if hs2 not in all_sectors:
            all_sectors[hs2] = {"US": 0, "China": 0, "EU": 0}
        all_sectors[hs2]["China"] = rate
    
    for hs2, rate in EU_TARIFFS_ON_CANADA.items():
        if hs2 not in all_sectors:
            all_sectors[hs2] = {"US": 0, "China": 0, "EU": 0}
        all_sectors[hs2]["EU"] = rate
    
    return all_sectors
