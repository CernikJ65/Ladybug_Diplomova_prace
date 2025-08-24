"""
Vytvoření malé čtvrti pomocí oficiálních Honeybee funkcí
Používá Room.from_polyface3d() pro automatické rozpoznání typů ploch
"""

import os
import math
from honeybee.model import Model
from honeybee.room import Room
from ladybug_geometry.geometry3d.pointvector import Point3D
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.polyface import Polyface3D

def create_simple_box_polyface(x_min, y_min, x_max, y_max, z_min, z_max):
    """
    Vytvoří základní kvádr jako Polyface3D pomocí Ladybug geometrie.
    
    Args:
        x_min, y_min, x_max, y_max: Rozměry v XY
        z_min, z_max: Výška
        
    Returns:
        Polyface3D: Uzavřený kvádr
    """
    # 8 vrcholů kvádru
    pts = [
        Point3D(x_min, y_min, z_min),  # 0
        Point3D(x_max, y_min, z_min),  # 1
        Point3D(x_max, y_max, z_min),  # 2
        Point3D(x_min, y_max, z_min),  # 3
        Point3D(x_min, y_min, z_max),  # 4
        Point3D(x_max, y_min, z_max),  # 5
        Point3D(x_max, y_max, z_max),  # 6
        Point3D(x_min, y_max, z_max)   # 7
    ]
    
    # 6 ploch kvádru (pořadí vrcholů pro správnou orientaci normál)
    faces = [
        Face3D([pts[0], pts[1], pts[2], pts[3]]),  # Spodní
        Face3D([pts[4], pts[7], pts[6], pts[5]]),  # Horní
        Face3D([pts[0], pts[4], pts[5], pts[1]]),  # Jižní
        Face3D([pts[1], pts[5], pts[6], pts[2]]),  # Východní
        Face3D([pts[2], pts[6], pts[7], pts[3]]),  # Severní
        Face3D([pts[3], pts[7], pts[4], pts[0]])   # Západní
    ]
    
    # Vytvoření Polyface3D
    polyface = Polyface3D.from_faces(faces, tolerance=0.01)
    return polyface

