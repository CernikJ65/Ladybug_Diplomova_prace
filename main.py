"""
Main - Hlavní spouštěcí soubor pro solární analýzu
Jednoducho: jeden čas, top 10 střech, pouze Ladybug funkce
"""

from model_loader import load_model, validate_model
from roof_analyzer import analyze_all_roofs, print_roof_summary
from solar_calculator import (
    create_location, 
    create_sunpath, 
    calculate_sun_position,
    analyze_all_roofs_solar,
    find_top_roofs,
    print_top_roofs
)

def main():
    """
    Hlavní funkce - provede analýzu solárního potenciálu střech
    pro jeden konkrétní čas a vypíše top 10 střech.
    """
    
    print("="*60)
    print("SOLÁRNÍ ANALÝZA STŘECH - LADYBUG TOOLS")
    print("="*60)
    
    try:
        # 1. Načteme HBJSON model pomocí Honeybee
        print("\n1. NAČÍTÁNÍ MODELU")
        model = load_model()
        
        if not validate_model(model):
            return
        
        # 2. Najdeme střešní plochy pomocí Honeybee
        print("\n2. ANALÝZA STŘECH")
        roof_data = analyze_all_roofs(model)
        
        if not roof_data:
            print("Žádné střešní plochy k analýze!")
            return
        
        print_roof_summary(roof_data)
        
        # 3. Vytvoříme lokaci a sunpath pomocí Ladybug
        print("\n3. PŘÍPRAVA SOLÁRNÍ ANALÝZY")
        location = create_location()
        sunpath = create_sunpath(location)
        
        # 4. Vypočítáme pozici slunce pro konkrétní čas pomocí Ladybug
        # Letní slunovrat, poledne (nejlepší podmínky)
        sun = calculate_sun_position(sunpath, month=6, day=21, hour=12.0)
        
        # 5. Analyzujeme solární radiaci všech střech pomocí Ladybug clear sky modelu
        print("\n4. SOLÁRNÍ ANALÝZA")
        solar_results = analyze_all_roofs_solar(roof_data, sun, location)
        
        # 6. Najdeme a vypíšeme top 10 střech
        print("\n5. VÝSLEDKY")
        top_10_roofs = find_top_roofs(solar_results, top_n=10)
        print_top_roofs(top_10_roofs, "TOP 10 STŘECH S NEJVYŠŠÍ SOLÁRNÍ RADIACÍ")
        
        # Bonus: všechny střechy s radiací > 0
        active_roofs = [r for r in solar_results if r['solar_irradiance'] > 0]
        print(f"\nCelkem {len(active_roofs)} střech má solární radiaci > 0 W/m²")
        
        print("\n" + "="*60)
        print("ANALÝZA DOKONČENA")
        print("="*60)
        
    except Exception as e:
        print(f"\nCHYBA: {e}")
        print("Zkontrolujte, že máte správně nainstalované Ladybug Tools")
        print("a že existuje HBJSON soubor k analýze.")

if __name__ == "__main__":
    main()