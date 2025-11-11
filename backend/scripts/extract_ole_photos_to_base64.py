"""
Extract OLE photos from Access database and save as base64 JSON
================================================================

Access stores photos as OLE objects (LONGCHAR type).
This script extracts them and saves as base64 data URLs.

Based on successful implementation from v5.2
"""
import pyodbc
import base64
import json
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'extract_ole_photos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def extract_ole_image(ole_data):
    """
    Extract image data from OLE object

    OLE format has a header that needs to be stripped.
    The actual image data starts after the OLE header.
    """
    if not ole_data or not isinstance(ole_data, (bytes, str)):
        return None

    # Convert string to bytes if needed
    if isinstance(ole_data, str):
        try:
            ole_data = ole_data.encode('latin-1')
        except:
            return None

    # OLE objects often start with specific headers
    # Try to find JPEG signature (FFD8FF)
    jpeg_start = ole_data.find(b'\xff\xd8\xff')
    if jpeg_start >= 0:
        return ole_data[jpeg_start:]

    # Try to find PNG signature (89504E47)
    png_start = ole_data.find(b'\x89PNG')
    if png_start >= 0:
        return ole_data[png_start:]

    # Try to find BMP signature (424D)
    bmp_start = ole_data.find(b'BM')
    if bmp_start >= 0 and bmp_start < 100:  # BMP should be near start
        return ole_data[bmp_start:]

    # If no signature found, try common OLE offsets
    common_offsets = [0, 20, 40, 78, 300]
    for offset in common_offsets:
        if offset < len(ole_data):
            chunk = ole_data[offset:]
            # Check if it looks like image data
            if chunk.startswith(b'\xff\xd8\xff') or chunk.startswith(b'\x89PNG') or chunk.startswith(b'BM'):
                return chunk

    return None

def image_to_data_url(image_data):
    """Convert image bytes to base64 data URL"""
    if not image_data:
        return None

    # Determine MIME type
    if image_data.startswith(b'\xff\xd8\xff'):
        mime_type = 'image/jpeg'
    elif image_data.startswith(b'\x89PNG'):
        mime_type = 'image/png'
    elif image_data.startswith(b'BM'):
        mime_type = 'image/bmp'
    elif image_data.startswith(b'GIF'):
        mime_type = 'image/gif'
    else:
        mime_type = 'image/jpeg'  # Default

    # Convert to base64
    b64_data = base64.b64encode(image_data).decode('ascii')

    # Create data URL
    data_url = f"data:{mime_type};base64,{b64_data}"

    return data_url

def main():
    """Extract all photos from Access database as base64"""

    # Configuration
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "BASEDATEJP" / "ユニバーサル企画㈱データベースv25.3.24_be.accdb"
    output_file = project_root / "config" / "access_photo_mappings.json"

    logger.info("=" * 80)
    logger.info("EXTRACTOR DE FOTOS OLE DESDE ACCESS -> BASE64")
    logger.info("=" * 80)
    logger.info(f"Base de datos: {db_path.name}")
    logger.info(f"Archivo salida: {output_file}")
    logger.info("")

    if not db_path.exists():
        logger.error(f"Base de datos no encontrada: {db_path}")
        return 0

    try:
        # Connect to Access
        conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            f'DBQ={db_path};'
        )
        logger.info("Conectando a Access...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        logger.info("Conexión exitosa\n")

        # Query with photos
        logger.info("Consultando candidatos con fotos...")
        cursor.execute("SELECT 履歴書ID, 氏名, 写真 FROM T_履歴書 WHERE 写真 IS NOT NULL ORDER BY 履歴書ID")

        # Fetch all rows
        rows = cursor.fetchall()
        total = len(rows)
        logger.info(f"Encontrados: {total} candidatos con fotos\n")

        if total == 0:
            logger.warning("No hay fotos para extraer")
            return 0

        # Extract photos
        logger.info("Extrayendo fotos y convirtiendo a base64...")
        mappings = {}
        stats = {'success': 0, 'failed': 0, 'skipped': 0}

        for idx, row in enumerate(rows, 1):
            rirekisho_id = str(row[0])
            name = row[1]
            photo_data = row[2]

            # Show progress
            if idx % 100 == 0 or idx == total:
                progress = (idx / total) * 100
                logger.info(f"  Procesando: {idx}/{total} ({progress:.1f}%)")

            # Skip if no data
            if not photo_data:
                stats['skipped'] += 1
                continue

            try:
                # Extract image from OLE
                image_data = extract_ole_image(photo_data)

                if image_data:
                    # Convert to base64 data URL
                    data_url = image_to_data_url(image_data)

                    if data_url:
                        mappings[rirekisho_id] = data_url
                        stats['success'] += 1

                        # Log first few for verification
                        if idx <= 5:
                            logger.info(f"  ✓ ID {rirekisho_id}: {len(data_url)} bytes (base64)")
                    else:
                        stats['failed'] += 1
                else:
                    stats['failed'] += 1

            except Exception as e:
                logger.error(f"  ✗ Error procesando ID {rirekisho_id}: {e}")
                stats['failed'] += 1

        logger.info("")

        # Save to JSON
        logger.info("Guardando mappings a JSON...")
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "source": "ole_extraction_from_access",
            "method": "ole_object_parser_with_base64",
            "statistics": {
                "total_mappings": len(mappings),
                "success": stats['success'],
                "failed": stats['failed'],
                "skipped": stats['skipped']
            },
            "mappings": mappings
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        # Get file size
        file_size_mb = output_file.stat().st_size / (1024 * 1024)

        # Summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("RESUMEN")
        logger.info("=" * 80)
        logger.info(f"Total candidatos: {total}")
        logger.info(f"Fotos extraídas: {stats['success']}")
        logger.info(f"Fallidas: {stats['failed']}")
        logger.info(f"Sin datos: {stats['skipped']}")
        logger.info(f"")
        logger.info(f"Archivo generado: {output_file}")
        logger.info(f"Tamaño: {file_size_mb:.2f} MB")
        logger.info("=" * 80)
        logger.info("")

        if stats['success'] > 0:
            logger.info("✓ EXTRACCIÓN EXITOSA")
            logger.info("")
            logger.info("PRÓXIMOS PASOS:")
            logger.info("1. Reiniciar servicios: scripts\\STOP.bat && scripts\\START.bat")
            logger.info("2. Las fotos se importarán automáticamente durante el inicio")
            logger.info("3. Verificar en: http://localhost:3000/candidates")
        else:
            logger.warning("⚠ No se pudieron extraer fotos")

        logger.info("")

        conn.close()
        return stats['success']

    except Exception as e:
        logger.error(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    extracted = main()
    exit(0 if extracted > 0 else 1)
