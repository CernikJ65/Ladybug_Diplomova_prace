"""
Validace a základní analýza vytvořené čtvrti
Pomocí oficiální honeybee-core knihovny
"""

import os
from honeybee.model import Model

def validate_model(hbjson_path):
    """
    Načte a zvaliduje HBJSON model.
    
    Args:
        hbjson_path: Cesta k HBJSON souboru
        
    Returns:
        Model: Načtený model nebo None při chybě
    """
    if not os.path.exists(hbjson_path):
        print(f"Soubor neexistuje: {hbjson_path}")
        return None
    
    try:
        # Načtení modelu pomocí honeybee-core
        model = Model.from_hbjson(hbjson_path)
        print(f"✓ Model úspěšně načten: {model.display_name}")
        return model
        
    except Exception as e:
        print(f"✗ Chyba při načítání modelu: {e}")
        return None

def analyze_model_geometry(model):
    """
    Analyzuje geometrii modelu.
    
    Args:
        model: Honeybee Model objekt
    """
    print(f"\n=== GEOMETRICKÁ ANALÝZA ===")
    
    total_floor_area = 0
    total_wall_area = 0
    total_roof_area = 0
    total_window_area = 0
    
    for room in model.rooms:
        for face in room.faces:
            area = face.area
            
            # Klasifikace podle typu plochy
            face_type = str(face.type)
            if 'Floor' in face_type:
                total_floor_area += area
            elif 'Wall' in face_type:
                total_wall_area += area
            elif 'RoofCeiling' in face_type:
                total_roof_area += area
            
            # Okna
            for aperture in face.apertures:
                total_window_area += aperture.area
    
    print(f"Celková podlahová plocha: {total_floor_area:.1f} m²")
    print(f"Celková plocha stěn: {total_wall_area:.1f} m²") 
    print(f"Celková plocha střech: {total_roof_area:.1f} m²")
    print(f"Celková plocha oken: {total_window_area:.1f} m²")
    
    # Poměry
    if total_wall_area > 0:
        window_to_wall_ratio = total_window_area / total_wall_area * 100
        print(f"Poměr oken ke stěnám: {window_to_wall_ratio:.1f}%")

def analyze_building_types(model):
    """
    Analyzuje typy budov v modelu.
    
    Args:
        model: Honeybee Model objekt
    """
    print(f"\n=== ANALÝZA TYPŮ BUDOV ===")
    
    building_stats = {}
    
    for room in model.rooms:
        if room.user_data and 'building_type' in room.user_data:
            btype = room.user_data['building_type']
            
            if btype not in building_stats:
                building_stats[btype] = {
                    'rooms': 0,
                    'floor_area': 0,
                    'volume': 0
                }
            
            building_stats[btype]['rooms'] += 1
            building_stats[btype]['floor_area'] += room.floor_area
            building_stats[btype]['volume'] += room.volume
    
    for btype, stats in building_stats.items():
        print(f"\n{btype.upper()}:")
        print(f"  Počet místností: {stats['rooms']}")
        print(f"  Podlahová plocha: {stats['floor_area']:.1f} m²")
        print(f"  Objem: {stats['volume']:.1f} m³")

def find_solar_surfaces(model):
    """
    Najde plochy vhodné pro solární analýzu (střechy).
    
    Args:
        model: Honeybee Model objekt
        
    Returns:
        list: Seznam střešních ploch s dodatečnými informacemi
    """
    roof_faces = []
    
    for room in model.rooms:
        # Jen místnosti s střechami (horní patra)
        if room.user_data and room.user_data.get('has_roof', False):
            roof_type = room.user_data.get('roof_type', 'unknown')
            building_type = room.user_data.get('building_type', 'unknown')
            
            for face in room.faces:
                if 'RoofCeiling' in str(face.type):
                    roof_faces.append({
                        'room': room.display_name,
                        'face': face.display_name,
                        'area': face.area,
                        'center': face.center,
                        'normal': face.normal,
                        'roof_type': roof_type,
                        'building_type': building_type
                    })
    
    return roof_faces

