from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.polyface import Polyface3D
from honeybee.model import Model
from honeybee.room import Room
from honeybee.face import Face
from honeybee.aperture import Aperture
from honeybee.shade import Shade
import honeybee.writer as writer
# Importujeme potřebné moduly pro Radiance vlastnosti
from honeybee_radiance.modifier.material import Plastic, Glass, Metal
import random
import math
import json
import os
import uuid

def create_flat_roof(footprint, height, roof_thickness=0.3, slope=0):
    """Vytvoří plochou střechu s možností mírného sklonu pro odvod vody."""
    # Pro reálnější ploché střechy přidáme mírný sklon
    roof_pts = []
    
    # Najdeme centrální bod půdorysu
    center_x = sum(pt.x for pt in footprint) / len(footprint)
    center_y = sum(pt.y for pt in footprint) / len(footprint)
    
    for pt in footprint:
        # Vypočítáme vzdálenost od centra pro určení výšky sklonu
        dist_from_center = math.sqrt((pt.x - center_x)**2 + (pt.y - center_y)**2)
        # Aplikace sklonu - body dále od centra budou níže
        roof_z = height + roof_thickness - (dist_from_center * slope / 100)
        roof_pts.append(Point3D(pt.x, pt.y, roof_z))
    
    roof_face = Face3D(roof_pts)
    return roof_face

def create_gable_roof(footprint, height, roof_height=3, axis='y', slope_angle=30):
    """Vytvoří sedlovou střechu s nastavitelným úhlem sklonu."""
    # Převeďme úhel sklonu na výšku hřebene
    min_x = min(pt.x for pt in footprint)
    max_x = max(pt.x for pt in footprint)
    min_y = min(pt.y for pt in footprint)
    max_y = max(pt.y for pt in footprint)
    
    width = max_x - min_x
    depth = max_y - min_y
    
    # Výpočet výšky hřebene na základě úhlu sklonu
    if axis == 'y':
        # Hřeben je rovnoběžný s osou y
        span = width / 2
        adjusted_height = span * math.tan(math.radians(slope_angle))
    else:  # axis == 'x'
        # Hřeben je rovnoběžný s osou x
        span = depth / 2
        adjusted_height = span * math.tan(math.radians(slope_angle))
    
    # Použijeme buď zadanou výšku nebo vypočtenou z úhlu sklonu (co je větší)
    roof_height = max(roof_height, adjusted_height)
    
    # Najdi body na spodní hraně střechy
    bottom_pts = sorted(footprint, key=lambda pt: (pt.x, pt.y))
    
    if axis == 'y':
        # Osa střechy je rovnoběžná s osou y
        mid_x = (min_x + max_x) / 2
        
        # Vytvoř body hřebene
        ridge_pt1 = Point3D(mid_x, min_y, height + roof_height)
        ridge_pt2 = Point3D(mid_x, max_y, height + roof_height)
        
        # Vytvoř plochy střechy
        roof_face1_pts = [
            Point3D(min_x, min_y, height), 
            Point3D(min_x, max_y, height),
            ridge_pt2,
            ridge_pt1
        ]
        
        roof_face2_pts = [
            Point3D(max_x, min_y, height),
            Point3D(max_x, max_y, height),
            ridge_pt2,
            ridge_pt1
        ]
        
    else:  # axis == 'x'
        # Osa střechy je rovnoběžná s osou x
        mid_y = (min_y + max_y) / 2
        
        # Vytvoř body hřebene
        ridge_pt1 = Point3D(min_x, mid_y, height + roof_height)
        ridge_pt2 = Point3D(max_x, mid_y, height + roof_height)
        
        # Vytvoř plochy střechy
        roof_face1_pts = [
            Point3D(min_x, min_y, height),
            Point3D(max_x, min_y, height),
            ridge_pt2,
            ridge_pt1
        ]
        
        roof_face2_pts = [
            Point3D(min_x, max_y, height),
            Point3D(max_x, max_y, height),
            ridge_pt2,
            ridge_pt1
        ]
    
    # Vytvoř plochy
    roof_face1 = Face3D(roof_face1_pts)
    roof_face2 = Face3D(roof_face2_pts)
    
    # Přidej čelní trojúhelníky (štíty)
    gable_faces = []
    if axis == 'y':
        gable1_pts = [
            Point3D(min_x, min_y, height),
            Point3D(max_x, min_y, height),
            ridge_pt1
        ]
        gable2_pts = [
            Point3D(min_x, max_y, height),
            Point3D(max_x, max_y, height),
            ridge_pt2
        ]
        gable_faces = [Face3D(gable1_pts), Face3D(gable2_pts)]
    else:  # axis == 'x'
        gable1_pts = [
            Point3D(min_x, min_y, height),
            Point3D(min_x, max_y, height),
            ridge_pt1
        ]
        gable2_pts = [
            Point3D(max_x, min_y, height),
            Point3D(max_x, max_y, height), 
            ridge_pt2
        ]
        gable_faces = [Face3D(gable1_pts), Face3D(gable2_pts)]
    
    return [roof_face1, roof_face2] + gable_faces

