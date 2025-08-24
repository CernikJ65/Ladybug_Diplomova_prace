"""
Energy Visualizer - Grafické zobrazení výsledků energetické analýzy
Jen dva užitečné grafy: tabulka místností + spotřeba vs. plocha
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import os

# Nastavení pro české prostředí
plt.rcParams['font.size'] = 10

class EnergyVisualizer:
    """
    Třída pro grafické zobrazení výsledků energetické analýzy.
    """
    
    def __init__(self, analysis_results: List[Dict[str, Any]]):
        """
        Inicializace s výsledky analýzy.
        
        Args:
            analysis_results: Seznam výsledků z BuildingEnergyAnalyzer
        """
        self.df = pd.DataFrame(analysis_results)
    
    def create_detailed_table_plot(self, save_path: str = None, show_plot: bool = True):
        """
        Vytvoří grafickou tabulku se VŠEMI místnostmi.
        
        Args:
            save_path: Cesta pro uložení grafu
            show_plot: Zda zobrazit graf
        """
        # VŠECHNY místnosti seřazené podle spotřeby
        display_df = self.df.sort_values('annual_consumption_kwh', ascending=False)[
            ['room_id', 'floor_number', 'floor_area_m2', 'annual_consumption_kwh', 'annual_cost_czk']
        ].copy()
        
        # Zaokrouhlení hodnot
        display_df['floor_area_m2'] = display_df['floor_area_m2'].round(1)
        display_df['annual_consumption_kwh'] = display_df['annual_consumption_kwh'].round(0).astype(int)
        display_df['annual_cost_czk'] = display_df['annual_cost_czk'].round(0).astype(int)
        
        # Vytvoření figure
        fig, ax = plt.subplots(figsize=(14, max(6, len(display_df) * 0.4)))
        ax.axis('tight')
        ax.axis('off')
        
        # Vytvoření tabulky
        table = ax.table(cellText=display_df.values,
                        colLabels=['Místnost', 'Podlaží', 'Plocha [m²]', 'Spotřeba [kWh/rok]', 'Náklady [CZK/rok]'],
                        cellLoc='center',
                        loc='center',
                        bbox=[0, 0, 1, 1])
        
        # Formátování tabulky
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        
        # Barevné hlavičky
        for i in range(len(display_df.columns)):
            table[(0, i)].set_facecolor('#4472C4')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Střídavé barvy řádků
        for i in range(1, len(display_df) + 1):
            for j in range(len(display_df.columns)):
                if i % 2 == 0:
                    table[(i, j)].set_facecolor('#F2F2F2')
        
        plt.title('PŘEHLED VŠECH MÍSTNOSTÍ', fontsize=14, fontweight='bold', pad=20)
        
        # Uložení nebo zobrazení
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Tabulka místností uložena do: {save_path}")
        
        if show_plot:
            plt.show()
        else:
            plt.close()
    
    def create_consumption_vs_area_plot(self, save_path: str = None, show_plot: bool = True):
        """
        Vytvoří graf spotřeba vs. plocha s trend linií.
        
        Args:
            save_path: Cesta pro uložení grafu  
            show_plot: Zda zobrazit graf
        """
        # Vytvoření figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Scatter plot
        ax.scatter(self.df['floor_area_m2'], self.df['annual_consumption_kwh'], 
                  color='steelblue', alpha=0.7, s=80)
        
        # Přidání popisků místností
        for idx, row in self.df.iterrows():
            ax.annotate(row['room_id'], 
                       (row['floor_area_m2'], row['annual_consumption_kwh']),
                       xytext=(5, 5), textcoords='offset points', 
                       fontsize=8, alpha=0.7)
        
        # Trend linie
        z = np.polyfit(self.df['floor_area_m2'], self.df['annual_consumption_kwh'], 1)
        p = np.poly1d(z)
        ax.plot(self.df['floor_area_m2'], p(self.df['floor_area_m2']), 
                "r--", alpha=0.8, linewidth=2, label=f'Trend: y = {z[0]:.1f}x + {z[1]:.1f}')
        
        ax.set_title('Jak roste spotřeba s plochou místnosti', fontsize=14, fontweight='bold')
        ax.set_xlabel('Plocha [m²]', fontsize=12)
        ax.set_ylabel('Spotřeba [kWh/rok]', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Uložení nebo zobrazení
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Graf spotřeba vs. plocha uložen do: {save_path}")
        
        if show_plot:
            plt.show()
        else:
            plt.close()
    
    def create_all_visualizations(self, output_dir: str = 'output/graphs'):
        """
        Vytvoří oba grafické výstupy.
        
        Args:
            output_dir: Složka pro uložení grafů
        """
        os.makedirs(output_dir, exist_ok=True)
        
        print("Vytvářím grafické výstupy...")
        
        # Tabulka místností
        self.create_detailed_table_plot(
            save_path=os.path.join(output_dir, 'table_all_rooms.png'),
            show_plot=False
        )
        
        # Graf spotřeba vs plocha
        self.create_consumption_vs_area_plot(
            save_path=os.path.join(output_dir, 'consumption_vs_area.png'),
            show_plot=False
        )
        
        print(f"Grafy uloženy do: {os.path.abspath(output_dir)}")
        print("\nSoubory:")
        print("- table_all_rooms.png")
        print("- consumption_vs_area.png")

def visualize_energy_results(analysis_results: List[Dict[str, Any]], 
                           output_dir: str = 'output/graphs',
                           show_plots: bool = True):
    """
    Hlavní funkce pro vytvoření grafických výstupů.
    
    Args:
        analysis_results: Výsledky z energy_analyzer
        output_dir: Složka pro uložení
        show_plots: Zda zobrazit grafy interaktivně
    """
    visualizer = EnergyVisualizer(analysis_results)
    
    if show_plots:
        # Interaktivní zobrazení
        visualizer.create_detailed_table_plot()
        visualizer.create_consumption_vs_area_plot()
    else:
        # Pouze uložení
        visualizer.create_all_visualizations(output_dir)

if __name__ == "__main__":
    # Test - načte výsledky z CSV pokud existuje
    try:
        df = pd.read_csv('output/energy_analysis_honeybee_standards.csv')
        results = df.to_dict('records')
        
        print("Načítám výsledky z CSV a vytvářím grafy...")
        visualize_energy_results(results, show_plots=True)
        
    except FileNotFoundError:
        print("CSV soubor s výsledky nebyl nalezen.")
        print("Nejprve spusťte energy_analyzer.py")