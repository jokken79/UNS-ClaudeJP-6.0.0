#!/usr/bin/env python3
"""
Script de validación de imports
Se ejecuta al iniciar el contenedor backend
PREVIENE: Que el contenedor arranque con imports rotos
"""

import sys
import os
import importlib
from pathlib import Path

# Asegurarse de estar en el directorio correcto
script_dir = Path(__file__).parent.parent
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

# Colores para terminal
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def validate_imports():
    """Valida que todos los módulos críticos se puedan importar"""

    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}  VALIDACIÓN DE IMPORTS - Backend{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    # Lista de módulos críticos a validar
    critical_modules = [
        # API Routers
        ("app.api.auth", "Authentication router"),
        ("app.api.candidates", "Candidates router"),
        ("app.api.employees", "Employees router"),
        ("app.api.factories", "Factories router"),
        ("app.api.timer_cards", "Timer cards router"),
        ("app.api.salary", "Salary router"),
        ("app.api.requests", "Requests router"),
        ("app.api.dashboard", "Dashboard router"),
        ("app.api.database", "Database router"),
        ("app.api.azure_ocr", "Azure OCR router"),
        ("app.api.import_export", "Import/Export router"),
        ("app.api.monitoring", "Monitoring router"),
        ("app.api.notifications", "Notifications router"),
        ("app.api.reports", "Reports router"),
        ("app.api.settings", "Settings router"),
        ("app.api.pages", "Pages router"),  # ← El que causó el problema

        # Core modules
        ("app.core.config", "Configuration"),
        ("app.core.database", "Database connection"),
        ("app.core.logging", "Logging setup"),
        ("app.core.middleware", "Middleware"),
        ("app.core.observability", "Observability"),

        # Main app
        ("app.main", "Main FastAPI app"),
    ]

    errors = []
    success_count = 0

    print(f"Validando {len(critical_modules)} módulos críticos...\n")

    for module_name, description in critical_modules:
        try:
            # Intentar importar el módulo
            module = importlib.import_module(module_name)

            # Validaciones adicionales
            if 'api' in module_name and module_name != 'app.main':
                # Los routers deben tener un atributo 'router'
                if not hasattr(module, 'router'):
                    raise AttributeError(f"Módulo '{module_name}' no tiene atributo 'router'")

            print(f"{GREEN}✓{RESET} {description:30s} ({module_name})")
            success_count += 1

        except ModuleNotFoundError as e:
            error_msg = f"Módulo no encontrado: {module_name}\n  Detalle: {str(e)}"
            errors.append(error_msg)
            print(f"{RED}✗{RESET} {description:30s} ({module_name})")
            print(f"  {RED}ERROR:{RESET} {str(e)}")

        except AttributeError as e:
            error_msg = f"Error en {module_name}\n  Detalle: {str(e)}"
            errors.append(error_msg)
            print(f"{RED}✗{RESET} {description:30s} ({module_name})")
            print(f"  {RED}ERROR:{RESET} {str(e)}")

        except Exception as e:
            error_msg = f"Error inesperado en {module_name}\n  Detalle: {str(e)}"
            errors.append(error_msg)
            print(f"{RED}✗{RESET} {description:30s} ({module_name})")
            print(f"  {RED}ERROR:{RESET} {str(e)}")

    # Resultado final
    print(f"\n{BLUE}{'='*60}{RESET}")

    if errors:
        print(f"{RED}✗ VALIDACIÓN FALLIDA{RESET}")
        print(f"\n{RED}Se encontraron {len(errors)} errores:{RESET}\n")
        for i, error in enumerate(errors, 1):
            print(f"{RED}[{i}]{RESET} {error}")
        print(f"\n{YELLOW}ACCIÓN REQUERIDA:{RESET}")
        print(f"  1. Revisa los errores listados arriba")
        print(f"  2. Corrige los imports incorrectos")
        print(f"  3. Reinicia el contenedor: docker restart uns-claudejp-backend")
        print(f"\n{BLUE}{'='*60}{RESET}\n")
        return False
    else:
        print(f"{GREEN}✓ VALIDACIÓN EXITOSA{RESET}")
        print(f"  {success_count}/{len(critical_modules)} módulos importados correctamente")
        print(f"\n{BLUE}{'='*60}{RESET}\n")
        return True


if __name__ == "__main__":
    # Ejecutar validación
    success = validate_imports()

    # Exit code
    sys.exit(0 if success else 1)