def create_hip_roof(footprint, height, roof_height=2.5, slope_angle=25):
    """Vytvoří valbovou střechu s nastavitelným úhlem sklonu."""
    # Předpokládáme, že půdorys je obdélník
    min_x = min(pt.x for pt in footprint)
    max_x = max(pt.x for pt in footprint)
    min_y = min(pt.y for pt in footprint)
    max_y = max(pt.y for pt in footprint)
    
    width = max_x - min_x
    depth = max_y - min_y
    
    # Výpočet výšky hřebene na základě úhlu sklonu a menší dimenze půdorysu
    span = min(width, depth) / 2
    adjusted_height = span * math.tan(math.radians(slope_angle))
    
    # Použijeme buď zadanou výšku nebo vypočtenou z úhlu sklonu
    roof_height = max(roof_height, adjusted_height)
    
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    
    # Vytvoř bod vrcholu (peak) pro klasickou valbovou střechu
    peak_pt = Point3D(center_x, center_y, height + roof_height)
    
    # Vytvoř body rohů (spodní hrana střechy)
    corner_pts = [
        Point3D(min_x, min_y, height),  # levý dolní
        Point3D(max_x, min_y, height),  # pravý dolní
        Point3D(max_x, max_y, height),  # pravý horní
        Point3D(min_x, max_y, height)   # levý horní
    ]
    
    # Vytvoř plochy střechy (čtyři trojúhelníky)
    roof_faces = []
    for i in range(4):
        pts = [corner_pts[i], corner_pts[(i+1) % 4], peak_pt]
        roof_faces.append(Face3D(pts))
    
    return roof_faces

def create_pyramid_roof(footprint, height, roof_height=4):
    """Vytvoří jehlanovitou střechu."""
    # Stejná implementace jako hip_roof, jen jiný název pro větší srozumitelnost
    return create_hip_roof(footprint, height, roof_height)

def create_shed_roof(footprint, height, roof_height=2, slope_direction='north', slope_angle=None):
    """Vytvoří pultovou střechu s nastavitelným úhlem sklonu."""
    # Předpokládáme, že půdorys je obdélník
    min_x = min(pt.x for pt in footprint)
    max_x = max(pt.x for pt in footprint)
    min_y = min(pt.y for pt in footprint)
    max_y = max(pt.y for pt in footprint)
    
    # Pokud je zadán úhel sklonu, přepočítáme výšku
    if slope_angle is not None:
        if slope_direction in ['north', 'south']:
            span = max_y - min_y
        else:  # east, west
            span = max_x - min_x
        # Výpočet výšky z úhlu sklonu
        roof_height = span * math.tan(math.radians(slope_angle))
    
    # Vytvoř body podle směru sklonu
    if slope_direction == 'north':
        # Vyšší strana je na severu (max_y)
        roof_pts = [
            Point3D(min_x, min_y, height),
            Point3D(max_x, min_y, height),
            Point3D(max_x, max_y, height + roof_height),
            Point3D(min_x, max_y, height + roof_height)
        ]
    elif slope_direction == 'south':
        # Vyšší strana je na jihu (min_y)
        roof_pts = [
            Point3D(min_x, min_y, height + roof_height),
            Point3D(max_x, min_y, height + roof_height),
            Point3D(max_x, max_y, height),
            Point3D(min_x, max_y, height)
        ]
    elif slope_direction == 'east':
        # Vyšší strana je na východě (max_x)
        roof_pts = [
            Point3D(min_x, min_y, height),
            Point3D(max_x, min_y, height + roof_height),
            Point3D(max_x, max_y, height + roof_height),
            Point3D(min_x, max_y, height)
        ]
    else:  # slope_direction == 'west'
        # Vyšší strana je na západě (min_x)
        roof_pts = [
            Point3D(min_x, min_y, height + roof_height),
            Point3D(max_x, min_y, height),
            Point3D(max_x, max_y, height),
            Point3D(min_x, max_y, height + roof_height)
        ]
    
    return Face3D(roof_pts)