def create_gable_roof_polyface(x_min, y_min, x_max, y_max, z_base, height_step, roof_angle=35):
    """
    Vytvoří budovu se sedlovou střechou jako Polyface3D.
    
    Args:
        x_min, y_min, x_max, y_max: Rozměry
        z_base: Základní výška
        height_step: Výška patra
        roof_angle: Úhel střechy ve stupních
        
    Returns:
        Polyface3D: Budova se sedlovou střechou
    """
    wall_height = z_base + height_step
    slope_rad = math.radians(roof_angle)
    width = y_max - y_min
    ridge_height = wall_height + (width / 2) * math.tan(slope_rad)
    ridge_y = (y_min + y_max) / 2
    
    # Vrcholy budovy se sedlovou střechou
    pts = [
        # Základní 4 body podlahy
        Point3D(x_min, y_min, z_base),     # 0
        Point3D(x_max, y_min, z_base),     # 1  
        Point3D(x_max, y_max, z_base),     # 2
        Point3D(x_min, y_max, z_base),     # 3
        # 4 body na úrovni stěn
        Point3D(x_min, y_min, wall_height), # 4
        Point3D(x_max, y_min, wall_height), # 5
        Point3D(x_max, y_max, wall_height), # 6
        Point3D(x_min, y_max, wall_height), # 7
        # 2 body na hřebenu střechy
        Point3D(x_min, ridge_y, ridge_height), # 8
        Point3D(x_max, ridge_y, ridge_height)  # 9
    ]
    
    # Plochy budovy se sedlovou střechou
    faces = [
        Face3D([pts[0], pts[1], pts[2], pts[3]]),  # Podlaha
        Face3D([pts[0], pts[4], pts[5], pts[1]]),  # Jižní stěna
        Face3D([pts[1], pts[5], pts[9], pts[8], pts[4], pts[0], pts[3], pts[7], pts[6], pts[2]]), # Složitější - obě štíty a stěny
        Face3D([pts[2], pts[6], pts[7], pts[3]]),  # Severní stěna
        Face3D([pts[4], pts[8], pts[9], pts[5]]),  # Jižní střešní rovina
        Face3D([pts[7], pts[6], pts[9], pts[8]])   # Severní střešní rovina
    ]
    
    # Jednodušší přístup - vytvoříme každou plochu zvlášť
    faces = [
        Face3D([pts[0], pts[1], pts[2], pts[3]]),       # Podlaha
        Face3D([pts[0], pts[4], pts[5], pts[1]]),       # Jižní stěna  
        Face3D([pts[1], pts[5], pts[9], pts[8], pts[4], pts[0]]), # Východní štít (6 bodů)
        Face3D([pts[2], pts[6], pts[7], pts[3]]),       # Severní stěna
        Face3D([pts[3], pts[7], pts[8]]),               # Západní štít (trojúhelník)
        Face3D([pts[4], pts[8], pts[9], pts[5]]),       # Jižní střecha
        Face3D([pts[7], pts[6], pts[9], pts[8]])        # Severní střecha
    ]
    
    # Opravím - jednoduše použiji triangulaci
    faces = []
    # Podlaha
    faces.append(Face3D([pts[0], pts[1], pts[2], pts[3]]))
    # Stěny
    faces.append(Face3D([pts[0], pts[4], pts[5], pts[1]]))  # Jih
    faces.append(Face3D([pts[2], pts[6], pts[7], pts[3]]))  # Sever
    # Štíty jako trojúhelníky
    faces.append(Face3D([pts[1], pts[5], pts[9]]))
    faces.append(Face3D([pts[1], pts[9], pts[8]]))
    faces.append(Face3D([pts[1], pts[8], pts[4]]))
    faces.append(Face3D([pts[3], pts[7], pts[8]]))
    faces.append(Face3D([pts[3], pts[8], pts[9]]))  
    faces.append(Face3D([pts[3], pts[9], pts[6]]))
    # Střešní plochy
    faces.append(Face3D([pts[4], pts[8], pts[9], pts[5]]))  # Jižní střecha
    faces.append(Face3D([pts[7], pts[6], pts[9], pts[8]]))  # Severní střecha
    
    try:
        polyface = Polyface3D.from_faces(faces, tolerance=0.01)
        return polyface
    except:
        # Fallback - použiji základní kvádr
        return create_simple_box_polyface(x_min, y_min, x_max, y_max, z_base, z_base + height_step)

def create_shed_roof_polyface(x_min, y_min, x_max, y_max, z_base, height_step, roof_angle=25):
    """
    Vytvoří budovu s pultovou střechou jako Polyface3D.
    """
    slope_rad = math.radians(roof_angle)
    depth = y_max - y_min
    height_diff = depth * math.tan(slope_rad)
    
    # 8 vrcholů s pultovou střechou
    pts = [
        Point3D(x_min, y_min, z_base),                      # 0
        Point3D(x_max, y_min, z_base),                      # 1
        Point3D(x_max, y_max, z_base),                      # 2
        Point3D(x_min, y_max, z_base),                      # 3
        Point3D(x_min, y_min, z_base + height_step),       # 4 - nižší
        Point3D(x_max, y_min, z_base + height_step),       # 5 - nižší
        Point3D(x_max, y_max, z_base + height_step + height_diff), # 6 - vyšší
        Point3D(x_min, y_max, z_base + height_step + height_diff)  # 7 - vyšší
    ]
    
    faces = [
        Face3D([pts[0], pts[1], pts[2], pts[3]]),  # Podlaha
        Face3D([pts[0], pts[4], pts[5], pts[1]]),  # Jižní stěna (nízká)
        Face3D([pts[1], pts[5], pts[6], pts[2]]),  # Východní stěna (lichoběžník)
        Face3D([pts[2], pts[6], pts[7], pts[3]]),  # Severní stěna (vysoká)
        Face3D([pts[3], pts[7], pts[4], pts[0]]),  # Západní stěna (lichoběžník)
        Face3D([pts[4], pts[7], pts[6], pts[5]])   # Pultová střecha
    ]
    
    try:
        polyface = Polyface3D.from_faces(faces, tolerance=0.01)
        return polyface
    except:
        return create_simple_box_polyface(x_min, y_min, x_max, y_max, z_base, z_base + height_step)

