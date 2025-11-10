"""
Hybrid OCR Service - UNS-ClaudeJP 3.0
Servicio híbrido que combina Azure OCR y EasyOCR para máxima precisión
"""
import os
import logging
import base64
import time
from typing import Dict, Any, Optional, List
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.observability import (
    record_ocr_failure,
    record_ocr_request,
    trace_ocr_operation,
)

logger = logging.getLogger(__name__)


class HybridOCRService:
    """Servicio híbrido OCR que combina múltiples métodos para máxima precisión.

    Este servicio implementa una estrategia inteligente de procesamiento OCR que:
    - Intenta múltiples proveedores OCR (Azure, EasyOCR)
    - Combina resultados para máxima precisión
    - Maneja fallbacks automáticos
    - Proporciona scores de confianza

    Attributes:
        azure_available (bool): Indica si Azure OCR está disponible
        easyocr_available (bool): Indica si EasyOCR está disponible
        azure_service: Instancia del servicio Azure OCR
        easyocr_service: Instancia del servicio EasyOCR

    Examples:
        >>> service = HybridOCRService()
        >>> result = service.process_document_hybrid(image_bytes, "zairyu_card")
        >>> print(result['method_used'])  # 'hybrid', 'azure', or 'easyocr'
        >>> print(result['confidence_score'])  # 0.0 - 0.95
    """

    def __init__(self):
        """Inicializa el servicio híbrido OCR.

        Intenta inicializar ambos servicios OCR (Azure y EasyOCR) y registra
        cuáles están disponibles para su uso.
        """
        self.azure_available = False
        self.easyocr_available = False

        # Inicializar servicios disponibles
        self._init_services()

        logger.info(f"HybridOCRService inicializado - Azure: {self.azure_available}, EasyOCR: {self.easyocr_available}")
    
    def _init_services(self):
        """Inicializa los servicios OCR disponibles.

        Intenta importar y configurar Azure OCR y EasyOCR. Si alguno falla,
        registra un warning pero continúa con los servicios disponibles.

        Side Effects:
            - Establece self.azure_service y self.azure_available
            - Establece self.easyocr_service y self.easyocr_available
            - Registra mensajes de log sobre disponibilidad
        """
        # Inicializar Azure OCR
        try:
            from app.services.azure_ocr_service import azure_ocr_service
            self.azure_service = azure_ocr_service
            self.azure_available = True
            logger.info("Azure OCR service disponible")
        except ImportError as e:
            logger.warning(f"Azure OCR no disponible: {e}")
            self.azure_service = None

        # Inicializar EasyOCR
        try:
            from app.services.easyocr_service import easyocr_service
            self.easyocr_service = easyocr_service
            self.easyocr_available = easyocr_service.easyocr_available
            logger.info("EasyOCR service disponible")
        except ImportError as e:
            logger.warning(f"EasyOCR no disponible: {e}")
            self.easyocr_service = None
    
    def process_document_hybrid(self, image_data: bytes, document_type: str = "zairyu_card",
                               preferred_method: str = "auto") -> Dict[str, Any]:
        """Procesa un documento usando estrategia híbrida inteligente de OCR.

        Este método implementa una estrategia sofisticada que:
        1. Si preferred_method='azure': Usa Azure primero, EasyOCR como fallback
        2. Si preferred_method='easyocr': Usa EasyOCR primero, Azure como fallback
        3. Si preferred_method='auto': Ejecuta ambos y combina los mejores resultados

        La estrategia automática proporciona la máxima precisión al combinar
        resultados de múltiples proveedores OCR y completar campos faltantes.

        Args:
            image_data (bytes): Bytes de la imagen del documento a procesar
            document_type (str): Tipo de documento. Opciones:
                - "zairyu_card": Tarjeta de residencia
                - "rirekisho": Curriculum vitae japonés
                - "license": Licencia de conducir
                - "timer_card": Timer card (タイムカード)
            preferred_method (str): Estrategia de procesamiento. Opciones:
                - "azure": Priorizar Azure OCR
                - "easyocr": Priorizar EasyOCR
                - "auto": Estrategia híbrida automática (recomendado)

        Returns:
            Dict[str, Any]: Diccionario con estructura:
                {
                    "success": bool,  # True si al menos un método funcionó
                    "method_used": str,  # "hybrid", "azure", "easyocr", "none"
                    "confidence_score": float,  # 0.0-0.95 (mayor=mejor)
                    "azure_result": Dict | None,  # Resultado de Azure
                    "easyocr_result": Dict | None,  # Resultado de EasyOCR
                    "combined_data": Dict,  # Datos combinados finales
                    "document_type": str,
                    # Campos extraídos (según tipo de documento):
                    "name_kanji": str,
                    "birthday": str,
                    "nationality": str,
                    # ... más campos según document_type
                }

        Raises:
            Exception: Si ambos métodos OCR fallan completamente

        Examples:
            >>> # Estrategia automática (recomendado)
            >>> result = service.process_document_hybrid(
            ...     image_bytes,
            ...     document_type="zairyu_card",
            ...     preferred_method="auto"
            ... )
            >>> if result['success']:
            ...     print(f"Método usado: {result['method_used']}")
            ...     print(f"Confianza: {result['confidence_score']}")
            ...     print(f"Nombre: {result['combined_data']['name_kanji']}")

            >>> # Forzar uso de Azure con fallback a EasyOCR
            >>> result = service.process_document_hybrid(
            ...     image_bytes,
            ...     preferred_method="azure"
            ... )

        Note:
            - El score de confianza es mayor cuando se combinan múltiples métodos
            - La estrategia 'auto' es la más precisa pero más lenta
            - Si ningún método está disponible, success=False
        """
        try:
            logger.info(f"Procesando documento con método híbrido: {document_type}, preferencia: {preferred_method}")
            
            results = {
                "document_type": document_type,
                "success": False,
                "method_used": "none",
                "confidence_score": 0.0,
                "azure_result": None,
                "easyocr_result": None,
                "combined_data": {}
            }
            
            # Estrategia de procesamiento según preferencia
            if preferred_method == "azure" and self.azure_available:
                # Azure primero, EasyOCR como fallback
                azure_result = self._process_with_azure(image_data, document_type)
                results["azure_result"] = azure_result
                
                if azure_result.get("success"):
                    results["success"] = True
                    results["method_used"] = "azure"
                    results["combined_data"] = azure_result
                    results["confidence_score"] = 0.8  # Confianza base para Azure
                    
                    # Intentar mejorar con EasyOCR si hay campos faltantes
                    if self.easyocr_available and self._has_missing_fields(azure_result, document_type):
                        logger.info("Campos faltantes detectados, complementando con EasyOCR")
                        easyocr_result = self._process_with_easyocr(image_data, document_type)
                        results["easyocr_result"] = easyocr_result
                        
                        if easyocr_result.get("success"):
                            combined = self._combine_results(azure_result, easyocr_result, "azure")
                            results["combined_data"] = combined
                            results["confidence_score"] = 0.9  # Mayor confianza con combinación
                else:
                    # Si Azure falla, probar con EasyOCR
                    if self.easyocr_available:
                        easyocr_result = self._process_with_easyocr(image_data, document_type)
                        results["easyocr_result"] = easyocr_result
                        
                        if easyocr_result.get("success"):
                            results["success"] = True
                            results["method_used"] = "easyocr"
                            results["combined_data"] = easyocr_result
                            results["confidence_score"] = 0.7
            
            elif preferred_method == "easyocr" and self.easyocr_available:
                # EasyOCR primero, Azure como fallback
                easyocr_result = self._process_with_easyocr(image_data, document_type)
                results["easyocr_result"] = easyocr_result
                
                if easyocr_result.get("success"):
                    results["success"] = True
                    results["method_used"] = "easyocr"
                    results["combined_data"] = easyocr_result
                    results["confidence_score"] = 0.8
                    
                    # Intentar mejorar con Azure si hay campos faltantes
                    if self.azure_available and self._has_missing_fields(easyocr_result, document_type):
                        logger.info("Campos faltantes detectados, complementando con Azure")
                        azure_result = self._process_with_azure(image_data, document_type)
                        results["azure_result"] = azure_result
                        
                        if azure_result.get("success"):
                            combined = self._combine_results(easyocr_result, azure_result, "easyocr")
                            results["combined_data"] = combined
                            results["confidence_score"] = 0.9
                else:
                    # Si EasyOCR falla, probar con Azure
                    if self.azure_available:
                        azure_result = self._process_with_azure(image_data, document_type)
                        results["azure_result"] = azure_result
                        
                        if azure_result.get("success"):
                            results["success"] = True
                            results["method_used"] = "azure"
                            results["combined_data"] = azure_result
                            results["confidence_score"] = 0.7
            
            else:  # auto
                # Estrategia automática: probar ambos y combinar los mejores resultados
                azure_result = None
                easyocr_result = None
                
                # Ejecutar ambos servicios en paralelo si es posible
                if self.azure_available:
                    azure_result = self._process_with_azure(image_data, document_type)
                    results["azure_result"] = azure_result
                
                if self.easyocr_available:
                    easyocr_result = self._process_with_easyocr(image_data, document_type)
                    results["easyocr_result"] = easyocr_result
                
                # Evaluar resultados y seleccionar el mejor
                azure_success = azure_result and azure_result.get("success")
                easyocr_success = easyocr_result and easyocr_result.get("success")
                
                if azure_success and easyocr_success:
                    # Ambos funcionaron, combinar resultados
                    logger.info("Ambos métodos funcionaron, combinando resultados")
                    combined = self._combine_results(azure_result, easyocr_result, "auto")
                    results["success"] = True
                    results["method_used"] = "hybrid"
                    results["combined_data"] = combined
                    results["confidence_score"] = 0.95  # Máxima confianza con híbrido
                    
                elif azure_success:
                    # Solo Azure funcionó
                    logger.info("Solo Azure funcionó")
                    results["success"] = True
                    results["method_used"] = "azure"
                    results["combined_data"] = azure_result
                    results["confidence_score"] = 0.8
                    
                elif easyocr_success:
                    # Solo EasyOCR funcionó
                    logger.info("Solo EasyOCR funcionó")
                    results["success"] = True
                    results["method_used"] = "easyocr"
                    results["combined_data"] = easyocr_result
                    results["confidence_score"] = 0.8
                    
                else:
                    # Ninguno funcionó
                    logger.error("Ningún método OCR funcionó")
                    results["success"] = False
                    results["method_used"] = "none"
                    results["confidence_score"] = 0.0
            
            # Extraer foto con el servicio mejorado de detección facial
            if results["success"]:
                try:
                    from app.services.face_detection_service import face_detection_service
                    photo_data = face_detection_service.extract_face_from_document(image_data, document_type)
                    if photo_data:
                        results["combined_data"]["photo"] = photo_data
                        logger.info("Foto extraída exitosamente con servicio mejorado")
                except Exception as e:
                    logger.warning(f"Error extrayendo foto: {e}")
                    # Usar método original como fallback
                    try:
                        if self.azure_available:
                            photo_data = self.azure_service._extract_photo_from_document(image_data, document_type)
                            if photo_data:
                                results["combined_data"]["photo"] = photo_data
                    except Exception as e2:
                        logger.error(f"Error extrayendo foto con método original: {e2}")
            
            logger.info(f"Procesamiento híbrido completado - Método: {results['method_used']}, Éxito: {results['success']}")
            return results
            
        except Exception as e:
            logger.error(f"Error en procesamiento híbrido: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "method_used": "error",
                "confidence_score": 0.0
            }
    
    def _process_with_azure(self, image_data: bytes, document_type: str) -> Optional[Dict[str, Any]]:
        """Procesa documento con Azure Computer Vision OCR.

        Args:
            image_data (bytes): Imagen del documento en bytes
            document_type (str): Tipo de documento ("zairyu_card", "license", etc.)

        Returns:
            Optional[Dict[str, Any]]: Resultado de Azure OCR o None si no disponible.
                Estructura del diccionario de éxito:
                {
                    "success": True,
                    "raw_text": str,
                    "name_kanji": str,
                    # ... más campos extraídos
                }

        Raises:
            Exception: Si Azure OCR falla durante el procesamiento

        Note:
            - Registra métricas de observabilidad (duración, errores)
            - Crea archivo temporal para Azure OCR
            - Limpia archivo temporal después del procesamiento
        """
        if not self.azure_available:
            return None

        try:
            # Guardar imagen temporal para Azure
            temp_path = "/tmp/temp_azure_image.jpg"
            with open(temp_path, 'wb') as f:
                f.write(image_data)

            started = time.perf_counter()
            with trace_ocr_operation("azure.process_document", document_type, "azure"):
                result = self.azure_service.process_document(temp_path, document_type)
            duration = time.perf_counter() - started
            record_ocr_request(document_type=document_type, method="azure", duration_seconds=duration)

            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.remove(temp_path)

            return result

        except Exception as e:
            logger.error(f"Error procesando con Azure: {e}")
            record_ocr_failure(document_type=document_type, method="azure")
            return {"success": False, "error": str(e)}

    def _process_with_easyocr(self, image_data: bytes, document_type: str) -> Optional[Dict[str, Any]]:
        """Procesa documento con EasyOCR.

        Args:
            image_data (bytes): Imagen del documento en bytes
            document_type (str): Tipo de documento ("zairyu_card", "license", etc.)

        Returns:
            Optional[Dict[str, Any]]: Resultado de EasyOCR o None si no disponible.
                Estructura del diccionario de éxito:
                {
                    "success": True,
                    "raw_text": str,
                    "detections": int,
                    "ocr_method": "EasyOCR",
                    # ... campos extraídos
                }

        Raises:
            Exception: Si EasyOCR falla durante el procesamiento

        Note:
            - Registra métricas de observabilidad (duración, errores)
            - No requiere archivo temporal (procesa bytes directamente)
        """
        if not self.easyocr_available:
            return None

        try:
            started = time.perf_counter()
            with trace_ocr_operation("easyocr.process_document", document_type, "easyocr"):
                result = self.easyocr_service.process_document_with_easyocr(image_data, document_type)
            duration = time.perf_counter() - started
            record_ocr_request(document_type=document_type, method="easyocr", duration_seconds=duration)
            return result

        except Exception as e:
            logger.error(f"Error procesando con EasyOCR: {e}")
            record_ocr_failure(document_type=document_type, method="easyocr")
            return {"success": False, "error": str(e)}
    
    def _has_missing_fields(self, result: Dict[str, Any], document_type: str) -> bool:
        """Verifica si faltan campos críticos en el resultado OCR.

        Determina si un resultado OCR necesita ser complementado con otro método
        basándose en la presencia de campos críticos según el tipo de documento.

        Args:
            result (Dict[str, Any]): Resultado OCR a verificar
            document_type (str): Tipo de documento para determinar campos críticos

        Returns:
            bool: True si faltan más del 50% de campos críticos, False en caso contrario

        Note:
            Campos críticos por tipo de documento:
            - zairyu_card: name_kanji, birthday, nationality
            - rirekisho: name_kanji, birthday
            - license: name_kanji, license_number
            - otros: name_kanji
        """
        if not result or not result.get("success"):
            return True

        # Campos críticos por tipo de documento
        if document_type == "zairyu_card":
            critical_fields = ['name_kanji', 'birthday', 'nationality']
        elif document_type == "rirekisho":
            critical_fields = ['name_kanji', 'birthday']
        elif document_type == "license":
            critical_fields = ['name_kanji', 'license_number']
        else:
            critical_fields = ['name_kanji']

        missing_count = 0
        for field in critical_fields:
            if not result.get(field):
                missing_count += 1

        # Si faltan más del 50% de campos críticos
        return missing_count > len(critical_fields) // 2
    
    def _combine_results(self, primary_result: Dict[str, Any], secondary_result: Dict[str, Any],
                        primary_method: str) -> Dict[str, Any]:
        """Combina resultados de dos métodos OCR para máxima precisión.

        Implementa lógica inteligente para seleccionar los mejores valores de cada
        método OCR, completando campos faltantes y mejorando la calidad general.

        Args:
            primary_result (Dict[str, Any]): Resultado del método principal
            secondary_result (Dict[str, Any]): Resultado del método secundario
            primary_method (str): Método principal ('azure', 'easyocr', 'auto')

        Returns:
            Dict[str, Any]: Diccionario combinado con metadata adicional:
                {
                    # Todos los campos del primary_result
                    # Campos completados/mejorados del secondary_result
                    "ocr_method": "hybrid",
                    "primary_method": str,  # Método que se priorizó
                    "azure_available": bool,
                    "easyocr_available": bool
                }

        Note:
            Estrategias de combinación por tipo de campo:
            - Nombres: Prefiere el valor más largo y completo
            - Fechas: Prefiere formato japonés completo (YYYY年MM月DD日)
            - Nacionalidad: EasyOCR tiene mejor normalización
            - Números de tarjeta: Valida formato antes de seleccionar
            - Texto crudo: Combina ambos sin duplicados
        """
        try:
            combined = primary_result.copy()
            
            # Campos a combinar, priorizando el método principal
            fields_to_combine = [
                'name_kanji', 'name_kana', 'name_roman',
                'birthday', 'date_of_birth',
                'nationality',
                'address', 'current_address',
                'visa_status', 'residence_status',
                'zairyu_card_number', 'residence_card_number',
                'license_number',
                'raw_text'
            ]
            
            # Para cada campo, seleccionar el mejor valor
            for field in fields_to_combine:
                primary_value = primary_result.get(field)
                secondary_value = secondary_result.get(field)
                
                if not primary_value and secondary_value:
                    # Si el principal no tiene valor, usar el secundario
                    combined[field] = secondary_value
                    logger.info(f"Campo '{field}' complementado con {self._secondary_method(primary_method)}")
                elif primary_value and secondary_value:
                    # Ambos tienen valores, seleccionar el mejor
                    better_value = self._select_best_field_value(
                        field, primary_value, secondary_value, primary_method
                    )
                    if better_value != primary_value:
                        combined[field] = better_value
                        logger.info(f"Campo '{field}' mejorado con {self._secondary_method(primary_method)}")
            
            # Agregar metadata del procesamiento híbrido
            combined['ocr_method'] = 'hybrid'
            combined['primary_method'] = primary_method
            combined['azure_available'] = self.azure_available
            combined['easyocr_available'] = self.easyocr_available
            
            return combined
            
        except Exception as e:
            logger.error(f"Error combinando resultados: {e}")
            return primary_result
    
    def _select_best_field_value(self, field: str, primary_value: str, secondary_value: str,
                                primary_method: str) -> str:
        """Selecciona el mejor valor entre dos opciones para un campo específico.

        Aplica heurísticas según el tipo de campo para determinar cuál valor
        es más confiable o completo.

        Args:
            field (str): Nombre del campo a evaluar
            primary_value (str): Valor del método principal
            secondary_value (str): Valor del método secundario
            primary_method (str): Método principal usado

        Returns:
            str: El mejor valor seleccionado (puede ser primary o secondary)

        Note:
            Heurísticas aplicadas:
            - Nombres: Prefiere valores más largos (más completos)
            - Fechas: Prefiere formato japonés (YYYY年MM月DD日)
            - Nacionalidad: Prefiere método EasyOCR
            - Números tarjeta: Valida con regex antes de seleccionar
            - Texto crudo: Combina ambos valores sin duplicados
        """
        # Para nombres, preferir el más largo y completo
        if 'name' in field:
            if len(secondary_value) > len(primary_value):
                return secondary_value
        
        # Para fechas, validar formato
        elif 'birthday' in field or 'date' in field:
            # Preferir formato japonés completo (YYYY年MM月DD日)
            if '年' in secondary_value and '月' in secondary_value and '日' in secondary_value:
                if '年' not in primary_value or '月' not in primary_value or '日' not in primary_value:
                    return secondary_value
        
        # Para nacionalidad, usar mapeo normalizado
        elif 'nationality' in field:
            # EasyOCR usualmente tiene mejor normalización para japonés
            if primary_method == 'azure' and secondary_value:
                return secondary_value
        
        # Para números de tarjeta, validar formato
        elif 'card_number' in field or 'license_number' in field:
            # Preferir el que coincida con el patrón esperado
            import re
            
            if field == 'zairyu_card_number':
                zairyu_pattern = r'[A-Z]{2}\s?\d{8}\s?[A-Z]{2}'
                if re.search(zairyu_pattern, secondary_value) and not re.search(zairyu_pattern, primary_value):
                    return secondary_value
        
        # Para texto crudo, combinar ambos
        elif field == 'raw_text':
            # Combinar textos únicos
            primary_lines = set(primary_value.split('\n'))
            secondary_lines = set(secondary_value.split('\n'))
            combined_lines = primary_lines.union(secondary_lines)
            return '\n'.join(sorted(combined_lines, key=len, reverse=True))
        
        # Por defecto, mantener el valor principal
        return primary_value
    
    def _secondary_method(self, primary_method: str) -> str:
        """Obtiene el nombre legible del método OCR secundario.

        Args:
            primary_method (str): Nombre del método principal

        Returns:
            str: Nombre descriptivo del método secundario:
                - "EasyOCR" si primary_method="azure"
                - "Azure OCR" si primary_method="easyocr"
                - "OCR secundario" en otros casos
        """
        if primary_method == "azure":
            return "EasyOCR"
        elif primary_method == "easyocr":
            return "Azure OCR"
        else:
            return "OCR secundario"


# Instancia global del servicio
hybrid_ocr_service = HybridOCRService()

__all__ = ["HybridOCRService", "hybrid_ocr_service"]