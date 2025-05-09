"""
Analýza solárního potenciálu pro město v Ostravě pomocí Ladybug Tools a Honeybee Radiance
"""
import os
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import pandas as pd

# Import Ladybug nástrojů
from ladybug.location import Location
from ladybug.sunpath import Sunpath
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.dt import DateTime
from ladybug.wea import Wea
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D

# Import Honeybee nástrojů pro práci s modelem
from honeybee.model import Model
from honeybee.shade import Shade

# Import Honeybee Radiance nástrojů - opravené importy
from honeybee_radiance.modifier.material.plastic import Plastic
from honeybee_radiance.modifier.material.glass import Glass

# Odstranění problematických importů - budeme implementovat alternativní řešení
# from honeybee_radiance.sky.certainilluminance import CertainIlluminanceLevel
# from honeybee_radiance.sky.cie import CIE

# Importy pro analýzu - využití dostupných tříd
from honeybee_radiance.sensorgrid import SensorGrid
from honeybee_radiance.sensorgrid import Sensor

# Načtení alternativních nástrojů, které mohou být dostupné
try:
    from honeybee_radiance_command.options.rtrace import RtraceOptions
except ImportError:
    # Vytvoříme vlastní zjednodušenou třídu, pokud není dostupná
    class RtraceOptions:
        def __init__(self):
            self.ab = 2
            self.ad = 1000
            self.as_param = 20
            self.ar = 300
            self.aa = 0.1

# Definice lokace Ostravy
OSTRAVA_LAT = 49.8209
OSTRAVA_LON = 18.2625
OSTRAVA_ELEVATION = 260  # nadmořská výška v metrech

def create_ostrava_location():
    """Vytvoří objekt lokace pro Ostravu."""
    return Location(
        city='Ostrava', 
        country='CZE', 
        latitude=OSTRAVA_LAT, 
        longitude=OSTRAVA_LON, 
        time_zone=1,  # časové pásmo (UTC+1)
        elevation=OSTRAVA_ELEVATION
    )

