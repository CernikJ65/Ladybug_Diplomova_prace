"""
Model Loader - Načítání HBJSON modelu pomocí Honeybee
Pouze Ladybug Tools funkce
"""

import os
from honeybee.model import Model

def load_model(file_path=None):
    """
    Načte HBJSON model pomocí Honeybee.
    
    Args:
        file_path: Cesta k HBJSON souboru (pokud None, hledá automaticky)
        
    Returns:
        Model: Honeybee model objekt
    """
    if file_path is None:
        file_path = find_model_file()
    
    if not file_path:
        raise FileNotFoundError("HBJSON model nebyl nalezen!")
    
    print(f"Načítám model: {file_path}")
    
    # Použití Honeybee funkce pro načtení
    model = Model.from_hbjson(file_path)
    
    print(f"Model načten: {model.display_name}")
    print(f"Počet místností: {len(model.rooms)}")
    
    return model

def find_model_file():
    """
    Najde HBJSON soubor v běžných lokacích.
    
    Returns:
        str: Cesta k nalezenému souboru nebo None
    """
    search_paths = [
        'output/city_model_solar.hbjson',
        'output/city_model.hbjson',
        'city_model.hbjson',
        'model.hbjson'
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            return path
    
    return None

def validate_model(model):
    """
    Validuje model pro analýzu.
    
    Args:
        model: Honeybee model
        
    Returns:
        bool: True pokud je model validní
    """
    if len(model.rooms) == 0:
        print("Model neobsahuje žádné místnosti!")
        return False
    
    total_faces = sum(len(room.faces) for room in model.rooms)
    if total_faces == 0:
        print("Model neobsahuje žádné plochy!")
        return False
    
    print(f"Model validován: {total_faces} ploch")
    return True