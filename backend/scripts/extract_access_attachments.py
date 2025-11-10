"""
Extract attachments from Access 2007+ database
===============================================

Access 2007+ stores attachments in a hidden child table.
Format: {ParentTable}.{AttachmentField}

For T_履歴書 with field 写真, the table would be: T_履歴書.写真
"""
import pyodbc
from pathlib import Path
import sys

class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

def main():
    """Extract photos from Access attachments table"""

    # Configuration
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "BASEDATEJP" / "ユニバーサル企画㈱データベースv25.3.24_be.accdb"
    output_dir = project_root / "uploads" / "photos" / "candidates"

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{Colors.CYAN}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}>>> EXTRACTOR DE ATTACHMENTS DE ACCESS{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 80}{Colors.ENDC}\n")

    try:
        # Connect
        conn_str = f'DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print(f"{Colors.GREEN}[OK]{Colors.ENDC} Conectado a Access\n")

        # Try the attachment table
        attachment_table = 'T_履歴書.写真'

        print(f"{Colors.BLUE}[INFO]{Colors.ENDC} Intentando acceder a: {attachment_table}")

        try:
            # Query attachment table
            cursor.execute(f'SELECT * FROM [{attachment_table}] ORDER BY [写真]')

            # Get columns
            columns = [col[0] for col in cursor.description]
            print(f"{Colors.GREEN}[OK]{Colors.ENDC} Tabla encontrada!")
            print(f"{Colors.BLUE}[INFO]{Colors.ENDC} Columnas: {', '.join(columns)}\n")

            # Fetch all attachments
            rows = cursor.fetchall()
            total = len(rows)

            print(f"{Colors.BLUE}[INFO]{Colors.ENDC} Total attachments: {total}\n")

            if total == 0:
                print(f"{Colors.YELLOW}[AVISO]{Colors.ENDC} No hay attachments")
                return 0

            # Process attachments
            stats = {'success': 0, 'failed': 0}

            print(f"{Colors.BLUE}[INFO]{Colors.ENDC} Extrayendo fotos...")

            for idx, row in enumerate(rows, 1):
                # Show progress
                if idx % 100 == 0:
                    progress = (idx / total) * 100
                    bar_len = 40
                    filled = int(bar_len * idx / total)
                    bar = '#' * filled + '-' * (bar_len - filled)
                    print(f"\r{Colors.CYAN}[{bar}]{Colors.ENDC} {progress:.1f}% ({idx}/{total})", end='', flush=True)

                # Build dict from row
                data = {}
                for i, col in enumerate(columns):
                    data[col] = row[i]

                # Get attachment data
                # Common column names for attachment data
                file_data = None
                filename = None
                parent_id = None

                for key in data:
                    if 'FileData' in key or 'data' in key.lower():
                        file_data = data[key]
                    if 'FileName' in key or 'name' in key.lower():
                        filename = data[key]
                    if key == '写真':  # Parent ID
                        parent_id = data[key]

                if not file_data:
                    # Try to get data from any binary column
                    for key, value in data.items():
                        if isinstance(value, bytes) and len(value) > 1000:
                            file_data = value
                            break

                if file_data and isinstance(file_data, bytes):
                    try:
                        # Determine extension
                        if file_data.startswith(b'\xff\xd8\xff'):
                            ext = 'jpg'
                        elif file_data.startswith(b'\x89PNG'):
                            ext = 'png'
                        elif file_data.startswith(b'BM'):
                            ext = 'bmp'
                        else:
                            ext = 'jpg'

                        # Generate filename
                        if filename:
                            save_name = filename
                        elif parent_id:
                            save_name = f"candidate_{parent_id}.{ext}"
                        else:
                            save_name = f"candidate_{idx}.{ext}"

                        # Save file
                        filepath = output_dir / save_name
                        with open(filepath, 'wb') as f:
                            f.write(file_data)

                        stats['success'] += 1
                    except Exception as e:
                        stats['failed'] += 1
                else:
                    stats['failed'] += 1

            # Final progress
            bar = '#' * 40
            print(f"\r{Colors.CYAN}[{bar}]{Colors.ENDC} 100.0% ({total}/{total})\n")

            # Summary
            print(f"\n{Colors.CYAN}{'=' * 80}{Colors.ENDC}")
            print(f"{Colors.BOLD}=== RESUMEN ==={Colors.ENDC}")
            print(f"{Colors.CYAN}{'=' * 80}{Colors.ENDC}\n")

            print(f"{Colors.BOLD}Total attachments:{Colors.ENDC} {total}")
            print(f"{Colors.BOLD}Fotos extraidas:{Colors.ENDC} {stats['success']}")
            print(f"{Colors.BOLD}Fallidas:{Colors.ENDC} {stats['failed']}")

            if stats['success'] > 0:
                print(f"\n{Colors.GREEN}[OK]{Colors.ENDC} Fotos guardadas en: {output_dir}")

            print(f"\n{Colors.CYAN}{'=' * 80}{Colors.ENDC}\n")

            conn.close()
            return stats['success']

        except pyodbc.Error as e:
            print(f"{Colors.RED}[ERROR]{Colors.ENDC} No se pudo acceder a la tabla de attachments")
            print(f"{Colors.BLUE}[INFO]{Colors.ENDC} Error: {e}")
            print(f"\n{Colors.YELLOW}[AVISO]{Colors.ENDC} Las fotos pueden no estar almacenadas como Attachments en esta base de datos")
            print(f"{Colors.BLUE}[INFO]{Colors.ENDC} Intentando metodo alternativo...\n")

            # Try alternative: maybe photos are in a different field
            return 0

    except Exception as e:
        print(f"\n{Colors.RED}[ERROR]{Colors.ENDC} {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    extracted = main()
    sys.exit(0 if extracted > 0 else 1)