def load_hbjson_model(file_path):
    """Načte HBJSON model města."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"HBJSON soubor nenalezen: {file_path}")
    
    print(f"Načítám model z {file_path}...")
    with open(file_path, 'r') as f:
        model_dict = json.load(f)
    
    # Převedeme slovník na Honeybee Model
    model = Model.from_dict(model_dict)
    
    print(f"Model načten: {model.display_name}")
    print(f"Počet místností: {len(model.rooms)}")
    print(f"Počet stínících prvků: {len(model.shades)}")
    
    return model

def identify_roof_surfaces(model):
    """Identifikuje střešní plochy v modelu."""
    roof_shades = []
    
    # Hledáme stínící prvky, které představují střechy
    for shade in model.shades:
        if shade.user_data and 'type' in shade.user_data and shade.user_data['type'] == 'roof':
            roof_shades.append(shade)
    
    # Pokud nemáme žádné střechy jako stínící prvky, podíváme se na plochy místností
    if not roof_shades:
        for room in model.rooms:
            for face in room.faces:
                if face.type == 'RoofCeiling':
                    # Vytvoříme stínící prvek ze střešní plochy
                    roof_shade = Shade(
                        f"RoofShade_{face.identifier}",
                        face.geometry
                    )
                    roof_shade.user_data = {'type': 'roof', 'parent_room': room.identifier}
                    roof_shades.append(roof_shade)
    
    print(f"Nalezeno {len(roof_shades)} střešních ploch.")
    return roof_shades

def create_analysis_grid_from_roofs(roof_shades, grid_size=1.0):
    """Vytvoří mřížku testovacích bodů pro střešní plochy."""
    analysis_grids = []
    grid_names = {}  # Slovník pro uložení názvů mřížek
    sensor_vectors = {}  # Slovník pro uložení vektorů pro každý sensor
    
    for roof in roof_shades:
        # Vytvoříme test body pro střechu
        test_points = []
        test_vectors = []
        
        # Získáme geometrii střechy
        vertices = roof.geometry.vertices
        normal = roof.geometry.normal
        
        # Zjistíme hranice střechy
        min_x = min(v.x for v in vertices)
        max_x = max(v.x for v in vertices)
        min_y = min(v.y for v in vertices)
        max_y = max(v.y for v in vertices)
        
        # Vytvoříme mřížku testovacích bodů
        for x in np.arange(min_x + grid_size/2, max_x, grid_size):
            for y in np.arange(min_y + grid_size/2, max_y, grid_size):
                # Vytvoříme bod na rovině střechy
                point = Point3D(x, y, vertices[0].z)
                
                # Zkontrolujeme, zda bod leží uvnitř střechy
                if roof.geometry.is_point_on_face(point, tolerance=0.1):
                    test_points.append(point)
                    test_vectors.append(normal)
        
        if test_points:
            # Vytvoříme sensory
            sensors = [Sensor(point, vector) for point, vector in zip(test_points, test_vectors)]
            
            # Vytvoříme SensorGrid
            grid_name = f"Grid_{roof.identifier}"
            grid = SensorGrid(grid_name, sensors)
            
            # Místo přidání nového atributu, uložíme název do slovníku
            grid_names[id(grid)] = grid_name
            
            # Uložíme vektory pro každý sensor
            for i, sensor in enumerate(sensors):
                sensor_vectors[id(sensor)] = test_vectors[i]
            
            analysis_grids.append(grid)
    
    print(f"Vytvořeno {len(analysis_grids)} analýzních mřížek s celkem {sum(len(g.sensors) for g in analysis_grids)} body.")
    return analysis_grids, grid_names, sensor_vectors

def calculate_sun_vectors_and_hoys(location, analysis_period=None):
    """Vypočítá vektory slunce a hodiny v roce."""
    # Výchozí analýzní období (celý rok)
    if analysis_period is None:
        analysis_period = AnalysisPeriod()
    
    # Vytvoříme sunpath pro lokaci
    sunpath = Sunpath.from_location(location)
    
    # Získáme hodiny v roce a vektory slunce
    hoys = analysis_period.hoys
    sun_vectors = []
    
    for hoy in hoys:
        dt = DateTime.from_hoy(hoy)
        # Oprava volání - předání explicitních argumentů month, day, hour
        sun = sunpath.calculate_sun(month=dt.month, day=dt.day, hour=dt.hour)
        if sun.altitude > 0:  # Slunce nad horizontem
            sun_vectors.append(sun.sun_vector)
    
    print(f"Vypočteno {len(sun_vectors)} slunečních vektorů.")
    return sun_vectors, hoys

# Alternativní implementace pro CertainIlluminanceLevel
class SimpleSkyModel:
    """Jednoduchá náhrada za CertainIlluminanceLevel a CIE"""
    def __init__(self, illuminance=10000):
        self.illuminance = illuminance
        self.name = f"simple_sky_{illuminance}"
    
    def to_dict(self):
        return {
            "type": "SimpleSkyModel",
            "illuminance": self.illuminance
        }

def run_solar_access_analysis(model, roof_shades, analysis_grids, grid_names, sensor_vectors, location, output_dir='solar_analysis'):
    """Spustí analýzu přístupu slunce na střechy."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Vytvoříme analýzní období (celý rok)
    analysis_period = AnalysisPeriod()
    
    # Získáme vektory slunce a hodiny v roce
    sun_vectors, hoys = calculate_sun_vectors_and_hoys(location, analysis_period)
    
    # Vytvoříme Radiance parametry
    rad_params = RtraceOptions()
    rad_params.ab = 2  # ambient bounces
    rad_params.ad = 1000  # ambient divisions
    
    # Nastavení parametru 'as' pomocí update_from_string
    # 'as' je v Pythonu klíčové slovo, proto se k němu přistupuje jinak
    rad_params.update_from_string("-as 20")
    
    rad_params.ar = 300  # ambient resolution
    rad_params.aa = 0.1  # ambient accuracy
    
    # Vytvoříme jednoduchý model oblohy
    sky = SimpleSkyModel(10000)  # 10000 lux
    
    # POZNÁMKA: Pokud SolarAccessGridBased není dostupný, použijeme vlastní implementaci
    # Alternativní řešení: Vytvoříme Radiance model a scénu
    print("Připravuji Radiance model...")
    
    # Vytvoříme jednoduchý výpočet přístupu slunce
    results = []
    
    # Pro každou mřížku vytvoříme zjednodušenou analýzu
    for i, grid in enumerate(analysis_grids):
        # Hodnoty pro každý bod (procento hodin se sluncem)
        sun_hours = []
        
        # Použijeme název mřížky ze slovníku nebo jen index
        grid_name = grid_names.get(id(grid), f"Mřížka_{i+1}")
        print(f"Analyzuji mřížku {grid_name}...")
        
        # Pro každý sensor spočítáme přístup slunce (zjednodušená logika)
        for sensor in grid.sensors:
            # Získáme vektor směru ze slovníku
            direction = sensor_vectors.get(id(sensor))
            
            # Zde by normálně bylo volání Radiance, ale místo toho použijeme zjednodušený výpočet
            # Simulace založená na normále povrchu a vektoru slunce
            visible_sun_hours = 0
            for sun_vector in sun_vectors:
                # Úhel mezi normálou a vektorem slunce
                angle = direction.angle(sun_vector.reverse())
                # Pokud je úhel menší než 90°, povrch vidí slunce
                if angle < 90:
                    visible_sun_hours += 1
            
            # Procento hodin se sluncem
            percentage = (visible_sun_hours / len(sun_vectors)) * 100 if sun_vectors else 0
            sun_hours.append(percentage)
        
        # Přidáme výsledky pro tuto mřížku
        results.append(sun_hours)
    
    print(f"Analýza dokončena pro {len(results)} mřížek.")
    return results

