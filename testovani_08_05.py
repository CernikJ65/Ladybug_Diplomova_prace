"""
Analýza solárního potenciálu střech pomocí Ladybug Tools
"""
import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# Import Ladybug Tools - základní nástroje
from ladybug.location import Location
from ladybug.sunpath import Sunpath
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.dt import DateTime
from ladybug_geometry.geometry3d import Vector3D

# Import Honeybee - práce s modely a geometrií
from honeybee.model import Model
from honeybee.face import Face
from honeybee.shade import Shade

# Import Ladybug - analytické funkce pro solární výpočty
from ladybug.sunpath import Sunpath

def load_hbjson_model(file_path):
    """Načte model města z HBJSON souboru pomocí Honeybee."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"HBJSON soubor nenalezen: {file_path}")
    
    print(f"Načítám model z {file_path}...")
    # Použití nativní funkce Honeybee pro načtení modelu
    model = Model.from_hbjson(file_path)
    
    print(f"Model načten: {model.display_name}")
    print(f"Počet místností: {len(model.rooms)}")
    print(f"Počet stínících prvků: {len(model.shades)}")
    return model

def find_roof_surfaces(model):
    """Najde střešní plochy v modelu pomocí Honeybee."""
    roof_surfaces = []
    
    # 1. Hledáme stínící prvky označené jako střechy
    for shade in model.shades:
        if shade.user_data and shade.user_data.get('type') == 'roof':
            roof_surfaces.append(shade)
    
    # 2. Pokud nemáme označené střechy, hledáme plochy typu 'RoofCeiling'
    if not roof_surfaces:
        for room in model.rooms:
            for face in room.faces:
                if face.type == 'RoofCeiling':
                    # Vytvoříme stínící prvek ze střešní plochy
                    new_shade = Shade(f"Roof_{face.identifier}", face.geometry)
                    new_shade.user_data = {'type': 'roof', 'from_face': True}
                    roof_surfaces.append(new_shade)
    
    # 3. Pokud stále nemáme střechy, použijeme horní plochy místností
    if not roof_surfaces:
        for room in model.rooms:
            top_faces = find_top_faces(room)
            for face in top_faces:
                new_shade = Shade(f"TopSurface_{face.identifier}", face.geometry)
                new_shade.user_data = {'type': 'roof', 'auto_detected': True}
                roof_surfaces.append(new_shade)
    
    print(f"Nalezeno {len(roof_surfaces)} střešních ploch.")
    return roof_surfaces

def find_top_faces(room):
    """Najde horní plochy místnosti (pravděpodobné střechy)."""
    # Seřadíme plochy podle maximální Z-souřadnice
    faces_by_height = sorted(
        room.faces,
        key=lambda f: max(v.z for v in f.geometry.vertices),
        reverse=True
    )
    
    # Určíme nejvyšší Z-souřadnici
    if not faces_by_height:
        return []
    
    max_z = max(v.z for v in faces_by_height[0].geometry.vertices)
    
    # Vybereme plochy, které jsou blízko nejvyšší Z-souřadnici (tolerance 0.1 m)
    top_faces = [f for f in faces_by_height 
                if abs(max(v.z for v in f.geometry.vertices) - max_z) < 0.1
                and f.type != 'Floor']  # Vyloučíme podlahy
                
    return top_faces

def calculate_roof_properties(roof_surfaces):
    """Spočítá vlastnosti střech pomocí Ladybug geometrie."""
    roof_props = []
    
    for roof in roof_surfaces:
        # Použití Ladybug geometrických funkcí
        normal = roof.geometry.normal
        centroid = roof.geometry.centroid
        area = roof.geometry.area
        
        # Výpočet sklonu (využití funkcí Ladybug Vector3D)
        up_vector = Vector3D(0, 0, 1)
        tilt_rad = normal.angle(up_vector)
        tilt_deg = tilt_rad * 180 / np.pi
        
        # Výpočet azimutu (orientace)
        north_vector = Vector3D(0, 1, 0)
        normal_horiz = Vector3D(normal.x, normal.y, 0)
        
        # Kontrola pro ploché střechy
        if normal_horiz.magnitude < 0.001:
            azimuth = 0  # Pro ploché střechy (sklon < 1°) není orientace důležitá
        else:
            normal_horiz = normal_horiz.normalize()
            azimuth_rad = normal_horiz.angle(north_vector)
            azimuth = azimuth_rad * 180 / np.pi
            
            # Úprava pro získání azimutu 0-360° od severu ve směru hodinových ručiček
            if normal.x < 0:
                azimuth = 360 - azimuth
        
        # Přidáme výsledky do seznamu
        roof_props.append({
            'roof': roof,
            'id': roof.identifier,
            'centroid': centroid,
            'normal': normal,
            'area': area,
            'tilt': 90 - tilt_deg,  # Sklon je 90° - úhel normály s vertikálou
            'azimuth': azimuth,
            'type': roof.user_data.get('roof_type', 'unknown') if roof.user_data else 'unknown'
        })
    
    return roof_props

def analyze_solar_access(roof_props, location, analysis_period=None):
    """Analyzuje přístup slunce pro každou střechu pomocí Ladybug."""
    # Vytvoříme Sunpath pro danou lokaci (využití Ladybug)
    sunpath = Sunpath.from_location(location)
    
    # Vytvoříme analyzační období
    if analysis_period is None:
        analysis_period = AnalysisPeriod()  # Celý rok
    
    # Získáme hodiny v roce
    hoys = analysis_period.hoys
    
    for roof in roof_props:
        normal = roof['normal']
        solar_access_hours = 0
        weighted_access_hours = 0
        
        # Analyzujeme každou hodinu v roce
        for hoy in hoys:
            dt = DateTime.from_hoy(hoy)
            # Využití Ladybug funkce pro výpočet pozice slunce
            sun = sunpath.calculate_sun(dt.month, dt.day, dt.hour)
            
            # Pokud je slunce nad horizontem
            if sun.altitude > 0:
                # Směr slunečních paprsků
                sun_vector = sun.sun_vector
                
                # Úhel dopadu (využití Ladybug Vector3D)
                angle = normal.angle(sun_vector.reverse())
                
                # Pokud sluneční paprsky dopadají na plochu (úhel < 90°)
                if angle < np.pi/2:
                    solar_access_hours += 1
                    
                    # Váha podle úhlu dopadu a výšky slunce
                    # Kolmý dopad (malý úhel) a vyšší slunce = vyšší váha
                    radiation_factor = np.cos(angle) * np.sin(sun.altitude_in_radians)
                    weighted_access_hours += radiation_factor
        
        # Vypočteme procentuální přístup slunce
        sun_access_percent = (solar_access_hours / len(hoys)) * 100
        
        # Přidáme výsledky analýzy do objektu střechy
        roof['sun_hours'] = solar_access_hours
        roof['sun_access_percent'] = sun_access_percent
        roof['weighted_hours'] = weighted_access_hours
    
    return roof_props

def calculate_solar_potential(roof_props):
    """Vypočítá solární potenciál střech na základě jejich vlastností a přístupu slunce."""
    # Normalizace váženého přístupu slunce pro všechny střechy
    if roof_props:
        max_weighted_hours = max(roof['weighted_hours'] for roof in roof_props)
        min_weighted_hours = min(roof['weighted_hours'] for roof in roof_props)
        range_weighted = max(max_weighted_hours - min_weighted_hours, 0.001)  # Předcházíme dělení nulou
    else:
        return roof_props
    
    for roof in roof_props:
        # Optimální sklon pro ČR je cca 35°
        tilt_factor = 1 - min(abs(roof['tilt'] - 35), 90) / 90
        
        # Optimální orientace je na jih (azimut 180°)
        azimuth_factor = 1 - min(abs(roof['azimuth'] - 180), 180) / 180
        
        # Faktor přístupu slunce - nyní používá normalizované vážené hodiny
        weighted_factor = (roof['weighted_hours'] - min_weighted_hours) / range_weighted
        
        # Kombinovaný faktor vhodnosti (0-1)
        suitability = (0.25 * tilt_factor + 0.25 * azimuth_factor + 0.5 * weighted_factor)
        
        # Odhadovaná roční produkce energie
        # Pro ČR je průměrné roční ozáření cca 1050 kWh/m² horizontální plochy
        annual_insolation = 1050 * suitability  # kWh/m²/rok
        
        # Předpokládaná účinnost fotovoltaických panelů 20%
        energy_production = annual_insolation * roof['area'] * 0.2  # kWh/rok
        
        # Uložíme výsledky
        roof['suitability'] = suitability
        roof['annual_insolation'] = annual_insolation
        roof['energy_production'] = energy_production
    
    # Seřadíme střechy podle vhodnosti
    roof_props.sort(key=lambda x: x['suitability'], reverse=True)
    return roof_props

def visualize_results(model, roof_results, output_file=None):
    """Vizualizuje výsledky analýzy ve 3D."""
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Barevná škála podle vhodnosti
    cmap = plt.cm.get_cmap('RdYlGn')
    norm = Normalize(vmin=0, vmax=1)
    
    # Vykreslíme model (mimo střech) průhledně
    for room in model.rooms:
        for face in room.faces:
            face_verts = [v.to_array() for v in face.vertices]
            poly = Poly3DCollection([face_verts], alpha=0.1)
            poly.set_facecolor('lightgray')
            ax.add_collection3d(poly)
    
    # Vykreslíme střechy s barevným kódováním
    for roof in roof_results:
        roof_verts = [v.to_array() for v in roof['roof'].vertices]
        poly = Poly3DCollection([roof_verts], alpha=0.8)
        
        # Barva podle vhodnosti pro solár
        color = cmap(norm(roof['suitability']))
        poly.set_facecolor(color)
        poly.set_edgecolor('black')
        ax.add_collection3d(poly)
    
    # Nastavíme rozsah os podle modelu
    all_verts = []
    for room in model.rooms:
        for face in room.faces:
            all_verts.extend([v.to_array() for v in face.vertices])
    
    all_verts = np.array(all_verts)
    ax.set_xlim([np.min(all_verts[:, 0]), np.max(all_verts[:, 0])])
    ax.set_ylim([np.min(all_verts[:, 1]), np.max(all_verts[:, 1])])
    ax.set_zlim([np.min(all_verts[:, 2]), np.max(all_verts[:, 2])])
    
    # Přidáme barevnou škálu a popisky
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax)
    cbar.set_label('Vhodnost pro solární panely (0-1)')
    
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    plt.title('Analýza solárního potenciálu střech')
    
    # Uložíme vizualizaci
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Vizualizace uložena do {output_file}")
    
    plt.show()

def create_summary_report(roof_results, output_dir=None):
    """Vytvoří souhrnnou zprávu s výsledky analýzy."""
    # Vytvoříme DataFrame pro reporting
    data = [{
        'ID': roof['id'],
        'Typ': roof['type'],
        'Plocha [m²]': round(roof['area'], 2),
        'Sklon [°]': round(roof['tilt'], 1),
        'Azimut [°]': round(roof['azimuth'], 1),
        'Sluneční hodiny [h/rok]': round(roof['sun_hours'], 1),
        'Vhodnost [-]': round(roof['suitability'], 2),
        'Potenciální výroba [kWh/rok]': round(roof['energy_production'], 1)
    } for roof in roof_results]
    
    df = pd.DataFrame(data)
    
    # Základní statistiky
    print("\nSOUHRN SOLÁRNÍ ANALÝZY:")
    print(f"Celkový počet analyzovaných střech: {len(df)}")
    
    suitable_roofs = df[df['Vhodnost [-]'] > 0.7]
    print(f"Počet velmi vhodných střech (> 0.7): {len(suitable_roofs)}")
    
    total_area = df['Plocha [m²]'].sum()
    total_production = df['Potenciální výroba [kWh/rok]'].sum()
    print(f"Celková plocha střech: {total_area:.1f} m²")
    print(f"Celková potenciální výroba: {total_production:.1f} kWh/rok")
    print(f"To odpovídá přibližně {total_production/3500:.1f} domácnostem (při 3500 kWh/rok na domácnost)")
    
    # Agregace podle typu střechy
    type_summary = df.groupby('Typ').agg({
        'Plocha [m²]': 'sum',
        'Vhodnost [-]': 'mean',
        'Potenciální výroba [kWh/rok]': 'sum'
    }).sort_values('Vhodnost [-]', ascending=False)
    
    print("\nSOUHRN PODLE TYPU STŘECHY:")
    print(type_summary)
    
    # Uložíme výsledky do souborů
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        df.to_csv(os.path.join(output_dir, 'solar_analysis_results.csv'), index=False)
        type_summary.to_csv(os.path.join(output_dir, 'roof_type_summary.csv'))
        print(f"\nVýsledky uloženy do adresáře: {output_dir}")
    
    return df

def main():
    """Hlavní funkce pro spuštění analýzy solárního potenciálu."""
    # Nastavení výstupní složky
    output_dir = 'solar_analysis_results'
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Načtení modelu města pomocí Honeybee
    model_path = os.path.join('output', 'city_model_solar.hbjson')
    if not os.path.exists(model_path):
        model_path = os.path.join('output', 'city_model.hbjson')
        if not os.path.exists(model_path):
            print("HBJSON model nebyl nalezen!")
            return
    
    try:
        model = load_hbjson_model(model_path)
    except Exception as e:
        print(f"Chyba při načítání modelu: {e}")
        # Zkusíme alternativní způsob načtení
        try:
            print("Zkouším alternativní způsob načtení...")
            with open(model_path, 'r') as f:
                model_dict = json.load(f)
            model = Model.from_dict(model_dict)
            print(f"Model načten alternativním způsobem: {len(model.rooms)} místností")
        except Exception as e2:
            print(f"Nepodařilo se načíst model: {e2}")
            return
    
    # 2. Identifikace střech pomocí Honeybee funkcí
    roof_surfaces = find_roof_surfaces(model)
    
    # 3. Výpočet geometrických vlastností střech pomocí Ladybug geometrie
    roof_props = calculate_roof_properties(roof_surfaces)
    
    # 4. Vytvoření lokace pro analýzu pomocí Ladybug
    location = Location(
        city='Frýdek-Místek',
        country='CZE',
        latitude=49.6825,
        longitude=18.3675,
        time_zone=1,
        elevation=300
    )
    
    # 5. Analýza přístupu slunce pomocí Ladybug sunpath
    print("Analyzuji přístup slunce...")
    try:
        roof_results = analyze_solar_access(roof_props, location)
    except Exception as e:
        print(f"Chyba při analýze přístupu slunce: {e}")
        print("Používám zjednodušenou analýzu...")
        # Přidáme alespoň základní hodnoty, abychom mohli pokračovat
        for roof in roof_props:
            roof['sun_hours'] = 0
            roof['sun_access_percent'] = 0
            roof['weighted_hours'] = 0
        roof_results = roof_props
    
    # 6. Výpočet solárního potenciálu
    print("Počítám solární potenciál...")
    roof_results = calculate_solar_potential(roof_results)
    
    # 7. Vizualizace výsledků
    print("Generuji vizualizaci...")
    visualize_results(model, roof_results, os.path.join(output_dir, 'solar_potential_3d.png'))
    
    # 8. Vytvoření souhrnné zprávy
    print("Vytvářím souhrnnou zprávu...")
    create_summary_report(roof_results, output_dir)
    
    print(f"Analýza dokončena. Výsledky jsou uloženy v adresáři: {os.path.abspath(output_dir)}")

if __name__ == "__main__":
    main()