def create_mansard_roof(footprint, height, roof_height=3, lower_slope=70, upper_slope=30):
    """Vytvoří mansardovou střechu s různými úhly sklonu."""
    min_x = min(pt.x for pt in footprint)
    max_x = max(pt.x for pt in footprint)
    min_y = min(pt.y for pt in footprint)
    max_y = max(pt.y for pt in footprint)
    
    width = max_x - min_x
    depth = max_y - min_y
    
    # Rozdělení výšky střechy mezi spodní a horní část
    lower_height = roof_height * 0.7
    upper_height = roof_height * 0.3
    
    # Inset pro horní část mansardové střechy
    inset_x = width * 0.25
    inset_y = depth * 0.25
    
    # Dolní body střechy (spodní hrana)
    corner_pts = [
        Point3D(min_x, min_y, height),  # levý dolní
        Point3D(max_x, min_y, height),  # pravý dolní
        Point3D(max_x, max_y, height),  # pravý horní
        Point3D(min_x, max_y, height)   # levý horní
    ]
    
    # Horní body střechy (mezi spodní a horní částí)
    mid_pts = [
        Point3D(min_x + inset_x, min_y + inset_y, height + lower_height),
        Point3D(max_x - inset_x, min_y + inset_y, height + lower_height),
        Point3D(max_x - inset_x, max_y - inset_y, height + lower_height),
        Point3D(min_x + inset_x, max_y - inset_y, height + lower_height)
    ]
    
    # Vrchol střechy
    top_pts = [
        Point3D(min_x + inset_x, min_y + inset_y, height + roof_height),
        Point3D(max_x - inset_x, min_y + inset_y, height + roof_height),
        Point3D(max_x - inset_x, max_y - inset_y, height + roof_height),
        Point3D(min_x + inset_x, max_y - inset_y, height + roof_height)
    ]
    
    # Vytvoř plochy střechy
    roof_faces = []
    
    # Spodní části (mansardové sklony)
    for i in range(4):
        pts = [
            corner_pts[i],
            corner_pts[(i+1) % 4],
            mid_pts[(i+1) % 4],
            mid_pts[i]
        ]
        roof_faces.append(Face3D(pts))
    
    # Horní části (plošší sklony)
    roof_faces.append(Face3D(mid_pts))  # Horní plocha
    
    return roof_faces

def create_butterfly_roof(footprint, height, roof_height=2, valley_depth=1):
    """Vytvoří motýlí střechu s centrálním úžlabím."""
    min_x = min(pt.x for pt in footprint)
    max_x = max(pt.x for pt in footprint)
    min_y = min(pt.y for pt in footprint)
    max_y = max(pt.y for pt in footprint)
    
    center_x = (min_x + max_x) / 2
    
    # Vytvoř body úžlabí (valley)
    valley_pt1 = Point3D(center_x, min_y, height + roof_height - valley_depth)
    valley_pt2 = Point3D(center_x, max_y, height + roof_height - valley_depth)
    
    # Vytvoř body hřebene na okrajích
    ridge_pt1 = Point3D(min_x, min_y, height + roof_height)
    ridge_pt2 = Point3D(max_x, min_y, height + roof_height)
    ridge_pt3 = Point3D(max_x, max_y, height + roof_height)
    ridge_pt4 = Point3D(min_x, max_y, height + roof_height)
    
    # Vytvoř plochy střechy
    roof_face1 = Face3D([
        ridge_pt1,
        valley_pt1,
        valley_pt2,
        ridge_pt4
    ])
    
    roof_face2 = Face3D([
        valley_pt1,
        ridge_pt2,
        ridge_pt3,
        valley_pt2
    ])
    
    return [roof_face1, roof_face2]

def create_sawtooth_roof(footprint, height, section_width=4, roof_height=2, slope_angle=30):
    """Vytvoří pilovou střechu s nastavitelným počtem sekcí."""
    min_x = min(pt.x for pt in footprint)
    max_x = max(pt.x for pt in footprint)
    min_y = min(pt.y for pt in footprint)
    max_y = max(pt.y for pt in footprint)
    
    width = max_x - min_x
    depth = max_y - min_y
    
    # Určení počtu sekcí
    num_sections = max(2, int(width / section_width))
    section_width = width / num_sections
    
    # Vytvoř plochy střechy
    roof_faces = []
    
    for i in range(num_sections):
        x1 = min_x + i * section_width
        x2 = min_x + (i + 1) * section_width
        
        # Vytvoření trojúhelníkových nebo lichoběžníkových ploch podle sklonu
        if i % 2 == 0:  # Šikmá část
            roof_pts = [
                Point3D(x1, min_y, height),
                Point3D(x2, min_y, height),
                Point3D(x2, max_y, height),
                Point3D(x1, max_y, height + roof_height)
            ]
        else:  # Svislá/prosklená část
            roof_pts = [
                Point3D(x1, min_y, height + roof_height),
                Point3D(x2, min_y, height),
                Point3D(x2, max_y, height),
                Point3D(x1, max_y, height + roof_height)
            ]
        
        roof_faces.append(Face3D(roof_pts))
    
    return roof_faces