def calculate_azimuth(normal_vector):
    """Vypočítá azimut vektoru (úhel od severu ve směru hodinových ručiček)."""
    # Projekce normálového vektoru do horizontální roviny
    projected_normal = Vector3D(normal_vector.x, normal_vector.y, 0)
    
    # Zkontrolujeme, zda projekce není nulový vektor (horizontální střecha)
    if abs(projected_normal.x) < 1e-6 and abs(projected_normal.y) < 1e-6:
        # Pro horizontální střechu vracíme výchozí azimut 0 (sever)
        return 0.0
    
    # Vektor směřující na sever
    north = Vector3D(0, 1, 0)
    
    # Úhel mezi vektory
    angle_rad = projected_normal.angle(north)
    angle_deg = angle_rad * 180 / np.pi
    
    # Určení kvadrantu a úprava úhlu pro měření ve směru hodinových ručiček od severu
    if normal_vector.x < 0:
        azimuth = 360 - angle_deg
    else:
        azimuth = angle_deg
    
    return azimuth

def analyze_solar_potential(analysis_results, roof_shades, location):
    """Analyzuje solární potenciál střešních ploch."""
    # Vytvoříme list pro výsledky
    solar_potential = []
    
    # Pro každou střechu a její výsledky
    for i, (shade, result) in enumerate(zip(roof_shades, analysis_results)):
        # Získáme geometrii střechy
        roof_geo = shade.geometry
        
        # Vypočítáme normálu plochy (vektor kolmý na plochu)
        normal_vector = roof_geo.normal
        
        # Vypočítáme sklon (úhel od horizontály)
        slope_angle = 90 - normal_vector.angle(Vector3D(0, 0, 1)) * 180 / np.pi
        
        # Vypočítáme orientaci (azimut - úhel od severu ve směru hodinových ručiček)
        azimuth = calculate_azimuth(normal_vector)
        
        # Vypočítáme plochu střechy
        area = roof_geo.area
        
        # Získáme průměrný počet hodin slunečního svitu
        if result:
            avg_sunlight_hours = np.mean(result) * 24 * 365 / 100  # Převod z procent na hodiny za rok
        else:
            avg_sunlight_hours = 0
        
        # Vypočítáme koeficient vhodnosti pro solární panely (0-1)
        # Optimální sklon pro ČR je cca 35° a orientace na jih (azimut 180°)
        slope_factor = 1 - min(abs(slope_angle - 35), 90) / 90
        azimuth_factor = 1 - min(abs(azimuth - 180), 180) / 180
        
        # Faktor slunečního svitu (normalizovaný na max 4380 hodin ročně - polovina roku)
        sunlight_factor = min(avg_sunlight_hours / 4380, 1)
        
        # Kombinovaný faktor vhodnosti (0-1)
        suitability = (0.3 * slope_factor + 0.3 * azimuth_factor + 0.4 * sunlight_factor)
        
        # Odhadneme roční produkci energie
        # Roční ozáření v Ostravě je přibližně 1050-1100 kWh/m² horizontální plochy
        # Použijeme váženou hodnotu podle sklonu a orientace
        annual_insolation = 1050 * suitability
        
        # Odhadovaná produkce energie (předpokládáme účinnost panelů 20%)
        energy_production = annual_insolation * area * 0.2  # kWh/rok
        
        # Uložíme informace o střeše
        roof_type = shade.user_data.get('roof_type', 'unknown') if shade.user_data else 'unknown'
        
        solar_potential.append({
            'id': shade.identifier,
            'type': roof_type,
            'area': area,
            'slope': slope_angle,
            'azimuth': azimuth,
            'avg_sunlight_hours': avg_sunlight_hours, 
            'suitability': suitability,
            'annual_insolation': annual_insolation,
            'energy_production': energy_production,
            'geometry': roof_geo,
            'normal': normal_vector
        })
    
    # Seřadíme výsledky podle vhodnosti (sestupně)
    solar_potential.sort(key=lambda x: x['suitability'], reverse=True)
    
    return solar_potential

