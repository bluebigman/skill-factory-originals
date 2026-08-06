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
    
    # 发票关键字段定义
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
    ]
    
    # 字段正则表达式模式
    FIELD_PATTERNS = {
        "invoice_no": r'发票号码[：:\s]*([0-9]{8,20})',
        "invoice_date": r'开票日期[：:\s]*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})',
        "buyer_name": r'购买方[：:\s]*名称[：:\s]*([^\n]{2,50})',
        "buyer_tax_id": r'购买方[：:\s]*纳税人识别号[：:\s]*([0-9A-Z]{15,20})',
        "seller_name": r'销售方[：:\s]*名称[：:\s]*([^\n]{2,50})',
        "seller_tax_id": r'销售方[：:\s]*纳税人识别号[：:\s]*([0-9A-Z]{15,20})',
        "amount": r'金额[：:\s]*([0-9,]+\.?[0-9]*)',
        "tax": r'税额[：:\s]*([0-9,]+\.?[0-9]*)',
        "total": r'价税合计[（(]小写[)）][：:\s]*[¥￥]?([0-9,]+\.?[0-9]*)',
    }
    
    def __init__(self, cache_dir: Optional[str] = None, max_workers: int = 4, use_cache: bool = True):
        self.results = []
        self.failures = []
        self.max_workers = max_workers
        self.use_cache = use_cache
        # 缓存目录
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "invoice_ocr_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
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
    
    def _get_file_hash(self, file_path: str) -> str:
        """计算文件哈希用于缓存"""
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
    
    def _load_from_cache(self, file_hash: str) -> Optional[Dict]:
        """从缓存加载结果"""
        if not self.use_cache:
            return None
        cache_path = self._get_cache_path(file_hash)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"读取缓存失败: {e}")
        return None
    
    def _save_to_cache(self, file_hash: str, data: Dict) -> None:
        """保存结果到缓存"""
        if not self.use_cache:
            return
        cache_path = self._get_cache_path(file_hash)
        try:
            # 原子写入
            temp_path = cache_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, cache_path)
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")
    
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """从PDF提取文本"""
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
        
        return text
    
    def _extract_text_from_image(self, image_path: str) -> str:
        """从图片提取文本"""
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
                return text
        except Exception as e:
            raise RuntimeError(f"图片处理失败: {e}")
    
    def _extract_fields(self, text: str) -> Dict[str, Dict[str, Any]]:
        """从文本中提取字段"""
        fields = {}
        
        for field_name in self.FIELDS:
            pattern = self.FIELD_PATTERNS.get(field_name)
            if pattern:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    # 清理值
                    if field_name in ['amount', 'tax', 'total']:
                        value = value.replace(',', '')
                        try:
                            value = float(value)
                            confidence = 0.9
                        except ValueError:
                            confidence = 0.5
                    else:
                        confidence = 0.9
                    
                    fields[field_name] = {
                        "value": value,
                        "confidence": confidence
                    }
                else:
                    # 尝试关键词匹配
                    keyword_patterns = {
                        "invoice_no": r'([0-9]{8,20})',
                        "invoice_date": r'([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})',
                        "buyer_name": r'购买方[：:\s]*([^\n]{2,50})',
                        "buyer_tax_id": r'纳税人识别号[：:\s]*([0-9A-Z]{15,20})',
                        "seller_name": r'销售方[：:\s]*([^\n]{2,50})',
                        "seller_tax_id": r'纳税人识别号[：:\s]*([0-9A-Z]{15,20})',
                        "amount": r'([0-9,]+\.?[0-9]*)',
                        "tax": r'([0-9,]+\.?[0-9]*)',
                        "total": r'[¥￥]?([0-9,]+\.?[0-9]*)',
                    }
                    
                    keyword_match = re.search(keyword_patterns.get(field_name, ''), text, re.IGNORECASE)
                    if keyword_match:
                        value = keyword_match.group(1).strip()
                        if field_name in ['amount', 'tax', 'total']:
                            value = value.replace(',', '')
                            try:
                                value = float(value)
                                confidence = 0.7
                            except ValueError:
                                confidence = 0.5
                        else:
                            confidence = 0.7
                        
                        fields[field_name] = {
                            "value": value,
                            "confidence": confidence
                        }
                    else:
                        # 默认中等置信度
                        fields[field_name] = {
                            "value": None,
                            "confidence": 0.5
                        }
            else:
                fields[field_name] = {
                    "value": None,
                    "confidence": 0.5
                }
        
        return fields
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """处理单个文件"""
        file_path = str(file_path)
        file_ext = Path(file_path).suffix.lower()
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {
                "file_name": os.path.basename(file_path),
                "status": "error",
                "error_code": "E001",
                "error_message": "文件不存在"
            }
        
        # 检查文件格式
        if file_ext not in ['.jpg', '.jpeg', '.png', '.pdf']:
            return {
                "file_name": os.path.basename(file_path),
                "status": "error",
                "error_code": "E002",
                "error_message": f"不支持的文件格式: {file_ext}"
            }
        
        # 计算文件哈希
        file_hash = self._get_file_hash(file_path)
        if not file_hash:
            return {
                "file_name": os.path.basename(file_path),
                "status": "error",
                "error_code": "E001",
                "error_message": "文件读取失败"
            }
        
        # 尝试从缓存加载
        cached_result = self._load_from_cache(file_hash)
        if cached_result:
            logger.info(f"从缓存加载: {os.path.basename(file_path)}")
            return cached_result
        
        try:
            # 提取文本
            if file_ext == '.pdf':
                text = self._extract_text_from_pdf(file_path)
            else:
                text = self._extract_text_from_image(file_path)
            
            if not text.strip():
                return {
                    "file_name": os.path.basename(file_path),
                    "status": "error",
                    "error_code": "E003",
                    "error_message": "未提取到文本内容"
                }
            
            # 提取字段
            fields = self._extract_fields(text)
            
            # 构建结果
            result = {
                "file_name": os.path.basename(file_path),
                "file_path": file_path,
                "status": "success",
                "fields": fields,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
            # 保存到缓存
            self._save_to_cache(file_hash, result)
            
            return result
            
        except RuntimeError as e:
            error_code = "E003"
            if "pdfplumber" in str(e):
                error_code = "E004"
            elif "PIL" in str(e) or "pytesseract" in str(e):
                error_code = "E003"
            elif "图片处理" in str(e):
                error_code = "E005"
            
            return {
                "file_name": os.path.basename(file_path),
                "status": "error",
                "error_code": error_code,
                "error_message": str(e)
            }
        except Exception as e:
            return {
                "file_name": os.path.basename(file_path),
                "status": "error",
                "error_code": "E005",
                "error_message": f"处理失败: {str(e)}"
            }
    
    def process_batch(self, input_path: str) -> Tuple[List[Dict], List[Dict]]:
        """批量处理文件"""
        input_path = Path(input_path)
        files = []
        
        if input_path.is_file():
            files = [input_path]
        elif input_path.is_dir():
            # 收集支持的格式文件
            for ext in ['.jpg', '.jpeg', '.png', '.pdf']:
                files.extend(input_path.glob(f"*{ext}"))
                files.extend(input_path.glob(f"*{ext.upper()}"))
        else:
            raise ValueError(f"输入路径不存在: {input_path}")
        
        if not files:
            logger.warning(f"未找到支持的文件: {input_path}")
            return [], []
        
        logger.info(f"找到 {len(files)} 个文件待处理")
        
        results = []
        failures = []
        
        # 并行处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {executor.submit(self.process_file, f): f for f in files}
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    if result["status"] == "success":
                        results.append(result)
                    else:
                        failures.append(result)
                except Exception as e:
                    failures.append({
                        "file_name": os.path.basename(str(file_path)),
                        "status": "error",
                        "error_code": "E005",
                        "error_message": f"处理异常: {str(e)}"
                    })
        
        # 排序结果
        results.sort(key=lambda x: x["file_name"])
        failures.sort(key=lambda x: x["file_name"])
        
        return results, failures
    
    def export_csv(self, results: List[Dict], output_path: str) -> None:
        """导出CSV格式结果"""
        if not results:
            logger.warning("没有结果可导出")
            return
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        
        # 构建CSV数据
        csv_data = []
        for result in results:
            row = {
                "file_name": result["file_name"],
                "status": result["status"]
            }
            
            # 添加字段
            for field_name in self.FIELDS:
                field_data = result.get("fields", {}).get(field_name, {})
                row[field_name] = field_data.get("value", "")
                row[f"{field_name}_confidence"] = field_data.get("confidence", 0.5)
            
            csv_data.append(row)
        
        # 写入CSV（原子写入）
        temp_path = output_path + '.tmp'
        try:
            with open(temp_path, 'w', newline='', encoding='utf-8-sig') as f:
                if csv_data:
                    fieldnames = list(csv_data[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_data)
            os.replace(temp_path, output_path)
            logger.info(f"CSV已导出: {output_path}")
        except Exception as e:
            logger.error(f"CSV导出失败: {e}")
            raise
    
    def export_json(self, results: List[Dict], output_path: str) -> None:
        """导出JSON格式结果"""
        if not results:
            logger.warning("没有结果可导出")
            return
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        
        # 写入JSON（原子写入）
        temp_path = output_path + '.tmp'
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, output_path)
            logger.info(f"JSON已导出: {output_path}")
        except Exception as e:
            logger.error(f"JSON导出失败: {e}")
            raise
    
    def export_failures(self, failures: List[Dict], output_path: str) -> None:
        """导出失败清单"""
        if not failures:
            logger.info("没有失败记录")
            return
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        
        # 写入失败清单（原子写入）
        temp_path = output_path + '.tmp'
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                for failure in failures:
                    f.write(f"{failure['file_name']}\t{failure.get('error_code', 'E005')}\t{failure.get('error_message', '未知错误')}\n")
            os.replace(temp_path, output_path)
            logger.info(f"失败清单已导出: {output_path}")
        except Exception as e:
            logger.error(f"失败清单导出失败: {e}")
            raise


def run_selftest() -> int:
    """运行自检程序"""
    logger.info("开始自检...")
    
    # 创建测试目录
    test_dir = tempfile.mkdtemp(prefix="invoice_ocr_test_")
    test_output = os.path.join(test_dir, "output")
    os.makedirs(test_output, exist_ok=True)
    
    try:
        # 创建测试文件
        test_file = os.path.join(test_dir, "test_invoice.txt")
        test_content = """
        增值税普通发票
        发票号码：12345678
        开票日期：2024年1月15日
        购买方名称：测试公司
        购买方纳税人识别号：91110108MA01XXXXX
        销售方名称：供应商公司
        销售方纳税人识别号：91110105MA02XXXXX
        金额：1000.00
        税额：130.00
        价税合计（小写）：¥1130.00
        """
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # 创建提取器实例
        extractor = InvoiceExtractor(cache_dir=os.path.join(test_dir, "cache"), use_cache=False)
        
        # 测试字段提取
        fields = extractor._extract_fields(test_content)
        
        # 断言关键字段
        assert fields["invoice_no"]["value"] == "12345678", "发票号码提取失败"
        assert fields["invoice_date"]["value"] == "2024年1月15日", "开票日期提取失败"
        assert fields["buyer_name"]["value"] == "测试公司", "购买方名称提取失败"
        assert fields["seller_name"]["value"] == "供应商公司", "销售方名称提取失败"
        assert fields["amount"]["value"] == 1000.0, "金额提取失败"
        assert fields["tax"]["value"] == 130.0, "税额提取失败"
        assert fields["total"]["value"] == 1130.0, "价税合计提取失败"
        
        # 测试置信度
        assert fields["invoice_no"]["confidence"] >= 0.8, "置信度设置错误"
        
        # 测试CSV导出
        test_result = {
            "file_name": "test.txt",
            "status": "success",
            "fields": fields
        }
        csv_path = os.path.join(test_output, "test.csv")
        extractor.export_csv([test_result], csv_path)
        assert os.path.exists(csv_path), "CSV导出失败"
        
        # 测试JSON导出
        json_path = os.path.join(test_output, "test.json")
        extractor.export_json([test_result], json_path)
        assert os.path.exists(json_path), "JSON导出失败"
        
        # 测试失败处理
        failure_result = {
            "file_name": "nonexistent.pdf",
            "status": "error",
            "error_code": "E001",
            "error_message": "文件不存在"
        }
        failure_path = os.path.join(test_output, "failures.txt")
        extractor.export_failures([failure_result], failure_path)
        assert os.path.exists(failure_path), "失败清单导出失败"
        
        logger.info("✅ 所有自检项通过")
        return 0
        
    except AssertionError as e:
        logger.error(f"❌ 自检失败: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ 自检异常: {e}")
        return 1
    finally:
        # 清理测试目录
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="票据识别字段提取与结构化输出工具")
    parser.add_argument("--input", type=str, help="输入文件或目录路径")
    parser.add_argument("--output", type=str, default="./output", help="输出目录路径")
    parser.add_argument("--format", type=str, choices=["csv", "json"], default="csv", help="输出格式")
    parser.add_argument("--workers", type=int, default=4, help="并行工作线程数")
    parser.add_argument("--no-cache", action="store_true", help="禁用缓存")
    parser.add_argument("--selftest", action="store_true", help="运行自检程序")
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        sys.exit(run_selftest())
    
    # 检查输入参数
    if not args.input:
        parser.error("请指定 --input 参数")
    
    # 创建提取器
    extractor = InvoiceExtractor(
        max_workers=args.workers,
        use_cache=not args.no_cache
    )
    
    try:
        # 批量处理
        results, failures = extractor.process_batch(args.input)
        
        # 输出统计信息
        logger.info(f"处理完成: 成功 {len(results)} 个, 失败 {len(failures)} 个")
        
        # 导出结果
        if results:
            # 确保输出目录存在
            os.makedirs(args.output, exist_ok=True)
            
            # 生成时间戳
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            
            if args.format == "csv":
                output_path = os.path.join(args.output, f"invoice_results_{timestamp}.csv")
                extractor.export_csv(results, output_path)
            else:
                output_path = os.path.join(args.output, f"invoice_results_{timestamp}.json")
                extractor.export_json(results, output_path)
            
            logger.info(f"结果已保存: {output_path}")
        
        # 导出失败清单
        if failures:
            failure_path = os.path.join(args.output, f"invoice_failures_{timestamp}.txt")
            extractor.export_failures(failures, failure_path)
            logger.info(f"失败清单已保存: {failure_path}")
        
        # 返回状态码
        if failures:
            logger.warning(f"有 {len(failures)} 个文件处理失败，请查看失败清单")
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"处理失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