def create_curved_roof(footprint, height, roof_height=3, num_segments=8):
    """Vytvoří zaoblenou střechu pomocí segmentace."""
    min_x = min(pt.x for pt in footprint)
    max_x = max(pt.x for pt in footprint)
    min_y = min(pt.y for pt in footprint)
    max_y = max(pt.y for pt in footprint)
    
    center_x = (min_x + max_x) / 2
    width = max_x - min_x
    
    # Vytvoř plochy střechy jako segmenty oblouku
    roof_faces = []
    
    for i in range(num_segments):
        angle1 = math.pi * i / num_segments
        angle2 = math.pi * (i + 1) / num_segments
        
        # Výpočet bodů pro aktuální segment
        height1 = height + roof_height * math.sin(angle1)
        height2 = height + roof_height * math.sin(angle2)
        
        x1 = center_x - (width / 2) * math.cos(angle1)
        x2 = center_x - (width / 2) * math.cos(angle2)
        
        # Vytvoř plochu segmentu
        segment_pts = [
            Point3D(x1, min_y, height1),
            Point3D(x2, min_y, height2),
            Point3D(x2, max_y, height2),
            Point3D(x1, max_y, height1)
        ]
        
        roof_faces.append(Face3D(segment_pts))
    
    return roof_faces

def create_solar_roof(footprint, height, tilt_angle=15, orientation='south', coverage=0.8):
    """
    Vytvoří střechu optimalizovanou pro solární panely s daným sklonem a orientací.
    Přidá objekty reprezentující samotné panely.
    """
    min_x = min(pt.x for pt in footprint)
    max_x = max(pt.x for pt in footprint)
    min_y = min(pt.y for pt in footprint)
    max_y = max(pt.y for pt in footprint)
    
    width = max_x - min_x
    depth = max_y - min_y
    
    # Základní plochá střecha
    flat_roof = create_flat_roof(footprint, height)
    roof_faces = [flat_roof]
    
    # Přidáme objekty reprezentující solární panely
    panel_width = 1.7  # typická šířka panelu v metrech
    panel_height = 1.0  # typická výška panelu v metrech
    panel_thickness = 0.05
    
    # Určení počtu panelů, které se vejdou na střechu
    max_panels_x = int(width / panel_width)
    max_panels_y = int(depth / panel_height)
    total_max_panels = max_panels_x * max_panels_y
    
    # Kolik panelů chceme rozmístit podle pokrytí
    num_panels = int(total_max_panels * coverage)
    
    # Vytvoření rozmístění panelů
    panel_faces = []
    
    # Určení normálového vektoru pro orientaci panelu
    if orientation == 'south':
        normal = Vector3D(0, -1, 0)
    elif orientation == 'north':
        normal = Vector3D(0, 1, 0)
    elif orientation == 'east':
        normal = Vector3D(-1, 0, 0)
    elif orientation == 'west':
        normal = Vector3D(1, 0, 0)
    else:
        normal = Vector3D(0, -1, 0)  # výchozí je jih
    
    # Rotace normály o úhel sklonu
    if orientation in ['south', 'north']:
        # Rotace kolem osy x
        rotation_axis = Vector3D(1, 0, 0)
    else:
        # Rotace kolem osy y
        rotation_axis = Vector3D(0, 1, 0)
    
    # Aplikace rotace
    angle_rad = math.radians(tilt_angle)
    # Složitější rotační matice by byla potřeba pro přesnou rotaci
    
    panels_placed = 0
    panel_spacing = 0.1  # mezera mezi panely
    
    for i in range(max_panels_x):
        for j in range(max_panels_y):
            if panels_placed < num_panels:
                # Umístění panelu na střechu
                panel_origin_x = min_x + i * (panel_width + panel_spacing)
                panel_origin_y = min_y + j * (panel_height + panel_spacing)
                
                # Základní body panelu bez rotace
                panel_pts = [
                    Point3D(panel_origin_x, panel_origin_y, height + panel_thickness),
                    Point3D(panel_origin_x + panel_width, panel_origin_y, height + panel_thickness),
                    Point3D(panel_origin_x + panel_width, panel_origin_y + panel_height, height + panel_thickness),
                    Point3D(panel_origin_x, panel_origin_y + panel_height, height + panel_thickness)
                ]
                
                # Aplikace sklonu (zjednodušený přístup)
                if orientation == 'south':
                    panel_pts[2] = Point3D(panel_pts[2].x, panel_pts[2].y, panel_pts[2].z + panel_height * math.sin(angle_rad))
                    panel_pts[3] = Point3D(panel_pts[3].x, panel_pts[3].y, panel_pts[3].z + panel_height * math.sin(angle_rad))
                elif orientation == 'north':
                    panel_pts[0] = Point3D(panel_pts[0].x, panel_pts[0].y, panel_pts[0].z + panel_height * math.sin(angle_rad))
                    panel_pts[1] = Point3D(panel_pts[1].x, panel_pts[1].y, panel_pts[1].z + panel_height * math.sin(angle_rad))
                elif orientation == 'east':
                    panel_pts[1] = Point3D(panel_pts[1].x, panel_pts[1].y, panel_pts[1].z + panel_width * math.sin(angle_rad))
                    panel_pts[2] = Point3D(panel_pts[2].x, panel_pts[2].y, panel_pts[2].z + panel_width * math.sin(angle_rad))
                elif orientation == 'west':
                    panel_pts[0] = Point3D(panel_pts[0].x, panel_pts[0].y, panel_pts[0].z + panel_width * math.sin(angle_rad))
                    panel_pts[3] = Point3D(panel_pts[3].x, panel_pts[3].y, panel_pts[3].z + panel_width * math.sin(angle_rad))
                
                panel_face = Face3D(panel_pts)
                panel_faces.append(panel_face)
                panels_placed += 1
    
    return roof_faces, panel_faces