def visualize_solar_potential(model, solar_results, output_dir='solar_analysis'):
    """Vizualizuje solární potenciál na 3D modelu."""
    # Vytvoříme normalizovanou barevnou škálu podle vhodnosti (0-1)
    norm = Normalize(vmin=0, vmax=1)
    cmap = cm.get_cmap('RdYlGn')  # červená (špatné) -> žlutá (střední) -> zelená (dobré)
    
    # Vytvoříme 3D vizualizaci
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Nejprve přidáme ostatní geometrii modelu (stěny, podlahy) průhledně
    for room in model.rooms:
        for face in room.faces:
            if face.type != 'RoofCeiling':  # vše kromě střech
                vertices = [point.to_array() for point in face.vertices]
                poly = Poly3DCollection([vertices], alpha=0.1)
                poly.set_facecolor('lightgray')
                poly.set_edgecolor('gray')
                ax.add_collection3d(poly)
    
    # Poté přidáme střechy s barevným kódováním podle potenciálu
    for result in solar_results:
        vertices = [point.to_array() for point in result['geometry'].vertices]
        poly = Poly3DCollection([vertices], alpha=0.9)
        
        # Nastavíme barvu podle vhodnosti
        color = cmap(norm(result['suitability']))
        poly.set_facecolor(color)
        poly.set_edgecolor('black')
        ax.add_collection3d(poly)
    
    # Najdeme hranice modelu
    all_points = []
    for room in model.rooms:
        for face in room.faces:
            all_points.extend([v.to_array() for v in face.vertices])
    all_points = np.array(all_points)
    
    # Nastavíme limity os
    if len(all_points) > 0:
        ax.set_xlim([np.min(all_points[:, 0]), np.max(all_points[:, 0])])
        ax.set_ylim([np.min(all_points[:, 1]), np.max(all_points[:, 1])])
        ax.set_zlim([np.min(all_points[:, 2]), np.max(all_points[:, 2])])
    
    # Popisky os
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    
    # Přidáme barevnou škálu
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.1)
    cbar.set_label('Vhodnost pro solární panely')
    
    # Titulek
    plt.title('Solární potenciál střešních ploch v Ostravě')
    
    # Uložíme obrázek
    output_file = os.path.join(output_dir, 'solar_potential_3d.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"3D vizualizace uložena do {output_file}")
    
    # Zobrazíme graf
    plt.show()

def generate_solar_report(solar_results, output_dir='solar_analysis'):
    """Generuje podrobnou zprávu o solárním potenciálu."""
    # Vytvoříme dataframe pro lepší analýzu
    df = pd.DataFrame(solar_results)
    
    # Odstraníme geometrické sloupce pro snazší zpracování
    analysis_df = df.drop(['geometry', 'normal'], axis=1)
    
    # Uložíme data do CSV souboru
    csv_path = os.path.join(output_dir, 'solar_analysis_results.csv')
    analysis_df.to_csv(csv_path, index=False)
    print(f"Výsledky analýzy uloženy do {csv_path}")
    
    # Vytvoříme souhrn podle typu střechy
    roof_type_summary = analysis_df.groupby('type').agg({
        'area': 'sum',
        'suitability': 'mean',
        'energy_production': 'sum'
    }).sort_values('suitability', ascending=False)
    
    # Uložíme souhrn
    summary_path = os.path.join(output_dir, 'roof_type_summary.csv')
    roof_type_summary.to_csv(summary_path)
    
    # Vykreslíme grafy
    # 1. Histogram vhodnosti
    plt.figure(figsize=(10, 6))
    plt.hist(analysis_df['suitability'], bins=10, color='skyblue', edgecolor='black')
    plt.title('Distribuce vhodnosti střech pro solární panely')
    plt.xlabel('Vhodnost (0-1)')
    plt.ylabel('Počet střech')
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(output_dir, 'suitability_histogram.png'), dpi=300)
    
    # 2. Graf potenciální produkce podle typu střechy
    plt.figure(figsize=(12, 8))
    roof_type_summary['energy_production'].plot(kind='bar', color='orange')
    plt.title('Potenciální roční výroba energie podle typu střechy')
    plt.xlabel('Typ střechy')
    plt.ylabel('Roční výroba energie (kWh)')
    plt.xticks(rotation=45)
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'energy_production_by_roof_type.png'), dpi=300)
    
    # Vytvoříme textovou zprávu s doporučeními
    with open(os.path.join(output_dir, 'solar_recommendations.txt'), 'w') as f:
        f.write("DOPORUČENÍ PRO INSTALACI SOLÁRNÍCH PANELŮ V OSTRAVĚ\n")
        f.write("==========================================\n\n")
        
        f.write("Top 5 střech s nejvyšším potenciálem:\n")
        top_roofs = analysis_df.sort_values('energy_production', ascending=False).head(5)
        for i, row in enumerate(top_roofs.itertuples(), 1):
            f.write(f"{i}. ID: {row.id}, Typ: {row.type}, Plocha: {row.area:.1f} m², ")
            f.write(f"Sklon: {row.slope:.1f}°, Azimut: {row.azimuth:.1f}°, ")
            f.write(f"Potenciální výroba: {row.energy_production:.1f} kWh/rok\n")
        
        f.write("\nSouhrn podle typu střechy:\n")
        for roof_type, row in roof_type_summary.iterrows():
            f.write(f"- {roof_type}: Celková plocha {row['area']:.1f} m², ")
            f.write(f"Průměrná vhodnost {row['suitability']:.2f}, ")
            f.write(f"Potenciální výroba {row['energy_production']:.1f} kWh/rok\n")
        
        f.write("\nVŠEOBECNÁ DOPORUČENÍ PRO OSTRAVU:\n")
        f.write("1. Preferujte střechy s vhodností nad 0.7 (optimální orientace a sklon)\n")
        f.write("2. Pro ploché střechy použijte konstrukce s optimálním sklonem 30-35°\n")
        f.write("3. Pultové a sedlové střechy orientované na jih mají nejvyšší potenciál\n")
        f.write("4. Valbové a mansardové střechy jsou vhodné při správné orientaci jižní části\n")
        f.write("5. Pro střechy s nižší vhodností zvažte použití účinnějších panelů\n")
        
        # Klimatické podmínky Ostravy
        f.write("\nKLIMATICKÉ PODMÍNKY OSTRAVY:\n")
        f.write("- Průměrné roční sluneční ozáření: 1050-1100 kWh/m²\n")
        f.write("- Počet slunečných dnů za rok: přibližně 150-160\n")
        f.write("- Průměrná teplota v létě: 18-22°C (optimální pro fotovoltaiku)\n")
        f.write("- Průměrná teplota v zimě: -2 až 2°C (snížená účinnost panelů)\n")
        f.write("- Časté znečištění ovzduší může snížit účinnost o 5-15%\n")
    
    print(f"Zpráva s doporučeními vygenerována: {os.path.join(output_dir, 'solar_recommendations.txt')}")
    return analysis_df

