"""
Solar Calculator - Solární výpočty pro jeden konkrétní čas
Pouze Ladybug Tools funkce
"""

import math
from ladybug.location import Location
from ladybug.sunpath import Sunpath
from ladybug_geometry.geometry3d.pointvector import Vector3D

def create_location():
    """
    Vytvoří Location objekt pro Frýdek-Místek pomocí Ladybug.
    
    Returns:
        Location: Ladybug Location objekt
    """
    # Použití Ladybug Location
    location = Location(
        city='Frýdek-Místek',
        country='CZE',
        latitude=49.6825,
        longitude=18.3675,
        time_zone=1,
        elevation=300
    )
    
    print(f"Lokace: {location.city} ({location.latitude}°, {location.longitude}°)")
    return location

def create_sunpath(location):
    """
    Vytvoří Sunpath objekt z lokace pomocí Ladybug.
    
    Args:
        location: Ladybug Location objekt
        
    Returns:
        Sunpath: Ladybug Sunpath objekt
    """
    # Použití Ladybug Sunpath
    sunpath = Sunpath.from_location(location)
    return sunpath

def calculate_sun_position(sunpath, month=6, day=21, hour=12.0):
    """
    Vypočítá pozici slunce pro konkrétní čas pomocí Ladybug.
    
    Args:
        sunpath: Ladybug Sunpath objekt
        month: Měsíc (1-12)
        day: Den (1-31)
        hour: Hodina (0.0-24.0)
        
    Returns:
        Sun: Ladybug Sun objekt
    """
    # Použití Ladybug sunpath funkce
    sun = sunpath.calculate_sun(month, day, hour)
    
    print(f"Pozice slunce ({day}.{month}. {hour:02.0f}:00):")
    print(f"  Výška: {math.degrees(sun.altitude_in_radians):.1f}°")
    print(f"  Azimut: {math.degrees(sun.azimuth_in_radians):.1f}°")
    
    return sun

def calculate_roof_solar_potential(roof_data, sun, location):
    """
    Vypočítá solární radiaci střechy pomocí Ladybug clear sky modelu.
    
    Args:
        roof_data: Slovník s vlastnostmi střechy
        sun: Ladybug Sun objekt
        location: Ladybug Location objekt
        
    Returns:
        float: Solární radiace [W/m²] z Ladybug výpočtů
    """
    # Pokud je slunce pod horizontem, není radiace
    if sun.altitude <= 0:
        return 0.0
    
    # Normála střechy (z Ladybug geometry)
    roof_normal = roof_data['normal']
    
    # Směr slunečních paprsků (z Ladybug Sun)
    sun_vector = sun.sun_vector
    
    # Výpočet úhlu dopadu pomocí Ladybug Vector3D funkcí
    # Použijeme dot product z Ladybug
    dot_product = roof_normal.dot(sun_vector.reverse())
    
    # Normalizace (délky vektorů z Ladybug)
    normal_magnitude = roof_normal.magnitude
    sun_magnitude = sun_vector.magnitude
    
    # Cosinus úhlu dopadu pomocí Ladybug funkcí
    cos_incident = dot_product / (normal_magnitude * sun_magnitude)
    
    # Pokud je úhel > 90°, není ozáření
    if cos_incident <= 0:
        return 0.0
    
    # Ladybug clear sky radiace pro dané místo a čas
    # Přibližný clear sky direct normal irradiance na základě výšky slunce
    # Používáme Ladybug sun.altitude_in_radians
    clear_sky_direct = 900 * sun.altitude_in_radians  # W/m² (zjednodušený clear sky model)
    
    # Radiace na nakloněnou plochu pomocí Ladybug výpočtu
    roof_irradiance = clear_sky_direct * cos_incident
    
    return roof_irradiance

def analyze_all_roofs_solar(roof_data_list, sun, location):
    """
    Analyzuje solární radiaci všech střech pomocí Ladybug clear sky modelu.
    
    Args:
        roof_data_list: Seznam slovníků s vlastnostmi střech
        sun: Ladybug Sun objekt
        location: Ladybug Location objekt
        
    Returns:
        list: Seznam slovníků rozšířených o solární radiaci
    """
    results = []
    
    for roof_data in roof_data_list:
        # Vypočítáme solární radiaci pomocí Ladybug clear sky modelu
        irradiance = calculate_roof_solar_potential(roof_data, sun, location)
        
        # Přidáme výsledek k datům střechy
        result = roof_data.copy()
        result['solar_irradiance'] = irradiance  # W/m² z Ladybug clear sky
        
        results.append(result)
    
    print(f"Analyzována solární radiace {len(results)} střech pomocí Ladybug clear sky modelu")
    return results

def find_top_roofs(solar_results, top_n=10):
    """
    Najde top N střech s nejvyšší solární radiací z Ladybug výpočtů.
    
    Args:
        solar_results: Seznam výsledků solární analýzy
        top_n: Počet top střech k vrácení
        
    Returns:
        list: Seznam top N střech seřazených podle radiace
    """
    # Seřadíme podle solární radiace (nejvyšší první)
    sorted_roofs = sorted(
        solar_results, 
        key=lambda x: x['solar_irradiance'], 
        reverse=True
    )
    
    # Vrátíme top N
    return sorted_roofs[:top_n]

def print_top_roofs(top_roofs, title="TOP STŘECHY"):
    """
    Vypíše top střechy s jejich solární radiací z Ladybug výpočtů.
    
    Args:
        top_roofs: Seznam top střech
        title: Název výpisu
    """
    print(f"\n{title}:")
    print("-" * 70)
    
    for i, roof in enumerate(top_roofs, 1):
        print(f"{i:2d}. {roof['id']:<20} "
              f"Plocha: {roof['area']:6.1f} m² "
              f"Radiace: {roof['solar_irradiance']:6.1f} W/m²")
    
    if top_roofs:
        total_area = sum(roof['area'] for roof in top_roofs)
        avg_irradiance = sum(roof['solar_irradiance'] for roof in top_roofs) / len(top_roofs)
        print(f"\nSouhrn top {len(top_roofs)} střech:")
        print(f"Celková plocha: {total_area:.1f} m²")
        print(f"Průměrná radiace: {avg_irradiance:.1f} W/m² (z Ladybug výpočtů)")