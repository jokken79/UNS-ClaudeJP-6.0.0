"""
EasyOCR Service - UNS-ClaudeJP 3.0
Servicio especializado para OCR de documentos japoneses (Zairyu Cards, Rirekisho)
"""
import os
import logging
import base64
import re
from typing import Dict, Any, Optional, List, Tuple
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

# Importaciones condicionales para manejar dependencias opcionales
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    easyocr = None

logger = logging.getLogger(__name__)


class EasyOCRService:
    """Servicio especializado para OCR de documentos japoneses con EasyOCR"""
    
    def __init__(self):
        self.reader = None
        self.easyocr_available = False
        self.cv2_available = CV2_AVAILABLE
        
        # Inicializar EasyOCR
        self._init_easyocr()
        
        logger.info(f"EasyOCRService inicializado - EasyOCR: {self.easyocr_available}, OpenCV: {self.cv2_available}")
    
    def _init_easyocr(self):
        """Inicializar EasyOCR con soporte para japonés e inglés"""
        if not EASYOCR_AVAILABLE:
            logger.warning("EasyOCR no disponible - se usará fallback")
            return
            
        try:
            # Inicializar lector para japonés e inglés
            self.reader = easyocr.Reader(['ja', 'en'], gpu=False)
            self.easyocr_available = True
            logger.info("EasyOCR inicializado correctamente para japonés e inglés")
            
        except Exception as e:
            logger.error(f"Error inicializando EasyOCR: {e}")
            self.easyocr_available = False
    
    def preprocess_japanese_document(self, image: Image.Image) -> np.ndarray:
        """
        Preprocesamiento especializado para documentos japoneses de identificación
        """
        try:
            # Convertir a RGB si no lo está
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convertir a array numpy para OpenCV
            img_array = np.array(image)
            
            if not self.cv2_available:
                logger.warning("OpenCV no disponible, usando preprocesamiento básico")
                return img_array
            
            # Convertir a escala de grises
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Reducir ruido (importante para caracteres japoneses complejos)
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
            # Mejorar contraste con CLAHE (muy efectivo para texto japonés)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Binarización adaptativa para mejor separación de caracteres
            binary = cv2.adaptiveThreshold(
                enhanced, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
            logger.info("Preprocesamiento especializado para documentos japoneses completado")
            return binary
            
        except Exception as e:
            logger.error(f"Error en preprocesamiento: {e}")
            # Fallback a imagen original
            return np.array(image)
    
    def detect_card_contour(self, image_array: np.ndarray) -> Optional[np.ndarray]:
        """
        Detectar automáticamente los bordes de la tarjeta de identificación
        """
        if not self.cv2_available or cv2 is None:
            return None
            
        try:
            # Si es imagen en color, convertir a grises
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_array
            
            # Aplicar suavizado para reducir ruido
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Detectar bordes con Canny
            edges = cv2.Canny(blur, 75, 200)
            
            # Encontrar contornos
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Encontrar el contorno más grande (probablemente la tarjeta)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Aproximar a un polígono
            perimeter = cv2.arcLength(largest_contour, True)
            approximation = cv2.approxPolyDP(largest_contour, 0.02 * perimeter, True)
            
            # Verificar si es un cuadrilátero (tarjeta)
            if len(approximation) == 4:
                logger.info("Contorno de tarjeta detectado correctamente")
                return approximation
            
            return None
            
        except Exception as e:
            logger.error(f"Error detectando contorno de tarjeta: {e}")
            return None
    
    def perspective_correction(self, image_array: np.ndarray, contour: np.ndarray) -> np.ndarray:
        """
        Aplicar corrección de perspectiva para enderezar la tarjeta
        """
        if not self.cv2_available or cv2 is None:
            return image_array
            
        try:
            # Ordenar puntos del contorno
            points = contour.reshape(4, 2)
            rect = self._order_points(points)
            
            # Calcular dimensiones del rectángulo
            (tl, tr, br, bl) = rect
            
            # Ancho: distancia entre puntos superiores o inferiores
            width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            max_width = max(int(width_a), int(width_b))
            
            # Altura: distancia entre puntos izquierdos o derechos
            height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            max_height = max(int(height_a), int(height_b))
            
            # Destino para transformación de perspectiva
            dst = np.array([
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1]], dtype="float32")
            
            # Calcular matriz de transformación y aplicar
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(image_array, M, (max_width, max_height))
            
            logger.info(f"Corrección de perspectiva aplicada: {max_width}x{max_height}")
            return warped
            
        except Exception as e:
            logger.error(f"Error en corrección de perspectiva: {e}")
            return image_array
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Ordenar puntos del contorno en orden: top-left, top-right, bottom-right, bottom-left"""
        rect = np.zeros((4, 2), dtype="float32")
        
        # Sumar coordenadas
        s = pts.sum(axis=1)
        
        # Top-left: menor suma
        rect[0] = pts[np.argmin(s)]
        
        # Bottom-right: mayor suma
        rect[2] = pts[np.argmax(s)]
        
        # Diferencia entre coordenadas
        diff = np.diff(pts, axis=1)
        
        # Top-right: menor diferencia (x grande, y pequeño)
        rect[1] = pts[np.argmin(diff)]
        
        # Bottom-left: mayor diferencia (x pequeño, y grande)
        rect[3] = pts[np.argmax(diff)]
        
        return rect
    
    def process_document_with_easyocr(self, image_data: bytes, document_type: str = "zairyu_card") -> Dict[str, Any]:
        """
        Procesar documento usando EasyOCR con preprocesamiento especializado
        """
        try:
            if not self.easyocr_available:
                logger.error("EasyOCR no disponible")
                return {
                    "success": False,
                    "error": "EasyOCR no disponible",
                    "raw_text": "Error: EasyOCR not available"
                }
            
            logger.info(f"Procesando documento con EasyOCR: {document_type}")
            
            # Cargar imagen
            image = Image.open(BytesIO(image_data)).convert("RGB")
            img_array = np.array(image)
            
            # Detectar contorno de tarjeta y aplicar corrección de perspectiva
            contour = self.detect_card_contour(img_array)
            if contour is not None:
                img_array = self.perspective_correction(img_array, contour)
            
            # Preprocesamiento especializado para documentos japoneses
            processed_image = self.preprocess_japanese_document(Image.fromarray(img_array))
            
            # Ejecutar EasyOCR
            logger.info("Ejecutando EasyOCR...")
            results = self.reader.readtext(processed_image)
            
            # Extraer y procesar texto
            raw_text = "\n".join([result[1] for result in results])
            
            logger.info(f"EasyOCR completado - {len(results)} detecciones")
            logger.info(f"Texto extraído (longitud): {len(raw_text)} caracteres")
            logger.info(f"Preview: {raw_text[:200] if raw_text else 'EMPTY'}")
            
            # Parsear datos específicos según tipo de documento
            parsed_data = self._parse_easyocr_results(raw_text, results, document_type)
            
            # Aplicar alias comunes
            parsed_data = self._apply_common_aliases(parsed_data)
            
            return {
                "success": True,
                "raw_text": raw_text,
                "detections": len(results),
                "ocr_method": "EasyOCR",
                **parsed_data
            }
            
        except Exception as e:
            logger.error(f"Error procesando documento con EasyOCR: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "raw_text": f"Error: {str(e)}"
            }
    
    def _parse_easyocr_results(self, raw_text: str, results: List, document_type: str) -> Dict[str, Any]:
        """
        Parsear resultados de EasyOCR para documentos japoneses
        """
        import re
        
        data = {
            "document_type": document_type,
            "extracted_text": raw_text
        }
        
        if document_type == "zairyu_card":
            data.update(self._parse_zairyu_card_easyocr(raw_text, results))
        elif document_type == "rirekisho":
            data.update(self._parse_candidate_document_easyocr(raw_text, results))
        
        return data
    
    def _parse_zairyu_card_easyocr(self, raw_text: str, results: List) -> Dict[str, Any]:
        """
        Parseo especializado para Zairyu Cards usando resultados de EasyOCR
        """
        result = {}
        
        # Analizar cada detección con su confianza
        for detection in results:
            bbox, text, confidence = detection
            
            # Solo procesar detecciones con buena confianza
            if confidence < 0.5:
                continue
            
            text_clean = text.strip()
            
            # Buscar patrones específicos
            
            # Número de tarjeta Zairyu
            zairyu_pattern = r'[A-Z]{2}\s?\d{8}\s?[A-Z]{2}'
            if re.search(zairyu_pattern, text_clean):
                result['zairyu_card_number'] = re.search(zairyu_pattern, text_clean).group()
                logger.info(f"Zairyu card number detectado: {result['zairyu_card_number']}")
            
            # Nombre en japonés
            if any(keyword in text_clean for keyword in ['氏名', '名前', 'Name']):
                # Buscar nombre después de estos marcadores
                name_match = re.search(r'(?:氏名|名前|Name)[:\s]*(.+)', text_clean)
                if name_match:
                    name = name_match.group(1).strip()
                    if len(name) > 1:
                        result['name_kanji'] = name
                        logger.info(f"Nombre kanji detectado: {name}")
            
            # Fecha de nacimiento (formato japonés)
            date_pattern = r'(\d{4})[年/\-\.](\d{1,2})[月/\-\.](\d{1,2})日?'
            date_match = re.search(date_pattern, text_clean)
            if date_match and 'birthday' not in result:
                year, month, day = date_match.groups()
                try:
                    if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                        result['birthday'] = f"{year}年{int(month):02d}月{int(day):02d}日"
                        logger.info(f"Fecha de nacimiento detectada: {result['birthday']}")
                except ValueError:
                    pass
            
            # Nacionalidad
            if any(keyword in text_clean for keyword in ['国籍', 'Nationality', '地域']):
                nationality_match = re.search(r'(?:国籍|Nationality|地域)[:\s]*(.+)', text_clean)
                if nationality_match:
                    nationality = self._normalize_nationality(nationality_match.group(1).strip())
                    result['nationality'] = nationality
                    logger.info(f"Nacionalidad detectada: {nationality}")
            
            # Dirección
            if any(keyword in text_clean for keyword in ['住居地', 'Address', '住所']):
                addr_match = re.search(r'(?:住居地|Address|住所)[:\s]*(.+)', text_clean)
                if addr_match:
                    result['address'] = addr_match.group(1).strip()
                    logger.info(f"Dirección detectada: {result['address'][:50]}...")
            
            # Estado de residencia
            if any(keyword in text_clean for keyword in ['在留資格', 'Status', '資格']):
                status_match = re.search(r'(?:在留資格|Status|資格)[:\s]*(.+)', text_clean)
                if status_match:
                    status = status_match.group(1).strip()
                    # Limpiar texto inglés si existe
                    status = re.sub(r'\s+[A-Za-z]+.*$', '', status).strip()
                    if len(status) > 2:
                        result['visa_status'] = status
                        logger.info(f"Estado de visa detectado: {status}")
        
        # Parseo adicional del texto completo
        self._parse_full_text_zairyu(raw_text, result)
        
        return result
    
    def _parse_candidate_document_easyocr(self, raw_text: str, results: List) -> Dict[str, Any]:
        """
        Parseo especializado para Candidate Document (履歴書/Rirekisho) usando EasyOCR
        """
        result = {}
        
        # Implementación específica para Rirekisho
        # Por ahora, parseo básico
        lines = raw_text.split('\n')
        
        for line in lines:
            line_clean = line.strip()
            
            # Nombre
            if '氏名' in line_clean and 'name_kanji' not in result:
                name_match = re.search(r'氏名[:\s]*(.+)', line_clean)
                if name_match:
                    result['name_kanji'] = name_match.group(1).strip()
            
            # Fecha de nacimiento
            date_pattern = r'(\d{4})[年/\-\.](\d{1,2})[月/\-\.](\d{1,2})'
            date_match = re.search(date_pattern, line_clean)
            if date_match and 'birthday' not in result:
                year, month, day = date_match.groups()
                try:
                    if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                        result['birthday'] = f"{year}年{int(month):02d}月{int(day):02d}日"
                except ValueError:
                    pass
        
        return result
    
    def _parse_full_text_zairyu(self, raw_text: str, result: Dict[str, Any]):
        """
        Parseo adicional del texto completo para Zairyu Cards
        """
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        for line in lines:
            # Buscar nombre si no se encontró antes
            if 'name_kanji' not in result:
                # Patrones comunes de nombres en Zairyu cards
                if len(line) > 2 and len(line) < 20:
                    # Si contiene caracteres japoneses pero no números o símbolos especiales
                    if re.search(r'[ひらがなカタカナ漢字]', line) and not re.search(r'[0-9A-Za-z]{5,}', line):
                        if not any(skip in line for skip in ['在留', '国籍', '生年', '住所', '期間']):
                            result['name_kanji'] = line
                            logger.info(f"Nombre detectado del texto completo: {line}")
                            break
    
    def _normalize_nationality(self, nationality: str) -> str:
        """
        Normalizar nacionalidad a formato japonés
        """
        nationality_mapping = {
            'VIETNAM': 'ベトナム',
            'VIET NAM': 'ベトナム',
            'Vietnam': 'ベトナム',
            'Viet Nam': 'ベトナム',
            'vietnan': 'ベトナム',
            'VIETNAN': 'ベトナム',
            'PHILIPPINES': 'フィリピン',
            'Philippines': 'フィリピン',
            'CHINA': '中国',
            'China': '中国',
            'KOREA': '韓国',
            'Korea': '韓国',
            'BRAZIL': 'ブラジル',
            'Brazil': 'ブラジル',
            'PERU': 'ペルー',
            'Peru': 'ペルー',
        }
        
        # Intentar coincidencia exacta
        normalized = nationality_mapping.get(nationality.upper())
        if normalized:
            return normalized
        
        # Intentar coincidencia parcial
        for key, value in nationality_mapping.items():
            if key.lower() in nationality.lower() or nationality.lower() in key.lower():
                return value
        
        return nationality
    
    def _apply_common_aliases(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplicar alias comunes para compatibilidad con frontend
        """
        if not isinstance(data, dict):
            return data
        
        # Nombres
        if data.get('name_kanji') and not data.get('full_name_kanji'):
            data['full_name_kanji'] = data['name_kanji']
        
        # Fechas
        if data.get('birthday') and not data.get('date_of_birth'):
            data['date_of_birth'] = data['birthday']
        
        # Identificación
        if data.get('zairyu_card_number') and not data.get('residence_card_number'):
            data['residence_card_number'] = data['zairyu_card_number']
        
        # Estado
        if data.get('visa_status') and not data.get('residence_status'):
            data['residence_status'] = data['visa_status']
        
        # Dirección
        if data.get('address'):
            data.setdefault('current_address', data['address'])
        
        return data


# Instancia global del servicio
easyocr_service = EasyOCRService()

__all__ = ["EasyOCRService", "easyocr_service"]