def main():
    """Hlavní funkce pro analýzu solárního potenciálu."""
    # Nastavení výstupního adresáře
    output_dir = 'solar_analysis_ostrava'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Vytvoření lokace pro Ostravu
    location = create_ostrava_location()
    print(f"Lokace: {location.city}, {location.country}")
    print(f"Souřadnice: {location.latitude}, {location.longitude}")
    
    # Načtení modelu města
    model_path = os.path.join('output', 'city_model_solar.hbjson')
    if not os.path.exists(model_path):
        # Zkusíme alternativní cestu
        model_path = os.path.join('output', 'city_model.hbjson')
    
    try:
        model = load_hbjson_model(model_path)
    except Exception as e:
        print(f"Chyba při načítání modelu: {e}")
        print("Vytvořte model města pomocí create_city_hbjson.py")
        return
    
    # Identifikace střešních ploch
    roof_shades = identify_roof_surfaces(model)
    
    # Vytvoření analýzních mřížek
    analysis_grids, grid_names, sensor_vectors = create_analysis_grid_from_roofs(roof_shades, grid_size=1.0)
    
    # Spuštění analýzy přístupu slunce
    solar_access_results = run_solar_access_analysis(model, roof_shades, analysis_grids, grid_names, sensor_vectors, location, output_dir)
    
    # Analýza solárního potenciálu
    print("Analyzuji solární potenciál střech...")
    solar_results = analyze_solar_potential(solar_access_results, roof_shades, location)
    
    # Vizualizace výsledků
    print("Generuji vizualizace...")
    visualize_solar_potential(model, solar_results, output_dir)
    
    # Generování zprávy
    print("Generuji zprávu s doporučeními...")
    analysis_df = generate_solar_report(solar_results, output_dir)
    
    print("\nAnalýza dokončena!")
    print(f"Všechny výsledky byly uloženy do adresáře: {os.path.abspath(output_dir)}")
    
    # Zobrazení souhrnu
    print("\nSOUHRN ANALÝZY:")
    print(f"Celkový počet analyzovaných střech: {len(solar_results)}")
    
    suitable_roofs = analysis_df[analysis_df['suitability'] > 0.7]
    print(f"Počet vysoce vhodných střech (vhodnost > 0.7): {len(suitable_roofs)}")
    
    total_potential = analysis_df['energy_production'].sum()
    print(f"Celkový potenciál výroby energie: {total_potential:.2f} kWh/rok")
    
    # Přibližný počet domácností, které lze zásobovat (průměrná spotřeba 3500 kWh/rok)
    households = total_potential / 3500
    print(f"To odpovídá roční spotřebě přibližně {households:.1f} domácností")

if __name__ == "__main__":
    main()