def create_roof(footprint, height, roof_type, roof_params=None):
    """Vytvoří střechu podle zadaného typu a parametrů."""
    if roof_params is None:
        roof_params = {}
    
    roof_faces = []
    solar_panels = []
    
    if roof_type == 'flat':
        roof_faces = [create_flat_roof(
            footprint, 
            height, 
            roof_params.get('roof_thickness', 0.3),
            roof_params.get('slope', 0)
        )]
    
    elif roof_type == 'gable':
        roof_faces = create_gable_roof(
            footprint, 
            height, 
            roof_params.get('roof_height', 3),
            roof_params.get('axis', 'y'),
            roof_params.get('slope_angle', 30)
        )
    
    elif roof_type == 'hip':
        roof_faces = create_hip_roof(
            footprint, 
            height,
            roof_params.get('roof_height', 2.5),
            roof_params.get('slope_angle', 25)
        )
    
    elif roof_type == 'pyramid':
        roof_faces = create_pyramid_roof(
            footprint, 
            height,
            roof_params.get('roof_height', 4)
        )
    
    elif roof_type == 'shed':
        roof_faces = [create_shed_roof(
            footprint, 
            height,
            roof_params.get('roof_height', 2),
            roof_params.get('slope_direction', 'north'),
            roof_params.get('slope_angle', None)
        )]
    
    elif roof_type == 'mansard':
        roof_faces = create_mansard_roof(
            footprint, 
            height,
            roof_params.get('roof_height', 3),
            roof_params.get('lower_slope', 70),
            roof_params.get('upper_slope', 30)
        )
    
    elif roof_type == 'butterfly':
        roof_faces = create_butterfly_roof(
            footprint, 
            height,
            roof_params.get('roof_height', 2),
            roof_params.get('valley_depth', 1)
        )
    
    elif roof_type == 'sawtooth':
        roof_faces = create_sawtooth_roof(
            footprint, 
            height,
            roof_params.get('section_width', 4),
            roof_params.get('roof_height', 2),
            roof_params.get('slope_angle', 30)
        )
    
    elif roof_type == 'curved':
        roof_faces = create_curved_roof(
            footprint, 
            height,
            roof_params.get('roof_height', 3),
            roof_params.get('num_segments', 8)
        )
    
    elif roof_type == 'solar':
        roof_faces, solar_panels = create_solar_roof(
            footprint, 
            height,
            roof_params.get('tilt_angle', 15),
            roof_params.get('orientation', 'south'),
            roof_params.get('coverage', 0.8)
        )
    
    else:
        # Výchozí je plochá střecha
        roof_faces = [create_flat_roof(footprint, height, 0.3)]
    
    return roof_faces, solar_panels

