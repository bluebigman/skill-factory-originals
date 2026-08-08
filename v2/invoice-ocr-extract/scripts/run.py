#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
票据识别字段提取与结构化输出工具
支持从发票图片/PDF中提取关键字段，输出结构化CSV表格
支持批量处理、并行加速、结果缓存
"""

import os
import sys
import csv
import json
import re
import argparse
import hashlib
import tempfile
import time
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 尝试导入可选依赖
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


class InvoiceExtractor:
    """发票字段提取器 - 基于规则和简单图像处理"""
    
    # 发票关键字段定义（包含置信度字段）
    FIELDS = [
        "invoice_no",      # 发票号码
        "invoice_date",    # 开票日期
        "buyer_name",      # 购买方名称
        "buyer_tax_id",    # 购买方税号
        "seller_name",     # 销售方名称
        "seller_tax_id",   # 销售方税号
        "amount",          # 金额
        "tax",             # 税额
        "total",           # 价税合计
        "confidence",      # 整体置信度
    ]
    
    # 字段正则表达式模式 - 优化容错，支持换行和空白符
    FIELD_PATTERNS = {
        "invoice_no": r'发票号码[：:\s]*([0-9]{8,20})',
        "invoice_date": r'开票日期[：:\s]*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})',
        "buyer_name": r'购买方[：:\s]*名称[：:\s]*([\s\S]{2,50}?)(?=\s*(?:纳税人识别号|地址|电话|$))',
        "buyer_tax_id": r'购买方[：:\s]*纳税人识别号[：:\s]*([0-9A-Z]{15,20})',
        "seller_name": r'销售方[：:\s]*名称[：:\s]*([\s\S]{2,50}?)(?=\s*(?:纳税人识别号|地址|电话|$))',
        "seller_tax_id": r'销售方[：:\s]*纳税人识别号[：:\s]*([0-9A-Z]{15,20})',
        "amount": r'金额[：:\s]*([0-9,]+\.?[0-9]*)',
        "tax": r'税额[：:\s]*([0-9,]+\.?[0-9]*)',
        "total": r'价税合计[（(]小写[)）][：:\s]*[¥￥]?([0-9,]+\.?[0-9]*)',
    }
    
    # 缓存TTL（秒）- 24小时
    CACHE_TTL = 24 * 60 * 60
    
    def __init__(self, cache_dir: Optional[str] = None, max_workers: int = 4, use_cache: bool = True):
        self.results = []
        self.failures = []
        self.max_workers = max_workers
        self.use_cache = use_cache
        # 缓存目录
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "invoice_ocr_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 文件锁字典用于并发控制（实际加锁）
        self._file_locks: Dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()
        
        # 检查依赖
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """检查必要依赖是否可用"""
        if not HAS_PIL:
            logger.warning("PIL未安装，图片处理功能受限")
        if not HAS_PDF:
            logger.warning("pdfplumber未安装，PDF解析功能受限")
        if not HAS_TESSERACT:
            logger.warning("pytesseract未安装，OCR功能受限")
    
    def _get_file_lock(self, file_path: str) -> threading.Lock:
        """获取文件锁（实际加锁）"""
        with self._locks_lock:
            if file_path not in self._file_locks:
                self._file_locks[file_path] = threading.Lock()
            return self._file_locks[file_path]
    
    def _get_file_hash(self, file_path: str) -> str:
        """计算文件内容哈希用于缓存"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败: {e}")
            return ""
    
    def _get_cache_path(self, file_hash: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{file_hash}.json")
    
    def _is_cache_valid(self, cache_path: str) -> bool:
        """检查缓存是否有效（TTL）"""
        try:
            mtime = os.path.getmtime(cache_path)
            age = time.time() - mtime
            return age < self.CACHE_TTL
        except Exception:
            return False
    
    def _load_from_cache(self, file_hash: str) -> Optional[Dict]:
        """从缓存加载结果（带损坏降级）"""
        if not self.use_cache:
            return None
        cache_path = self._get_cache_path(file_hash)
        if os.path.exists(cache_path) and self._is_cache_valid(cache_path):
            try:
                # 使用文件锁保护读取
                lock = self._get_file_lock(cache_path)
                with lock:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                # 验证缓存数据完整性
                if 'fields' in data and 'status' in data:
                    return data
                else:
                    logger.warning(f"缓存数据不完整: {cache_path}")
                    return None
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"缓存文件损坏，降级处理: {e}")
                # 删除损坏的缓存文件
                try:
                    os.remove(cache_path)
                except OSError:
                    pass
                return None
            except Exception as e:
                logger.warning(f"读取缓存失败: {e}")
                return None
        return None
    
    def _save_to_cache(self, file_hash: str, data: Dict) -> None:
        """保存结果到缓存（原子写入+文件锁+损坏降级）"""
        if not self.use_cache:
            return
        cache_path = self._get_cache_path(file_hash)
        
        # 获取文件锁（实际加锁）
        lock = self._get_file_lock(cache_path)
        with lock:
            try:
                # 原子写入：先写临时文件，再os.replace
                temp_path = cache_path + f'.tmp.{os.getpid()}.{threading.get_ident()}'
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(temp_path, cache_path)
            except Exception as e:
                logger.warning(f"保存缓存失败: {e}")
                # 清理临时文件
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except OSError:
                    pass
    
    def _clean_text(self, text: str) -> str:
        """清洗OCR文本"""
        if not text:
            return ""
        
        # 统一全半角
        text = text.replace('：', ':').replace('（', '(').replace('）', ')')
        text = text.replace('，', ',').replace('。', '.')
        
        # 去除多余空格（保留换行符用于正则匹配）
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 去除特殊字符（保留换行符）
        text = re.sub(r'[^\u4e00-\u9fff\uFF00-\uFFEFa-zA-Z0-9:()（）¥￥,.\-\s\n]', '', text)
        
        return text.strip()
    
    def _normalize_text_for_regex(self, text: str) -> str:
        """将文本中的换行符替换为空格，用于正则匹配"""
        if not text:
            return ""
        # 将换行符替换为空格，同时保留其他空白符
        return re.sub(r'\n+', ' ', text)
    
    def _validate_field(self, field_name: str, value: Any) -> Tuple[Any, float]:
        """验证字段值并返回置信度"""
        if value is None:
            return None, 0.0
        
        confidence = 0.9
        
        if field_name == "invoice_no":
            if not re.match(r'^[0-9]{8,20}$', str(value)):
                confidence = 0.3
        elif field_name == "invoice_date":
            # 验证日期格式
            date_str = str(value)
            if re.match(r'^[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日$', date_str):
                try:
                    year = int(date_str[:4])
                    month = int(date_str[5:date_str.index('月')])
                    day = int(date_str[date_str.index('月')+1:date_str.index('日')])
                    if not (1 <= month <= 12 and 1 <= day <= 31):
                        confidence = 0.3
                except ValueError:
                    confidence = 0.3
            elif re.match(r'^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}$', date_str):
                try:
                    datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    confidence = 0.3
            else:
                confidence = 0.3
        elif field_name in ["buyer_tax_id", "seller_tax_id"]:
            # 税号验证（15-20位数字或字母）
            if not re.match(r'^[0-9A-Z]{15,20}$', str(value)):
                confidence = 0.3
        elif field_name in ["amount", "tax", "total"]:
            try:
                amount = float(value)
                if amount < 0:
                    confidence = 0.3
            except (ValueError, TypeError):
                confidence = 0.3
        elif field_name in ["buyer_name", "seller_name"]:
            # 名称验证（至少2个字符）
            if len(str(value)) < 2:
                confidence = 0.3
        
        return value, confidence
    
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """从PDF提取文本（实际使用pdfplumber）"""
        if not HAS_PDF:
            raise RuntimeError("pdfplumber未安装，无法解析PDF")
        
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            raise RuntimeError(f"PDF解析失败: {e}")
        
        return self._clean_text(text)
    
    def _extract_text_from_image(self, image_path: str) -> str:
        """从图片提取文本（OCR）"""
        if not HAS_PIL:
            raise RuntimeError("PIL未安装，无法处理图片")
        if not HAS_TESSERACT:
            raise RuntimeError("pytesseract未安装，无法进行OCR")
        
        try:
            # 打开图片并预处理
            with Image.open(image_path) as img:
                # 转换为灰度图
                img = img.convert('L')
                # 二值化处理
                img = img.point(lambda x: 0 if x < 128 else 255, '1')
                # OCR识别
                text = pytesseract.image_to_string(img, lang='chi_sim+eng')
                return self._clean_text(text)
        except Exception as e:
            raise RuntimeError(f"图片处理失败: {e}")
    
    def _extract_fields(self, text: str) -> Dict[str, Dict[str, Any]]:
        """从文本中提取字段（含置信度计算）"""
        fields = {}
        confidence_sum = 0.0
        confidence_count = 0
        
        # 将换行符替换为空格，避免正则匹配失败
        normalized_text = self._normalize_text_for_regex(text)
        
        # 多模式正则备选（增加容错）
        multi_patterns = {
            "invoice_no": [
                r'发票号码[：:\s]*([0-9]{8,20})',
                r'发票号[：:\s]*([0-9]{8,20})',
                r'NO[.:\s]*([0-9]{8,20})',
            ],
            "invoice_date": [
                r'开票日期[：:\s]*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})',
                r'日期[：:\s]*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})',
            ],
            "buyer_name": [
                r'购买方[：:\s]*名称[：:\s]*([\s\S]{2,50}?)(?=\s*(?:纳税人识别号|地址|电话|$))',
                r'购买方[：:\s]*([\s\S]{2,50}?)(?=\s*(?:纳税人识别号|地址|电话|$))',
            ],
            "buyer_tax_id": [
                r'购买方[：:\s]*纳税人识别号[：:\s]*([0-9A-Z]{15,20})',
                r'纳税人识别号[：:\s]*([0-9A-Z]{15,20})',
            ],
            "seller_name": [
                r'销售方[：:\s]*名称[：:\s]*([\s\S]{2,50}?)(?=\s*(?:纳税人识别号|地址|电话|$))',
                r'销售方[：:\s]*([\s\S]{2,50}?)(?=\s*(?:纳税人识别号|地址|电话|$))',
            ],
            "seller_tax_id": [
                r'销售方[：:\s]*纳税人识别号[：:\s]*([0-9A-Z]{15,20})',
                r'纳税人识别号[：:\s]*([0-9A-Z]{15,20})',
            ],
            "amount": [
                r'金额[：:\s]*([¥￥]?\s*[0-9,]+\.?[0-9]*)',
                r'金额[：:\s]*([0-9,]+\.?[0-9]*)',
                r'([¥￥]\s*[0-9,]+\.?[0-9]*)',
            ],
            "tax": [
                r'税额[：:\s]*([¥￥]?\s*[0-9,]+\.?[0-9]*)',
                r'税额[：:\s]*([0-9,]+\.?[0-9]*)',
                r'([¥￥]\s*[0-9,]+\.?[0-9]*)',
            ],
            "total": [
                r'价税合计[（(]小写[)）][：:\s]*[¥￥]?\s*([0-9,]+\.?[0-9]*)',
                r'价税合计[（(]小写[)）][：:\s]*([0-9,]+\.?[0-9]*)',
                r'价税合计[：:\s]*[¥￥]?\s*([0-9,]+\.?[0-9]*)',
            ],
        }
        
        for field_name in self.FIELDS:
            if field_name == "confidence":
                continue
                
            patterns = multi_patterns.get(field_name, [self.FIELD_PATTERNS.get(field_name, '')])
            matched = False
            
            for pattern in patterns:
                if not pattern:
                    continue
                match = re.search(pattern, normalized_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    # 清理值
                    if field_name in ['amount', 'tax', 'total']:
                        # 去除货币符号和千分位逗号
                        value = value.replace('¥', '').replace('￥', '').replace(',', '')
                        try:
                            value = float(value)
                        except ValueError:
                            value = None
                    elif field_name in ['buyer_name', 'seller_name']:
                        # 清理名称中的多余空格和换行
                        value = re.sub(r'[\s\n]+', '', value)
                    
                    #