def create_hip_roof_polyface(x_min, y_min, x_max, y_max, z_base, height_step, roof_angle=30):
    """
    Vytvoří budovu s valbovou střechou (zjednodušenou) jako Polyface3D.
    """
    wall_height = z_base + height_step
    slope_rad = math.radians(roof_angle)
    width = min(x_max - x_min, y_max - y_min)
    ridge_height = wall_height + (width / 4) * math.tan(slope_rad)
    
    # Vrchol ve středu
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    apex = Point3D(center_x, center_y, ridge_height)
    
    # Základní body
    base_pts = [
        Point3D(x_min, y_min, z_base),     # 0
        Point3D(x_max, y_min, z_base),     # 1
        Point3D(x_max, y_max, z_base),     # 2
        Point3D(x_min, y_max, z_base),     # 3
        Point3D(x_min, y_min, wall_height), # 4
        Point3D(x_max, y_min, wall_height), # 5
        Point3D(x_max, y_max, wall_height), # 6
        Point3D(x_min, y_max, wall_height)  # 7
    ]
    
    faces = [
        Face3D([base_pts[0], base_pts[1], base_pts[2], base_pts[3]]), # Podlaha
        Face3D([base_pts[0], base_pts[4], base_pts[5], base_pts[1]]), # Jižní stěna
        Face3D([base_pts[1], base_pts[5], base_pts[6], base_pts[2]]), # Východní stěna
        Face3D([base_pts[2], base_pts[6], base_pts[7], base_pts[3]]), # Severní stěna
        Face3D([base_pts[3], base_pts[7], base_pts[4], base_pts[0]]), # Západní stěna
        # 4 trojúhelníkové střešní plochy
        Face3D([base_pts[4], base_pts[5], apex]), # Jižní střecha
        Face3D([base_pts[5], base_pts[6], apex]), # Východní střecha
        Face3D([base_pts[6], base_pts[7], apex]), # Severní střecha
        Face3D([base_pts[7], base_pts[4], apex])  # Západní střecha
    ]
    
    try:
        polyface = Polyface3D.from_faces(faces, tolerance=0.01)
        return polyface
    except:
        return create_simple_box_polyface(x_min, y_min, x_max, y_max, z_base, z_base + height_step)