def create_building(origin, width, depth, height, num_floors, roof_type, roof_params=None, window_ratio=0.4):
    """Vytvoří budovu se zadaným typem střechy."""
    if roof_params is None:
        roof_params = {}
    
    # Vytvoř půdorys
    footprint_pts = [
        Point3D(origin.x, origin.y, origin.z),
        Point3D(origin.x + width, origin.y, origin.z),
        Point3D(origin.x + width, origin.y + depth, origin.z),
        Point3D(origin.x, origin.y + depth, origin.z)
    ]
    
    # Vytvoř místnosti pro každé podlaží
    rooms = []
    floor_height = height / num_floors
    
    for floor in range(num_floors):
        floor_base = origin.z + floor * floor_height
        floor_top = floor_base + floor_height
        
        # Použití jednoduššího přístupu - vytvoření místnosti jako kvádr
        room_id = f"Building_{int(origin.x)}_{int(origin.y)}_Floor_{floor}"
        
        room = Room.from_box(
            room_id, 
            width, 
            depth, 
            floor_height, 
            origin=Point3D(origin.x, origin.y, floor_base)
        )
        
        # Přidej okna na každou stěnu (kromě podlahy a stropu)
        for face in room.faces:
            if face.type == 'wall':
                try:
                    face.apertures_by_ratio(window_ratio, tolerance=0.01)
                except Exception as e:
                    print(f"Chyba při přidávání okna: {e}")
                    pass
        
        rooms.append(room)
    
    # Vytvoříme střechu a případné solární panely
    roof_faces, solar_panels = create_roof(footprint_pts, height, roof_type, roof_params)
    
    # Vytvoříme Shade objekty pro střechu a solární panely
    roof_shades = []
    for i, roof_face in enumerate(roof_faces):
        shade_id = f"Roof_{int(origin.x)}_{int(origin.y)}_{i}"
        roof_shade = Shade(shade_id, roof_face)
        # Přidání vlastností pro sledování typu střechy
        roof_shade.user_data = {
            "type": "roof",
            "roof_type": roof_type,
            "building_id": rooms[0].identifier,
            "slope_direction": roof_params.get('slope_direction', 'none'),
            "slope_angle": roof_params.get('slope_angle', 0)
        }
        roof_shades.append(roof_shade)
    
    # Přidáme solární panely jako Shade objekty
    panel_shades = []
    for i, panel_face in enumerate(solar_panels):
        panel_id = f"SolarPanel_{int(origin.x)}_{int(origin.y)}_{i}"
        panel_shade = Shade(panel_id, panel_face)
        panel_shade.user_data = {
            "type": "solar_panel",
            "building_id": rooms[0].identifier,
            "efficiency": 0.2  # typická účinnost solárního panelu
        }
        panel_shades.append(panel_shade)
    
    # Nejvyšší patro označíme jako patro se střechou
    top_floor_room = rooms[-1]
    top_floor_room.user_data = {
        "roof_type": roof_type,
        "roof_params": roof_params
    }
    
    return rooms, roof_shades + panel_shades

