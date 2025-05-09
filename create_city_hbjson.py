import honeybee_radiance
import inspect
import sys

def analyze_module(module, indent=0, max_depth=3, current_depth=0, visited=None):
    """Rekurzivně analyzuje a vypisuje obsah modulu a jeho podmodulů."""
    if visited is None:
        visited = set()
    
    # Předejdeme nekonečné rekurzi
    if module.__name__ in visited or current_depth > max_depth:
        return
    
    visited.add(module.__name__)
    prefix = ' ' * indent
    
    print(f"{prefix}MODUL: {module.__name__}")
    
    # Získáme veškeré atributy modulu
    for name in dir(module):
        if name.startswith('_'):  # Přeskočíme privátní atributy
            continue
        
        try:
            attr = getattr(module, name)
            
            # Zobrazíme typ atributu
            if inspect.ismodule(attr):
                print(f"{prefix}  + PODMODUL: {name}")
                # Rekurzivně analyzujeme podmoduly, ale jen pokud jsou součástí honeybee_radiance
                if attr.__name__.startswith('honeybee_radiance'):
                    analyze_module(attr, indent + 4, max_depth, current_depth + 1, visited)
            
            elif inspect.isclass(attr):
                print(f"{prefix}  + TŘÍDA: {name}")
                
                # Vypíšeme metody třídy
                for method_name in dir(attr):
                    if not method_name.startswith('_'):
                        try:
                            method = getattr(attr, method_name)
                            if inspect.isfunction(method) or inspect.ismethod(method):
                                print(f"{prefix}      - metoda: {method_name}")
                        except:
                            pass
            
            elif inspect.isfunction(attr):
                print(f"{prefix}  + FUNKCE: {name}")
                
            else:
                print(f"{prefix}  + ATRIBUT: {name} (typ: {type(attr).__name__})")
        
        except Exception as e:
            print(f"{prefix}  + CHYBA při analýze {name}: {e}")

# Analyzujeme celý modul honeybee_radiance
print("KOMPLETNÍ PŘEHLED HONEYBEE_RADIANCE:\n")
analyze_module(honeybee_radiance)

# Vypíšeme také všechny dostupné submoduly
print("\nSEZNAM VŠECH SUBMODULŮ:\n")
modules = [name for name, module in sys.modules.items() 
           if name.startswith('honeybee_radiance') and name != 'honeybee_radiance']
for name in sorted(modules):
    print(f"  - {name}")