def create_ostrava_district():
    """
    Vytvoří malou čtvrť pomocí oficiálních Honeybee funkcí.
    
    Returns:
        Model: Honeybee Model objekt
    """
    model = Model('Ostrava_Small_District')
    
    # Definice budov s různými typy střech
    buildings = [
        {
            'name': 'ResidentialBuilding_01',
            'x_min': 0, 'y_min': 0, 'x_max': 12, 'y_max': 8,
            'height': 9, 'floors': 3, 'roof_type': 'gable'
        },
        {
            'name': 'OfficeBuilding_01', 
            'x_min': 20, 'y_min': 0, 'x_max': 30, 'y_max': 15,
            'height': 12, 'floors': 4, 'roof_type': 'flat'
        },
        {
            'name': 'ResidentialBuilding_02',
            'x_min': 0, 'y_min': 15, 'x_max': 15, 'y_max': 25, 
            'height': 6, 'floors': 2, 'roof_type': 'hip'
        },
        {
            'name': 'CommercialBuilding_01',
            'x_min': 25, 'y_min': 20, 'x_max': 35, 'y_max': 30,
            'height': 4, 'floors': 1, 'roof_type': 'shed'
        }
    ]
    
    # Vytvoření budov
    for building in buildings:
        floor_height_step = building['height'] / building['floors']
        
        # Každé patro jako samostatná místnost
        for floor in range(building['floors']):
            room_name = f"{building['name']}_Floor{floor+1}"
            floor_height = floor * floor_height_step
            is_top_floor = (floor == building['floors'] - 1)
            
            # Vytvoření geometrie podle typu střechy (jen pro horní patro)
            if is_top_floor:
                if building['roof_type'] == 'gable':
                    polyface = create_gable_roof_polyface(
                        building['x_min'], building['y_min'],
                        building['x_max'], building['y_max'],
                        floor_height, floor_height_step
                    )
                    # Pro sedlovou střechu použijeme menší roof_angle aby se střecha správně rozpoznala
                    roof_angle = 45
                elif building['roof_type'] == 'shed':
                    polyface = create_shed_roof_polyface(
                        building['x_min'], building['y_min'],
                        building['x_max'], building['y_max'],
                        floor_height, floor_height_step
                    )
                    roof_angle = 50
                elif building['roof_type'] == 'hip':
                    polyface = create_hip_roof_polyface(
                        building['x_min'], building['y_min'],
                        building['x_max'], building['y_max'],
                        floor_height, floor_height_step
                    )
                    roof_angle = 45
                else: # flat
                    polyface = create_simple_box_polyface(
                        building['x_min'], building['y_min'],
                        building['x_max'], building['y_max'],
                        floor_height, floor_height + floor_height_step
                    )
                    roof_angle = 60  # Standardní hodnota
            else:
                # Vnitřní patra - použijeme standardní kvádr
                polyface = create_simple_box_polyface(
                    building['x_min'], building['y_min'],
                    building['x_max'], building['y_max'],
                    floor_height, floor_height + floor_height_step
                )
                roof_angle = 60  # Standard
            
            # KLÍČOVÉ: Použijeme Room.from_polyface3d() pro automatické rozpoznání ploch!
            try:
                room = Room.from_polyface3d(
                    room_name, 
                    polyface,
                    roof_angle=roof_angle,
                    floor_angle=130
                )
                
                # Přidáme user_data
                room.user_data = {
                    'building_type': building['name'].split('_')[0].lower(),
                    'floor_number': floor + 1,
                    'total_floors': building['floors'],
                    'roof_type': building['roof_type'],
                    'has_roof': is_top_floor
                }
                
                model.add_room(room)
                
            except Exception as e:
                print(f"Chyba při vytváření místnosti {room_name}: {e}")
                # Fallback - použijeme Room.from_box()
                try:
                    room = Room.from_box(
                        room_name,
                        width=building['x_max'] - building['x_min'],
                        depth=building['y_max'] - building['y_min'],
                        height=floor_height_step,
                        origin=Point3D(building['x_min'], building['y_min'], floor_height)
                    )
                    room.user_data = {
                        'building_type': building['name'].split('_')[0].lower(),
                        'floor_number': floor + 1,
                        'total_floors': building['floors'],
                        'roof_type': 'flat',  # Fallback
                        'has_roof': is_top_floor
                    }
                    model.add_room(room)
                except Exception as e2:
                    print(f"Fallback také selhal pro {room_name}: {e2}")
    
    print(f"Model vytvořen s {len(model.rooms)} místnostmi")
    print("Typy střech vytvořené pomocí Honeybee automatického rozpoznání ploch")
    return model

def save_district_model(output_dir='output'):
    """
    Vytvoří a uloží malou čtvrť jako HBJSON.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Vytvoření modelu pomocí oficiálních Honeybee funkcí
    model = create_ostrava_district()
    
    # Uložení
    output_file = os.path.join(output_dir, 'ostrava_small_district.hbjson')
    model.to_hbjson(output_file)
    
    print(f"Model uložen do: {os.path.abspath(output_file)}")
    print(f"\nInformace o modelu:")
    print(f"Název: {model.display_name}")
    print(f"Počet místností: {len(model.rooms)}")
    
    # Analýza typů střech rozpoznaných Honeybee
    roof_faces = []
    for room in model.rooms:
        if room.user_data and room.user_data.get('has_roof', False):
            for face in room.faces:
                if 'RoofCeiling' in str(face.type):
                    roof_faces.append({
                        'room': room.display_name,
                        'roof_type': room.user_data.get('roof_type', 'unknown'),
                        'area': face.area
                    })
    
    print(f"\nRozpoznané střešní plochy:")
    roof_type_stats = {}
    for roof in roof_faces:
        rtype = roof['roof_type']
        if rtype not in roof_type_stats:
            roof_type_stats[rtype] = {'count': 0, 'area': 0}
        roof_type_stats[rtype]['count'] += 1
        roof_type_stats[rtype]['area'] += roof['area']
    
    for rtype, stats in roof_type_stats.items():
        print(f"- {rtype}: {stats['count']} ploch, {stats['area']:.1f} m²")
    
    return output_file

if __name__ == "__main__":
    save_district_model()