def create_city(num_buildings=10, city_size=100):
    """Vytvoří město s zadaným počtem budov."""
    # Rozšířený seznam typů střech
    roof_types = ['flat', 'gable', 'hip', 'pyramid', 'shed', 'mansard', 'butterfly', 'sawtooth', 'curved', 'solar']
    
    # Parametry pro různé typy budov
    building_types = [
        {'width': 10, 'depth': 10, 'height': 10, 'num_floors': 3},  # Malý dům
        {'width': 15, 'depth': 15, 'height': 15, 'num_floors': 4},  # Střední dům
        {'width': 20, 'depth': 15, 'height': 20, 'num_floors': 5},  # Velký dům
        {'width': 30, 'depth': 20, 'height': 30, 'num_floors': 8},  # Malý panelák
        {'width': 40, 'depth': 25, 'height': 45, 'num_floors': 15},  # Velký panelák
        {'width': 50, 'depth': 50, 'height': 25, 'num_floors': 6},  # Kancelářská budova
        {'width': 25, 'depth': 60, 'height': 12, 'num_floors': 3},  # Dlouhá budova
        {'width': 30, 'depth': 30, 'height': 15, 'num_floors': 4},  # Čtvercová budova
        {'width': 18, 'depth': 12, 'height': 18, 'num_floors': 5},  # Bytový dům
        {'width': 35, 'depth': 20, 'height': 22, 'num_floors': 6}   # Administrativní budova
    ]
    
    # Parametry pro různé typy střech s větší variabilitou
    roof_params = {
        'flat': {'roof_thickness': 0.3, 'slope': 0.5},  # mírný sklon pro odvod vody
        'gable': {'roof_height': 4, 'axis': 'y', 'slope_angle': 35},
        'hip': {'roof_height': 3.5, 'slope_angle': 30},
        'pyramid': {'roof_height': 5},
        'shed': {'roof_height': 3, 'slope_direction': 'north', 'slope_angle': 25},
        'mansard': {'roof_height': 4, 'lower_slope': 70, 'upper_slope': 20},
        'butterfly': {'roof_height': 2.5, 'valley_depth': 1.2},
        'sawtooth': {'section_width': 4, 'roof_height': 2.5, 'slope_angle': 25},
        'curved': {'roof_height': 3.5, 'num_segments': 10},
        'solar': {'tilt_angle': 15, 'orientation': 'south', 'coverage': 0.7}
    }
    
    # Vytvoř mřížku pro umístění budov
    grid_size = math.ceil(math.sqrt(num_buildings))
    spacing = city_size / grid_size
    
    # Vytvoř budovy
    all_rooms = []
    all_shades = []
    
    # Modifikace pro solární potenciál - lepší strategie rozmístění budov
    # Budovy s vyšším potenciálem pro solár umístíme na jih a do míst bez stínění
    
    # Seřadíme mřížku podle vzdálenosti od jižní strany (předpokládáme, že y = 0 je jih)
    grid_positions = []
    for i in range(grid_size):
        for j in range(grid_size):
            # Určení priority - čím menší y, tím lepší pro solár (méně stínění)
            priority = j  # priorita podle y-souřadnice
            grid_positions.append((i, j, priority))
    
    # Seřadíme pozice podle priority
    grid_positions.sort(key=lambda x: x[2])
    
    # Každé budově přidělíme typ střechy odpovídající optimálně její pozici a velikosti
    building_assignments = []
    
    for i in range(min(num_buildings, len(grid_positions))):
        grid_x, grid_y, _ = grid_positions[i]
        
        # Vyber typ budovy náhodně
        building_type = random.choice(building_types)
        
        # Vyber typ střechy chytřeji na základě pozice
        # Jižní strana - dobré pro solární střechy
        if grid_y < grid_size / 3:
            if random.random() < 0.6:  # 60% šance na solární nebo šikmou střechu orientovanou na jih
                roof_type = random.choice(['solar', 'gable', 'shed'])
                if roof_type == 'shed':
                    roof_params['shed']['slope_direction'] = 'south'
                elif roof_type == 'gable':
                    roof_params['gable']['axis'] = 'x'  # hřeben východ-západ pro jižní orientaci
            else:
                roof_type = random.choice(roof_types)
        # Střed - mix různých typů
        elif grid_y < 2 * grid_size / 3:
            roof_type = random.choice(roof_types)
        # Sever - méně solárních střech, více plochých nebo šikmých s orientací na jih
        else:
            if random.random() < 0.7:  # 70% šance na střechu vhodnou pro severní pozici
                roof_type = random.choice(['flat', 'gable', 'hip', 'mansard'])
                if roof_type == 'shed':
                    roof_params['shed']['slope_direction'] = 'south'  # i na severu orientujeme na jih
            else:
                roof_type = random.choice(roof_types)
        
        # Přizpůsobení parametrů střechy
        current_roof_params = roof_params.get(roof_type, {}).copy()
        
        # Variabilita ve sklonu a orientaci
        if roof_type == 'gable':
            current_roof_params['axis'] = random.choice(['x', 'y'])
            current_roof_params['slope_angle'] = random.uniform(25, 45)
        elif roof_type == 'shed':
            current_roof_params['slope_direction'] = random.choice(['north', 'south', 'east', 'west'])
            current_roof_params['slope_angle'] = random.uniform(15, 35)
        elif roof_type == 'solar':
            # Optimální sklon pro solární panely podle zeměpisné šířky (přibližně)
            current_roof_params['tilt_angle'] = random.uniform(30, 40)  # Optimální pro střední Evropu
            current_roof_params['orientation'] = random.choice(['south', 'southeast', 'southwest'])
            current_roof_params['coverage'] = random.uniform(0.5, 0.9)
        
        # Vypočítej pozici budovy v mřížce
        offset_x = random.uniform(0, spacing - building_type['width'])
        offset_y = random.uniform(0, spacing - building_type['depth'])
        
        origin = Point3D(
            grid_x * spacing + offset_x,
            grid_y * spacing + offset_y,
            0
        )
        
        # Vytvoř budovu
        building_rooms, building_shades = create_building(
            origin,
            building_type['width'],
            building_type['depth'],
            building_type['height'],
            building_type['num_floors'],
            roof_type,
            current_roof_params,
            window_ratio=0.3
        )
        
        all_rooms.extend(building_rooms)
        all_shades.extend(building_shades)
        
        print(f"Vytvořena budova {i+1} s typem střechy '{roof_type}'")
    
    # Vytvoř model města
    city_model = Model('City_Model', all_rooms, orphaned_shades=all_shades)
    
    # Odstraníme pokus o přidání vlastností, které nejsou dostupné v aktuální verzi Honeybee
    # city_model.properties.energy.add_default_constructionset()
    # city_model.properties.energy.add_default_schedule_set()
    
    return city_model

