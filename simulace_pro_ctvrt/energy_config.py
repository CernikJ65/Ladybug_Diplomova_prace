"""
Energy Configuration - Konfigurace energetických typů a cen
Používá oficiální honeybee-energy-standards knihovnu
"""

from dataclasses import dataclass
from typing import Dict, Any
from honeybee_energy.lib.programtypes import building_program_type_by_identifier, program_type_by_identifier

@dataclass
class EnergyPrices:
    """Ceny energií v České republice (CZK)"""
    electricity_kwh: float = 6.50  # CZK/kWh
    gas_kwh: float = 2.80  # CZK/kWh  
    heating_kwh: float = 1.50  # CZK/kWh (dálkové topení)

class EnergyStandardsConfig:
    """
    Konfigurace využívající oficiální honeybee-energy standardy.
    Mapuje naše typy budov na ASHRAE/DOE standardy.
    """
    
    def __init__(self):
        self.building_mapping = self._create_building_mapping()
        self.energy_prices = EnergyPrices()
    
    def _create_building_mapping(self) -> Dict[str, Dict[str, Any]]:
        """
        Mapuje naše typy budov na officiální honeybee-energy standardy.
        
        Returns:
            Dict: Mapování typů budov na standardy
        """
        return {
            'residential': {
                'honeybee_type': 'MidriseApartment',  # ASHRAE standard
                'display_name': 'Bytový dům',
                'template': '90.1-2013',
                'space_type': 'MidriseApartment',
                'typical_kwh_m2_year': 120
            },
            'office': {
                'honeybee_type': 'MediumOffice',
                'display_name': 'Kancelářská budova', 
                'template': '90.1-2013',
                'space_type': 'MediumOffice - OpenOffice',
                'typical_kwh_m2_year': 140
            },
            'commercial': {
                'honeybee_type': 'StripMall',
                'display_name': 'Obchodní budova',
                'template': '90.1-2013', 
                'space_type': 'StripMall',
                'typical_kwh_m2_year': 160
            }
        }
    
    def get_honeybee_program_type(self, building_type: str):
        """
        Získá oficiální honeybee ProgramType pro daný typ budovy.
        
        Args:
            building_type: Náš typ budovy ('residential', 'office', 'commercial')
            
        Returns:
            ProgramType: Oficiální honeybee ProgramType objekt
        """
        if building_type not in self.building_mapping:
            building_type = 'residential'  # Fallback
        
        config = self.building_mapping[building_type]
        
        try:
            # Použití oficiální honeybee-energy funkce!
            program_type = building_program_type_by_identifier(config['honeybee_type'])
            return program_type, config
        except Exception as e:
            print(f"Chyba při načítání standardu {config['honeybee_type']}: {e}")
            # VYLEPŠENO: Používá oficiální pattern z ladybug-tools/honeybee-grasshopper-energy
            try:
                program_type = program_type_by_identifier(config['honeybee_type'])
                return program_type, config
            except ValueError:
                # Finální fallback
                try:
                    program_type = program_type_by_identifier('MediumOffice')
                    return program_type, self.building_mapping['office']
                except:
                    return None, config
    
    def get_building_config(self, building_type: str) -> Dict[str, Any]:
        """Vrátí konfiguraci pro daný typ budovy."""
        return self.building_mapping.get(building_type, self.building_mapping['residential'])
    
    def list_available_standards(self) -> Dict[str, str]:
        """
        Vypíše dostupné honeybee standardy pro ladění.
        
        Returns:
            Dict: Dostupné standardy
        """
        available = {}
        for building_type, config in self.building_mapping.items():
            try:
                program_type = building_program_type_by_identifier(config['honeybee_type'])
                available[building_type] = f"✓ {config['honeybee_type']} - {program_type.display_name}"
            except:
                available[building_type] = f"✗ {config['honeybee_type']} - NEDOSTUPNÉ"
        
        return available

def test_standards():
    """Test dostupnosti honeybee-energy standardů."""
    config = EnergyStandardsConfig()
    
    print("TESTOVÁNÍ HONEYBEE-ENERGY STANDARDŮ:")
    print("="*50)
    
    available = config.list_available_standards()
    for building_type, status in available.items():
        print(f"{building_type:12}: {status}")
    
    print("\nDETAIL - MediumOffice standard:")
    try:
        program_type, config_detail = config.get_honeybee_program_type('office')
        if program_type:
            print(f"  Název: {program_type.display_name}")
            print(f"  Osvětlení: {program_type.lighting.watts_per_area:.1f} W/m²")
            print(f"  Lidé: {program_type.people.people_per_area:.3f} lidí/m²")
            if program_type.electric_equipment:
                print(f"  Zařízení: {program_type.electric_equipment.watts_per_area:.1f} W/m²")
    except Exception as e:
        print(f"  Chyba: {e}")

if __name__ == "__main__":
    test_standards()