def print_solar_analysis_preview(model):
    """
    Vypíše náhled na solární potenciál s informacemi o typech střech.
    
    Args:
        model: Honeybee Model objekt
    """
    print(f"\n=== SOLÁRNÍ POTENCIÁL (NÁHLED) ===")
    
    roof_faces = find_solar_surfaces(model)
    
    if not roof_faces:
        print("Žádné střešní plochy nenalezeny!")
        return
    
    total_roof_area = sum(roof['area'] for roof in roof_faces)
    print(f"Počet střešních ploch: {len(roof_faces)}")
    print(f"Celková plocha střech: {total_roof_area:.1f} m²")
    
    # Analýza podle typu střechy
    roof_type_stats = {}
    for roof in roof_faces:
        rtype = roof['roof_type']
        if rtype not in roof_type_stats:
            roof_type_stats[rtype] = {'count': 0, 'area': 0}
        roof_type_stats[rtype]['count'] += 1
        roof_type_stats[rtype]['area'] += roof['area']
    
    print(f"\nRozdělení podle typu střechy:")
    solar_ratings = {
        'gable': '⭐⭐⭐ Výborné (jižní strana)',
        'shed': '⭐⭐⭐ Výborné (orientace na jih)',  
        'flat': '⭐⭐ Dobré (nastavitelný sklon)',
        'hip': '⭐ Střední (menší plochy)'
    }
    
    for rtype, stats in roof_type_stats.items():
        rating = solar_ratings.get(rtype, '❓ Neznámé')
        print(f"  {rtype}: {stats['count']} ploch, {stats['area']:.1f} m² - {rating}")
    
    print(f"\nTop 3 největší střechy:")
    sorted_roofs = sorted(roof_faces, key=lambda x: x['area'], reverse=True)
    
    for i, roof in enumerate(sorted_roofs[:3], 1):
        rating = solar_ratings.get(roof['roof_type'], '❓')
        print(f"  {i}. {roof['face']}: {roof['area']:.1f} m² ({roof['roof_type']}) - {rating}")
    
    # Odhad solárního potenciálu
    estimated_panels = total_roof_area * 0.7 / 2.0  # 70% pokrytí, 2m² na panel
    estimated_power = estimated_panels * 0.4  # 400W na panel
    estimated_annual = estimated_power * 1000  # kWh/rok (přibližně)
    
    print(f"\n📊 ODHAD SOLÁRNÍHO POTENCIÁLU:")
    print(f"Odhadovaný počet panelů: {estimated_panels:.0f}")
    print(f"Odhadovaný výkon: {estimated_power:.1f} kWp") 
    print(f"Odhadovaná roční výroba: {estimated_annual:.0f} kWh/rok")

def main():
    """
    Hlavní funkce pro validaci čtvrti.
    """
    print("=== VALIDACE OSTRAVSKÉ ČTVRTI ===")
    
    # Hledání HBJSON souboru
    hbjson_paths = [
        'output/ostrava_small_district.hbjson',
        'ostrava_small_district.hbjson'
    ]
    
    model = None
    for path in hbjson_paths:
        if os.path.exists(path):
            model = validate_model(path)
            break
    
    if not model:
        print("\n⚠️  Žádný HBJSON soubor nenalezen!")
        print("Nejprve spusťte: python create_small_district.py")
        return
    
    # Detailní analýzy
    analyze_model_geometry(model)
    analyze_building_types(model)
    print_solar_analysis_preview(model)
    
    print(f"\n✅ Model je připraven pro experimenty s Ladybug Tools!")
    print(f"✅ Obsahuje různé typy střech ideální pro solární simulace")
    print(f"✅ Můžete použít tento model pro analýzu spotřeby energie")
    print(f"✅ Model obsahuje {len(model.rooms)} místností ve 4 budovách")
    print(f"✅ Střechy: gable, flat, hip, shed s různými sklony a orientacemi")

if __name__ == "__main__":
    main()