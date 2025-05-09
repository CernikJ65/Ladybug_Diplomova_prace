import json
import os
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import matplotlib.patches as mpatches

def read_hbjson(file_path):
    """Načte HBJSON soubor."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Soubor {file_path} nebyl nalezen.")
        return None
    except json.JSONDecodeError:
        print(f"Soubor {file_path} není validní JSON.")
        return None

def extract_vertices_from_face(face):
    """Extrahuje vrcholy z plochy."""
    vertices = []
    # Kontrola starého formátu (geometry.boundary)
    if 'geometry' in face and 'boundary' in face['geometry']:
        for pt in face['geometry']['boundary']:
            vertices.append(pt)
    # Kontrola nového formátu (geometry.vertices + geometry.faces)
    elif 'geometry' in face and 'vertices' in face['geometry'] and 'faces' in face['geometry']:
        face_vertices = face['geometry']['vertices']
        # Může být více ploch v jednom objektu
        for face_indices in face['geometry']['faces']:
            # Vytvoříme jednotlivé plochy pomocí indexů vrcholů
            face_pts = [face_vertices[idx] for idx in face_indices]
            if face_pts:
                vertices.append(face_pts)
    return vertices

def extract_faces_from_rooms_and_shades(model_data):
    """Extrahuje všechny plochy z místností a stínů modelu."""
    all_faces = []
    all_face_types = []
    all_room_indices = []
    all_heights = []
    all_roof_types = []
    all_is_solar_panel = []
    
    # Projít všechny místnosti
    if 'rooms' in model_data:
        for room_idx, room in enumerate(model_data['rooms']):
            # Zjistit, zda místnost má definovaný typ střechy
            roof_type = 'unknown'
            if 'user_data' in room and room['user_data'] and 'roof_type' in room['user_data']:
                roof_type = room['user_data']['roof_type']
            
            # Zjistit výšku místnosti (pro barevné mapování)
            height = 0
            if 'geometry' in room:
                for vertex in room['geometry'].get('vertices', []):
                    height = max(height, vertex[2])  # Z-souřadnice nejvyššího bodu
            
            # Projít všechny plochy místnosti
            if 'faces' in room:
                for face in room['faces']:
                    vertices = extract_vertices_from_face(face)
                    if vertices:
                        # Pokud je to seznam ploch (nový formát)
                        if isinstance(vertices[0], list) and isinstance(vertices[0][0], list):
                            for v in vertices:
                                all_faces.append(v)
                                face_type = face.get('face_type', 'unknown')
                                all_face_types.append(face_type)
                                all_room_indices.append(room_idx)
                                all_heights.append(height)
                                all_roof_types.append(roof_type)
                                all_is_solar_panel.append(False)
                        else:
                            all_faces.append(vertices)
                            # Uložit typ plochy (roof_ceiling, wall, floor)
                            face_type = face.get('face_type', 'unknown')
                            all_face_types.append(face_type)
                            all_room_indices.append(room_idx)
                            all_heights.append(height)
                            all_roof_types.append(roof_type)
                            all_is_solar_panel.append(False)
            
            # Projít okna (apertures)
            if 'apertures' in room:
                for aperture in room['apertures']:
                    vertices = extract_vertices_from_face(aperture)
                    if vertices:
                        # Kontrola typu vrcholů
                        if isinstance(vertices[0], list) and isinstance(vertices[0][0], list):
                            for v in vertices:
                                all_faces.append(v)
                                all_face_types.append('aperture')
                                all_room_indices.append(room_idx)
                                all_heights.append(height)
                                all_roof_types.append(roof_type)
                                all_is_solar_panel.append(False)
                        else:
                            all_faces.append(vertices)
                            all_face_types.append('aperture')  # Okna mají vlastní typ
                            all_room_indices.append(room_idx)
                            all_heights.append(height)
                            all_roof_types.append(roof_type)
                            all_is_solar_panel.append(False)
    
    # Projít stíny (orphaned_shades) - střechy a solární panely
    if 'orphaned_shades' in model_data:
        for shade_idx, shade in enumerate(model_data['orphaned_shades']):
            # Určit, zda je to střecha nebo solární panel
            is_solar_panel = False
            roof_type = 'unknown'
            
            if 'user_data' in shade and shade['user_data']:
                if 'type' in shade['user_data']:
                    if shade['user_data']['type'] == 'solar_panel':
                        is_solar_panel = True
                    elif shade['user_data']['type'] == 'roof':
                        roof_type = shade['user_data'].get('roof_type', 'unknown')
            
            vertices = extract_vertices_from_face(shade)
            if vertices:
                # Kontrola typu vrcholů
                if isinstance(vertices[0], list) and isinstance(vertices[0][0], list):
                    for v in vertices:
                        all_faces.append(v)
                        all_face_types.append('shade')
                        all_room_indices.append(-1)  # -1 označuje stín, který nepatří k žádné místnosti
                        
                        # Určení výšky stínu
                        height = max([pt[2] for pt in v]) if v else 0
                        all_heights.append(height)
                        
                        all_roof_types.append(roof_type)
                        all_is_solar_panel.append(is_solar_panel)
                else:
                    all_faces.append(vertices)
                    all_face_types.append('shade')
                    all_room_indices.append(-1)
                    
                    # Určení výšky stínu
                    height = max([pt[2] for pt in vertices]) if vertices else 0
                    all_heights.append(height)
                    
                    all_roof_types.append(roof_type)
                    all_is_solar_panel.append(is_solar_panel)
    
    return all_faces, all_face_types, all_room_indices, all_heights, all_roof_types, all_is_solar_panel

def plot_hbjson_model(model_data, output_file=None, show_interactive=True):
    """Vykreslí 3D model z HBJSON dat."""
    if not model_data:
        print("Žádná data k vizualizaci!")
        return
    
    faces, face_types, room_indices, heights, roof_types, is_solar_panel = extract_faces_from_rooms_and_shades(model_data)
    
    if not faces:
        print("Model neobsahuje žádné plochy k vizualizaci!")
        return
    
    # Barvy pro různé typy ploch
    color_map = {
        'roof_ceiling': 'red',
        'wall': 'lightgray',
        'floor': 'darkgray',
        'air_boundary': 'lightblue',
        'aperture': 'skyblue',
        'shade': 'gray',  # Základní barva pro stíny
        'unknown': 'purple'
    }
    
    # Barvy pro různé typy střech
    roof_type_colors = {
        'flat': 'tomato',
        'gable': 'firebrick',
        'hip': 'darkred',
        'pyramid': 'maroon',
        'shed': 'orangered',
        'mansard': 'brown',
        'butterfly': 'coral',
        'sawtooth': 'chocolate',
        'curved': 'sienna',
        'solar': 'gold',
        'unknown': 'red'
    }
    
    # Vytvoř 3D plot
    fig = plt.figure(figsize=(14, 12))
    ax = fig.add_subplot(111, projection='3d')
    
    # Přidej každou plochu do grafu s odpovídající barvou
    for i, (face, face_type, room_idx, height, roof_type, solar_panel) in enumerate(
        zip(faces, face_types, room_indices, heights, roof_types, is_solar_panel)):
        
        face_array = np.array(face)
        
        # Vyber barvu podle typu plochy a dalších vlastností
        if solar_panel:
            # Solární panely mají speciální barvu
            color = 'blue'
            alpha = 0.8
        elif face_type == 'shade' and roof_type != 'unknown':
            # Pro stíny s definovaným typem střechy (střešní plochy)
            color = roof_type_colors.get(roof_type, 'red')
            alpha = 0.9
        elif face_type == 'roof_ceiling':
            # Pro střechy vyber barvu podle typu střechy
            color = roof_type_colors.get(roof_type, 'red')
            alpha = 0.8
        else:
            # Pro ostatní plochy
            color = color_map.get(face_type, 'purple')
            alpha = 0.7 if face_type != 'aperture' else 0.5  # Okna jsou průhlednější
        
        # Vytvoř polygon
        poly = Poly3DCollection([face_array], alpha=alpha)
        poly.set_facecolor(color)
        poly.set_edgecolor('black')
        poly.set_linewidth(0.5)
        ax.add_collection3d(poly)
    
    # Najdi hranice modelu
    all_pts = np.vstack([np.array(face) for face in faces])
    min_x, max_x = np.min(all_pts[:, 0]), np.max(all_pts[:, 0])
    min_y, max_y = np.min(all_pts[:, 1]), np.max(all_pts[:, 1])
    min_z, max_z = np.min(all_pts[:, 2]), np.max(all_pts[:, 2])
    
    # Nastav limity os
    ax.set_xlim(min_x, max_x)
    ax.set_ylim(min_y, max_y)
    ax.set_zlim(min_z, max_z)
    
    # Nastav popisky os
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z (výška)')
    
    # Přidej legendu pro typy ploch a střech
    legend_elements = []
    
    # Typy ploch v legendě
    used_face_types = set(face_types)
    for face_type in used_face_types:
        if face_type in color_map:
            legend_elements.append(mpatches.Patch(color=color_map[face_type], label=face_type))
    
    # Typy střech v legendě
    used_roof_types = [rt for rt in set(roof_types) if rt != 'unknown']
    for roof_type in used_roof_types:
        if roof_type in roof_type_colors:
            legend_elements.append(mpatches.Patch(color=roof_type_colors[roof_type], 
                                              label=f"Střecha: {roof_type}"))
    
    # Solární panely v legendě (pokud existují)
    if any(is_solar_panel):
        legend_elements.append(mpatches.Patch(color='blue', label='Solární panel'))
    
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))
    
    # Nastav titulek
    plt.title('3D Vizualizace HBJSON Modelu Města se Střechami a Solárními Panely')
    plt.tight_layout()
    
    # Ulož obrázek
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Vizualizace uložena do {output_file}")
    
    # Zobraz interaktivní graf
    if show_interactive:
        plt.show()

def create_alternative_view(model_data, output_file=None, view_type='top'):
    """Vytvoří alternativní pohled na město (půdorys nebo boční pohled)."""
    if not model_data:
        print("Žádná data k vizualizaci!")
        return
    
    # Extrahuj data
    faces, face_types, room_indices, heights, roof_types, is_solar_panel = extract_faces_from_rooms_and_shades(model_data)
    
    if not faces:
        print("Model neobsahuje žádné plochy k vizualizaci!")
        return
    
    # Barvy pro různé typy střech
    roof_type_colors = {
        'flat': 'tomato',
        'gable': 'firebrick',
        'hip': 'darkred',
        'pyramid': 'maroon',
        'shed': 'orangered',
        'mansard': 'brown',
        'butterfly': 'coral',
        'sawtooth': 'chocolate',
        'curved': 'sienna',
        'solar': 'gold',
        'unknown': 'red'
    }
    
    # Vytvoř 2D plot
    fig, ax = plt.subplots(figsize=(14, 12))
    
    # Pro každou plochu
    for i, (face, face_type, room_idx, height, roof_type, solar_panel) in enumerate(
        zip(faces, face_types, room_indices, heights, roof_types, is_solar_panel)):
        
        face_array = np.array(face)
        
        # Vyber souřadnice podle typu pohledu
        if view_type == 'top':
            # Půdorys - použij X, Y souřadnice
            x_coords = face_array[:, 0]
            y_coords = face_array[:, 1]
            
            # Barevně rozliš podle typu objektu
            if solar_panel:
                color = 'blue'
                alpha = 0.9
                zorder = 5  # Solární panely jsou vidět nad vším
            elif face_type == 'shade' and roof_type != 'unknown':
                # Střešní plochy (shade s definovaným typem střechy)
                color = roof_type_colors.get(roof_type, 'red')
                alpha = 0.8
                zorder = 4  # Střechy jsou nad běžnými plochami
            elif face_type == 'roof_ceiling':
                color = roof_type_colors.get(roof_type, 'red')
                alpha = 0.8
                zorder = 3
            elif face_type == 'floor':
                color = 'darkgray'
                alpha = 0.6
                zorder = 1
            else:
                # Pro ostatní typy ploch jen tenký obrys
                color = 'lightgray'
                alpha = 0.3
                zorder = 2
        
        elif view_type == 'front':
            # Čelní pohled - použij X, Z souřadnice
            x_coords = face_array[:, 0]
            y_coords = face_array[:, 2]  # Z souřadnice jako Y v grafu
            
            # Barevně rozliš podle typu objektu
            if solar_panel:
                color = 'blue'
                alpha = 0.9
                zorder = 5
            elif face_type == 'shade' and roof_type != 'unknown':
                color = roof_type_colors.get(roof_type, 'red')
                alpha = 0.8
                zorder = 4
            elif face_type == 'roof_ceiling':
                color = roof_type_colors.get(roof_type, 'red')
                alpha = 0.8
                zorder = 3
            elif face_type == 'wall':
                color = 'lightgray'
                alpha = 0.6
                zorder = 1
            elif face_type == 'aperture':
                color = 'skyblue'
                alpha = 0.7
                zorder = 2
            else:
                color = 'darkgray'
                alpha = 0.4
                zorder = 1
        
        else:  # 'side'
            # Boční pohled - použij Y, Z souřadnice
            x_coords = face_array[:, 1]  # Y souřadnice jako X v grafu
            y_coords = face_array[:, 2]  # Z souřadnice jako Y v grafu
            
            # Barevně rozliš podle typu objektu
            if solar_panel:
                color = 'blue'
                alpha = 0.9
                zorder = 5
            elif face_type == 'shade' and roof_type != 'unknown':
                color = roof_type_colors.get(roof_type, 'red')
                alpha = 0.8
                zorder = 4
            elif face_type == 'roof_ceiling':
                color = roof_type_colors.get(roof_type, 'red')
                alpha = 0.8
                zorder = 3
            elif face_type == 'wall':
                color = 'lightgray'
                alpha = 0.6
                zorder = 1
            elif face_type == 'aperture':
                color = 'skyblue'
                alpha = 0.7
                zorder = 2
            else:
                color = 'darkgray'
                alpha = 0.4
                zorder = 1
        
        # Přidej polygon
        ax.fill(x_coords, y_coords, color=color, alpha=alpha, 
                edgecolor='black', linewidth=0.5, zorder=zorder)
    
    # Nastav popisky os podle typu pohledu
    if view_type == 'top':
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        plt.title('Půdorys Města (střechy barevně podle typu)')
    elif view_type == 'front':
        ax.set_xlabel('X')
        ax.set_ylabel('Výška (Z)')
        plt.title('Čelní Pohled na Město')
    else:  # 'side'
        ax.set_xlabel('Y')
        ax.set_ylabel('Výška (Z)')
        plt.title('Boční Pohled na Město')
    
    # Přidej legendu pro typy střech a solární panely
    legend_elements = []
    
    # Typy střech v legendě
    used_roof_types = [rt for rt in set(roof_types) if rt != 'unknown']
    for roof_type in used_roof_types:
        if roof_type in roof_type_colors:
            legend_elements.append(mpatches.Patch(color=roof_type_colors[roof_type], 
                                              label=f"Střecha: {roof_type}"))
    
    # Solární panely v legendě (pokud existují)
    if any(is_solar_panel):
        legend_elements.append(mpatches.Patch(color='blue', label='Solární panel'))
    
    # Další prvky pro lepší orientaci
    if view_type != 'top':
        legend_elements.append(mpatches.Patch(color='lightgray', label='Stěna'))
        legend_elements.append(mpatches.Patch(color='skyblue', label='Okno'))
    
    ax.legend(handles=legend_elements, loc='upper right')
    
    # Nastav správný poměr stran
    ax.set_aspect('equal')
    
    # Ulož obrázek
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Vizualizace uložena do {output_file}")
    
    # Zobraz graf
    plt.show()

def create_solar_analysis_view(model_data, output_file=None):
    """Vytvoří vizualizaci zaměřenou na analýzu potenciálu pro solární panely."""
    if not model_data:
        print("Žádná data k vizualizaci!")
        return
    
    # Extrahuj data
    faces, face_types, room_indices, heights, roof_types, is_solar_panel = extract_faces_from_rooms_and_shades(model_data)
    
    if not faces:
        print("Model neobsahuje žádné plochy k vizualizaci!")
        return
    
    # Barvy pro různé typy střech podle solárního potenciálu
    # Hodnoty jsou subjektivní odhady vhodnosti pro solární panely
    solar_potential_colors = {
        'flat': 'gold',       # Dobré pro solární panely s nastavitelným sklonem
        'gable': 'orange',    # Dobrý potenciál, pokud je správně orientovaná
        'hip': 'darkorange',  # Střední potenciál kvůli více plochám s různou orientací
        'pyramid': 'coral',   # Omezený potenciál kvůli malým plochám
        'shed': 'yellow',     # Výborné pokud je orientovaná na jih
        'mansard': 'orangered', # Omezený potenciál
        'butterfly': 'yellow', # Potenciálně dobré pro zachycení vody a solární využití
        'sawtooth': 'gold',    # Velmi dobré pro průmyslové budovy, často orientované na sever (okna) a jih (panely)
        'curved': 'coral',     # Limitovaný potenciál kvůli zakřivení
        'solar': 'lime',       # Již navržené pro solární využití
        'unknown': 'gray'
    }
    
    # Vytvoř 3D plot
    fig = plt.figure(figsize=(14, 12))
    ax = fig.add_subplot(111, projection='3d')
    
    # Přidej každou plochu do grafu s odpovídající barvou
    for i, (face, face_type, room_idx, height, roof_type, solar_panel) in enumerate(
        zip(faces, face_types, room_indices, heights, roof_types, is_solar_panel)):
        
        face_array = np.array(face)
        
        # Zobrazuj jen střechy a solární panely pro tuto analýzu
        if solar_panel:
            # Solární panely
            color = 'blue'
            alpha = 0.9
            edge_color = 'black'
            linewidth = 1
        elif face_type == 'shade' and roof_type != 'unknown':
            # Střešní plochy
            color = solar_potential_colors.get(roof_type, 'gray')
            alpha = 0.8
            edge_color = 'black'
            linewidth = 0.7
        elif face_type == 'roof_ceiling':
            # Stropy/střechy
            color = solar_potential_colors.get(roof_type, 'gray')
            alpha = 0.8
            edge_color = 'black'
            linewidth = 0.7
        else:
            # Ostatní plochy zobrazujeme šedě a poloprůhledně
            color = 'lightgray'
            alpha = 0.1
            edge_color = 'gray'
            linewidth = 0.2
        
        # Vytvoř polygon
        poly = Poly3DCollection([face_array], alpha=alpha)
        poly.set_facecolor(color)
        poly.set_edgecolor(edge_color)
        poly.set_linewidth(linewidth)
        ax.add_collection3d(poly)
    
    # Najdi hranice modelu
    all_pts = np.vstack([np.array(face) for face in faces])
    min_x, max_x = np.min(all_pts[:, 0]), np.max(all_pts[:, 0])
    min_y, max_y = np.min(all_pts[:, 1]), np.max(all_pts[:, 1])
    min_z, max_z = np.min(all_pts[:, 2]), np.max(all_pts[:, 2])
    
    # Nastav limity os
    ax.set_xlim(min_x, max_x)
    ax.set_ylim(min_y, max_y)
    ax.set_zlim(min_z, max_z)
    
    # Nastav popisky os
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z (výška)')
    
    # Přidej legendu pro potenciál solárního využití
    legend_elements = []
    
    # Legenda pro existující solární panely
    if any(is_solar_panel):
        legend_elements.append(mpatches.Patch(color='blue', label='Instalované solární panely'))
    
    # Legenda pro potenciál různých typů střech
    potential_levels = {
        'Výborný potenciál': ['shed', 'solar', 'sawtooth'],
        'Dobrý potenciál': ['flat', 'gable'],
        'Střední potenciál': ['hip', 'butterfly'],
        'Omezený potenciál': ['pyramid', 'mansard', 'curved']
    }
    
    # Vyfiltrujeme typy střech, které jsou skutečně v modelu
    used_roof_types = set(roof_types) - {'unknown'}
    
    # Přidáme do legendy jen relevantní kategorie
    for potential, roof_list in potential_levels.items():
        relevant_roofs = [rt for rt in roof_list if rt in used_roof_types]
        if relevant_roofs:
            # Použijeme barvu prvního střešního typu v seznamu pro reprezentaci kategorie
            color = solar_potential_colors.get(relevant_roofs[0], 'gray')
            legend_elements.append(mpatches.Patch(color=color, label=f"{potential} ({', '.join(relevant_roofs)})"))
    
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))
    
    # Nastav titulek
    plt.title('Analýza Solárního Potenciálu Střech')
    plt.tight_layout()
    
    # Ulož obrázek
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Vizualizace uložena do {output_file}")
    
    # Zobraz interaktivní graf
    plt.show()

def main():
    """Hlavní funkce pro vizualizaci HBJSON modelu."""
    # Cesta k HBJSON souboru
    model_path = os.path.join('output', 'city_model_solar.hbjson')
    
    if not os.path.exists(model_path):
        print(f"Soubor {model_path} neexistuje. Zkouším najít alternativní soubor...")
        # Pokus o nalezení jiného HBJSON souboru
        alt_path = os.path.join('output', 'city_model.hbjson')
        if os.path.exists(alt_path):
            print(f"Nalezen alternativní soubor: {alt_path}")
            model_path = alt_path
        else:
            print("Žádný HBJSON soubor nebyl nalezen. Nejprve generujte model pomocí create_city_hbjson.py.")
            return
    
    # Načtení modelu
    print(f"Načítám model z {model_path}...")
    model_data = read_hbjson(model_path)
    
    if not model_data:
        print("Nepodařilo se načíst model. Zkontrolujte, zda je soubor validní HBJSON.")
        return
    
    # Vytvoření výstupního adresáře pro vizualizace
    viz_dir = os.path.join('output', 'visualizations')
    if not os.path.exists(viz_dir):
        os.makedirs(viz_dir)
    
    # Vykreslení 3D modelu
    output_file_3d = os.path.join(viz_dir, 'city_model_3d.png')
    print("Generuji 3D vizualizaci...")
    plot_hbjson_model(model_data, output_file_3d)
    
    # Vykreslení půdorysu
    output_file_top = os.path.join(viz_dir, 'city_model_top.png')
    print("Generuji půdorys...")
    create_alternative_view(model_data, output_file_top, view_type='top')
    
    # Vykreslení čelního pohledu
    output_file_front = os.path.join(viz_dir, 'city_model_front.png')
    print("Generuji čelní pohled...")
    create_alternative_view(model_data, output_file_front, view_type='front')
    
    # Vykreslení analýzy solárního potenciálu
    output_file_solar = os.path.join(viz_dir, 'city_model_solar_analysis.png')
    print("Generuji analýzu solárního potenciálu...")
    create_solar_analysis_view(model_data, output_file_solar)
    
    print("Všechny vizualizace byly úspěšně vygenerovány!")

if __name__ == "__main__":
    main()