def add_solar_analysis_properties(model):
    """Přidá vlastnosti pro solární analýzu k modelu."""
    # Vytvoříme vlastní modifikátory pro různé povrchy
    roof_material = Plastic('roof_material')
    roof_material.r_reflectance = 0.3
    roof_material.g_reflectance = 0.3
    roof_material.b_reflectance = 0.3
    roof_material.specularity = 0.0
    roof_material.roughness = 0.15
    
    solar_panel_material = Metal('solar_panel_material')
    solar_panel_material.r_reflectance = 0.1
    solar_panel_material.g_reflectance = 0.1
    solar_panel_material.b_reflectance = 0.1
    solar_panel_material.specularity = 0.5
    
    # Projdeme všechny stíny (shade) a přidáme vlastnosti pro solární analýzu
    for shade in model.shades:
        if shade.user_data and shade.user_data.get('type') == 'roof':
            # Přidá vlastnosti pro analýzu solárního potenciálu střech
            shade.properties.radiance.modifier = roof_material
        
        if shade.user_data and shade.user_data.get('type') == 'solar_panel':
            # Přidá vlastnosti pro solární panely
            shade.properties.radiance.modifier = solar_panel_material
    
    return model

def export_model_to_hbjson(model, output_file):
    """Exportuje model do HBJSON souboru."""
    # Převeď model na slovník
    model_dict = model.to_dict()
    
    # Zapiš do HBJSON souboru
    with open(output_file, 'w') as f:
        json.dump(model_dict, f, indent=4)
    
    print(f"Model byl úspěšně exportován do {output_file}")

def main():
    """Hlavní funkce pro vytvoření a uložení modelu města."""
    # Vytvoř složku pro výstup
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Vytvoř město
    print("Generuji model města...")
    city_model = create_city(num_buildings=15, city_size=200)
    
    # Přidej vlastnosti pro solární analýzu
    city_model = add_solar_analysis_properties(city_model)
    
    # Exportuj do HBJSON
    output_file = os.path.join(output_dir, 'city_model_solar.hbjson')
    export_model_to_hbjson(city_model, output_file)
    
    print("Generování modelu města bylo dokončeno.")
    print(f"Model obsahuje {len(city_model.rooms)} místností a {len(city_model.shades)} stínících prvků.")
    print(f"Model byl uložen do souboru: {os.path.abspath(output_file)}")
    print("\nPOZNÁMKA: Pro vizualizaci HBJSON modelu můžete použít:")
    print("1. Online viewer: https://hydrashare.github.io/viewer/")
    print("2. Plugin pro VS Code: 'ladybug-tools' extension")
    print("3. Pro solární analýzu použijte Ladybug Tools s následujícími kroky:")
    print("   - Použijte 'LB Radiation Analysis' pro analýzu radiace na plochách")
    print("   - Použijte 'LB Sunlight Hours Analysis' pro analýzu hodin slunečního svitu")
    print("   - Použijte 'LB Incident Radiation' pro výpočet dopadajícího záření na plochy")
    print("   - Použijte 'HB Annual Irradiance' pro roční analýzu ozáření")
    print("\nPro optimální sklon a orientaci solárních panelů v Česku (Frýdek-Místek) doporučuji:")
    print("   - Orientace: jižní (azimut 180°)")
    print("   - Sklon: přibližně 35-40° pro maximální celoroční zisk")
    print("   - Sklon: přibližně 30° pro optimalizaci na letní období")
    print("   - Sklon: přibližně 45-50° pro optimalizaci na zimní období")

if __name__ == "__main__":
    main()