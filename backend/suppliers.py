"""Global supplier registry shared by Streamlit UI and FastAPI."""

from typing import Any, Dict

SUPPLIERS: Dict[str, Dict[str, Any]] = {
    "SUPPLIER-SINO-COBALT": {
        "name": "Sino Cobalt Industries",
        "zone": "MINING-ZONE-A-CHINA",
        "country": "China",
        "lat": 35.8617,
        "lon": 104.1954,
        "default_lang": "zh",
        "base_risk": "High ESG Exposure (CSDDD Target)",
    },
    "SUPPLIER-ATACAMA-LITHIUM": {
        "name": "Atacama Lithium Corp",
        "zone": "SALT-FLATS-ZONE-C-CHILE",
        "country": "Chile",
        "lat": -23.6500,
        "lon": -68.3000,
        "default_lang": "es",
        "base_risk": "Moderate Environmental Scrutiny",
    },
    "SUPPLIER-KATANGA-COPPER": {
        "name": "Katanga Copper Alliance",
        "zone": "MINING-ZONE-F-DRC",
        "country": "Democratic Republic of the Congo",
        "lat": -10.6500,
        "lon": 26.5000,
        "default_lang": "fr",
        "base_risk": "Critical Human Rights Track (UFLPA & CSDDD Target)",
    },
    "SUPPLIER-QUEENSLAND-NICKEL": {
        "name": "Queensland Nickel Refinery",
        "zone": "LOGISTICS-ZONE-D-AUSTRALIA",
        "country": "Australia",
        "lat": -20.5500,
        "lon": 145.7507,
        "default_lang": "en",
        "base_risk": "Stable Operations (Routine Audit)",
    },
    "SUPPLIER-SUDBURY-SMELTING": {
        "name": "Sudbury Smelting Hub",
        "zone": "SMELTING-ZONE-B-CANADA",
        "country": "Canada",
        "lat": 46.4900,
        "lon": -81.0100,
        "default_lang": "en",
        "base_risk": "Stable Operations (Routine Audit)",
    },
}


def get_supplier(supplier_id: str) -> Dict[str, Any]:
    if supplier_id not in SUPPLIERS:
        raise KeyError(f"Unknown supplier: {supplier_id}")
    return SUPPLIERS[supplier_id]
