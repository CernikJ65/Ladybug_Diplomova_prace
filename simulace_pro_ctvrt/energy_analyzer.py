"""
Energy Analyzer - Hlavní analyzátor energetické spotřeby
Využívá oficiální honeybee-energy standardy přes energy_config modul
+ GRAFICKÝ VÝSTUP místo jen textového
"""

import os
import pandas as pd
from typing import List, Dict, Any
from honeybee.model import Model
from energy_config import EnergyStandardsConfig

class BuildingEnergyAnalyzer:
    """
    Analyzátor energetické spotřeby využívající oficiální honeybee-energy standardy.
    """
    
    def __init__(self):
        """Inicializace analyzátoru s oficiálními standardy."""
        self.config = EnergyStandardsConfig()
        self.analysis_results = []
    
    def analyze_building_energy(self, model: Model) -> List[Dict[str, Any]]:
        """
        Analyzuje energetickou spotřebu všech budov v modelu pomocí honeybee standardů.
        
        Args:
            model: Honeybee Model objekt
            
        Returns:
            List: Seznam slovníků s výsledky analýzy
        """
        self.analysis_results = []
        
        for room in model.rooms:
            if not room.user_data:
                continue
            
            building_type = room.user_data.get('building_type', 'residential')
            has_roof = room.user_data.get('has_roof', False)
            floor_number = room.user_data.get('floor_number', 1)
            
            # Získání oficiálního honeybee standardu
            program_type, config = self.config.get_honeybee_program_type(building_type)
            
            # Výpočet pomocí honeybee vlastností
            floor_area = room.floor_area  # m²
            volume = room.volume         # m³
            
            # Výpočet spotřeby pomocí oficiálních honeybee parametrů
            if program_type:
                annual_consumption = self._calculate_consumption_from_standard(
                    program_type, floor_area, config['typical_kwh_m2_year']
                )
                lighting_kwh = program_type.lighting.watts_per_area * floor_area * 2000 / 1000
                equipment_kwh = 0
                if program_type.electric_equipment:
                    equipment_kwh = program_type.electric_equipment.watts_per_area * floor_area * 3000 / 1000
                heating_kwh = annual_consumption * 0.6  # 60% na vytápění
                gas_kwh = 0
                if program_type.gas_equipment:
                    gas_kwh = program_type.gas_equipment.watts_per_area * floor_area * 1500 / 1000
            else:
                # Fallback pro případy, kdy standard není dostupný
                annual_consumption = floor_area * config['typical_kwh_m2_year']
                lighting_kwh = floor_area * 8.0 * 2000 / 1000
                equipment_kwh = floor_area * 10.0 * 3000 / 1000  
                heating_kwh = annual_consumption * 0.6
                gas_kwh = 0
            
            # Výpočet nákladů
            annual_cost = self._calculate_annual_cost(
                lighting_kwh, equipment_kwh, heating_kwh, gas_kwh
            )
            
            result = {
                'room_id': room.identifier,
                'building_type': config['display_name'],
                'building_type_code': building_type,
                'floor_number': floor_number,
                'has_roof': has_roof,
                'floor_area_m2': round(floor_area, 1),
                'volume_m3': round(volume, 1),
                'annual_consumption_kwh': round(annual_consumption, 1),
                'lighting_kwh_year': round(lighting_kwh, 1),
                'equipment_kwh_year': round(equipment_kwh, 1),
                'heating_kwh_year': round(heating_kwh, 1),
                'gas_kwh_year': round(gas_kwh, 1),
                'annual_cost_czk': round(annual_cost, 0),
                'cost_per_m2_czk': round(annual_cost / floor_area, 0),
                'honeybee_standard': config.get('honeybee_type', 'fallback')
            }
            
            self.analysis_results.append(result)
        
        return self.analysis_results
    
    def _calculate_consumption_from_standard(self, program_type, floor_area: float, 
                                           typical_kwh_m2: float) -> float:
        """Výpočet spotřeby na základě honeybee standardu."""
        if not program_type:
            return floor_area * typical_kwh_m2
        
        # Součet všech zdrojů spotřeby podle honeybee standardu
        lighting_annual = program_type.lighting.watts_per_area * floor_area * 2000 / 1000
        equipment_annual = 0
        if program_type.electric_equipment:
            equipment_annual = program_type.electric_equipment.watts_per_area * floor_area * 3000 / 1000
        
        # Odhad celkové spotřeby (osvětlení + zařízení + vytápění/chlazení)
        total_consumption = (lighting_annual + equipment_annual) / 0.4  # předpokládáme 40% na osvětlení a zařízení
        
        return total_consumption
    
    def _calculate_annual_cost(self, lighting_kwh: float, equipment_kwh: float,
                             heating_kwh: float, gas_kwh: float) -> float:
        """Výpočet ročních nákladů podle českých cen energií."""
        return (
            lighting_kwh * self.config.energy_prices.electricity_kwh +
            equipment_kwh * self.config.energy_prices.electricity_kwh +
            heating_kwh * self.config.energy_prices.heating_kwh +
            gas_kwh * self.config.energy_prices.gas_kwh
        )
    
    def print_summary(self):
        """Vypíše přehledný souhrn energetické analýzy."""
        if not self.analysis_results:
            print("Žádné výsledky k zobrazení!")
            return
        
        df = pd.DataFrame(self.analysis_results)
        
        print("\n" + "="*80)
        print("ENERGETICKÁ ANALÝZA - HONEYBEE STANDARDY")
        print("="*80)
        
        # Celkový přehled
        total_area = df['floor_area_m2'].sum()
        total_consumption = df['annual_consumption_kwh'].sum()
        total_cost = df['annual_cost_czk'].sum()
        
        print(f"\nCELKOVÝ PŘEHLED:")
        print(f"Celková plocha: {total_area:,.1f} m²")
        print(f"Celková spotřeba: {total_consumption:,.0f} kWh/rok")
        print(f"Celkové náklady: {total_cost:,.0f} CZK/rok")
        print(f"Průměrné náklady: {total_cost/total_area:.0f} CZK/m²/rok")
        
        # Přehled použitých honeybee standardů
        print(f"\nPOUŽITÉ HONEYBEE STANDARDY:")
        standards_used = df.groupby(['building_type', 'honeybee_standard']).size()
        for (btype, standard), count in standards_used.items():
            print(f"  {btype}: {standard} ({count}x)")
        
        # Detailní tabulka (zkrácená)
        print(f"\nDETAILNÍ PŘEHLED (TOP 10):")
        print("-"*80)
        display_df = df[['room_id', 'building_type', 'floor_area_m2', 
                        'annual_consumption_kwh', 'annual_cost_czk']].head(10)
        print(display_df.to_string(index=False))
        print("-"*80)
    
    def create_graphs(self, output_dir: str = 'output/graphs'):
        """NOVÁ FUNKCE: Vytvoří grafické výstupy místo jen textové tabulky."""
        try:
            from energy_visualizer import EnergyVisualizer
            
            visualizer = EnergyVisualizer(self.analysis_results)
            visualizer.create_all_visualizations(output_dir)
            
            print(f"\n🎯 GRAFICKÉ VÝSTUPY VYTVOŘENY!")
            print(f"Složka: {os.path.abspath(output_dir)}")
            
        except ImportError:
            print("⚠ Chyba: energy_visualizer.py není dostupný")
            print("Pro grafické výstupy potřebujete matplotlib a seaborn:")
            print("pip install matplotlib seaborn")
    
    def save_results(self, output_dir: str = 'output'):
        """Uloží výsledky do CSV souboru."""
        if not self.analysis_results:
            print("Žádné výsledky k uložení!")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        df = pd.DataFrame(self.analysis_results)
        output_file = os.path.join(output_dir, 'energy_analysis_honeybee_standards.csv')
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"Výsledky uloženy do: {os.path.abspath(output_file)}")

def analyze_district_energy(hbjson_path: str) -> BuildingEnergyAnalyzer:
    """
    Provede energetickou analýzu celé čtvrti pomocí honeybee standardů.
    
    Args:
        hbjson_path: Cesta k HBJSON souboru
        
    Returns:
        BuildingEnergyAnalyzer: Analyzátor s výsledky
    """
    model = Model.from_hbjson(hbjson_path)
    analyzer = BuildingEnergyAnalyzer()
    analyzer.analyze_building_energy(model)
    return analyzer

if __name__ == "__main__":
    # Test na našem modelu
    model_path = os.path.join('output', 'ostrava_small_district.hbjson')
    
    if os.path.exists(model_path):
        print("Spouštím energetickou analýzu s honeybee standardy...")
        analyzer = analyze_district_energy(model_path)
        
        # Textový výstup (původní)
        analyzer.print_summary()
        analyzer.save_results()
        
        # NOVÉ: Grafický výstup
        analyzer.create_graphs()
        
    else:
        print(f"Model nenalezen: {model_path}")
        print("Nejprve spusťte create_small_district.py")