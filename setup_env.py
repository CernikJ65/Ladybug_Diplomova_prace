import subprocess
import sys
import os
import platform

def run_command(command):
    """Spustí příkaz v příkazové řádce a vypíše výstup."""
    print(f"Spouštím: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"CHYBA: {result.stderr}")
    return result.returncode

def main():
    # Určení cesty k Python
    python_exe = sys.executable
    
    # Vytvoření virtuálního prostředí
    venv_name = "ladybug_env"
    print(f"Vytvářím virtuální prostředí {venv_name}...")
    
    # Kontrola existence prostředí
    if os.path.exists(venv_name):
        print(f"Prostředí {venv_name} již existuje. Přeskakuji vytváření.")
    else:
        run_command(f"{python_exe} -m venv {venv_name}")
    
    # Určení příkazu pro aktivaci
    if platform.system() == "Windows":
        activate_cmd = f"{venv_name}\\Scripts\\activate"
        pip_path = f"{venv_name}\\Scripts\\pip"
    else:
        activate_cmd = f"source {venv_name}/bin/activate"
        pip_path = f"{venv_name}/bin/pip"
    
    print(f"Virtuální prostředí vytvořeno v: {os.path.abspath(venv_name)}")
    print(f"Pro aktivaci použijte: {activate_cmd}")
    
    # Instalace balíčků
    print("\nInstalace potřebných balíčků...")
    packages = [
        "ladybug-core",
        "ladybug-geometry",
        "ladybug-radiance",
        "honeybee-core",
        "honeybee-energy",
        "honeybee-radiance"
    ]
    
    for package in packages:
        print(f"\nInstaluji {package}...")
        if platform.system() == "Windows":
            run_command(f"{venv_name}\\Scripts\\pip install {package}")
        else:
            # Pro Linux/macOS je potřeba spustit v novém procesu s aktivovaným prostředím
            run_command(f"cd {os.getcwd()} && {activate_cmd} && pip install {package}")
    
    print("\nInstalace dokončena!")
    print(f"\nPRO MANUÁLNÍ AKTIVACI PROSTŘEDÍ:")
    print(f"Windows CMD: {venv_name}\\Scripts\\activate")
    print(f"Windows PowerShell: .\\{venv_name}\\Scripts\\Activate.ps1")
    print(f"Linux/macOS: source {venv_name}/bin/activate")

if __name__ == "__main__":
    main()