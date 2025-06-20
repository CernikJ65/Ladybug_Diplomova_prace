"""
Roof Analyzer - Hledání střešních ploch
Pouze Honeybee funkce
"""

from honeybee.model import Model
from honeybee.face import Face

def find_roof_faces(model):
    """
    Najde střešní plochy v modelu pomocí Honeybee.
    
    Args:
        model: Honeybee model
        
    Returns:
        list: Seznam Face objektů představujících střechy
    """
    roof_faces = []
    
    # Projdeme všechny místnosti v modelu
    for room in model.rooms:
        # Projdeme všechny plochy v místnosti
        for face in room.faces:
            # Použijeme Honeybee vlastnost typu plochy
            if str(face.type) == 'RoofCeiling':
                roof_faces.append(face)
    
    print(f"Nalezeno {len(roof_faces)} střešních ploch typu RoofCeiling")
    return roof_faces

def get_roof_properties(roof_face):
    """
    Získá základní vlastnosti střechy pomocí Honeybee geometrie.
    
    Args:
        roof_face: Honeybee Face objekt
        
    Returns:
        dict: Slovník s vlastnostmi střechy
    """
    # Použijeme Honeybee geometry vlastnosti
    geometry = roof_face.geometry
    
    # Ladybug geometry funkce
    area = geometry.area
    normal = geometry.normal
    centroid = geometry.centroid
    vertices = geometry.vertices
    
    return {
        'id': roof_face.identifier,
        'face': roof_face,
        'geometry': geometry,
        'area': area,
        'normal': normal,
        'centroid': centroid,
        'vertices': vertices
    }

def analyze_all_roofs(model):
    """
    Analyzuje všechny střešní plochy v modelu.
    
    Args:
        model: Honeybee model
        
    Returns:
        list: Seznam slovníků s vlastnostmi všech střech
    """
    # Najdeme střešní plochy
    roof_faces = find_roof_faces(model)
    
    if not roof_faces:
        print("Nebyly nalezeny žádné střešní plochy!")
        return []
    
    # Analyzujeme každou střechu
    roof_data = []
    for roof_face in roof_faces:
        properties = get_roof_properties(roof_face)
        roof_data.append(properties)
    
    print(f"Analyzováno {len(roof_data)} střech")
    return roof_data

def print_roof_summary(roof_data):
    """
    Vypíše souhrn analyzovaných střech.
    
    Args:
        roof_data: Seznam slovníků s vlastnostmi střech
    """
    if not roof_data:
        return
    
    total_area = sum(roof['area'] for roof in roof_data)
    
    print(f"\nSOUHRN STŘECH:")
    print(f"Počet střech: {len(roof_data)}")
    print(f"Celková plocha: {total_area:.1f} m²")
    print(f"Průměrná plocha: {total_area/len(roof_data):.1f} m²")
    
    # Největší střecha
    largest_roof = max(roof_data, key=lambda x: x['area'])
    print(f"Největší střecha: {largest_roof['id']} ({largest_roof['area']:.1f} m²)")