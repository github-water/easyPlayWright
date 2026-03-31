"""
component 层 - 系统内部编排组件
职责：将抓取结果持久化输出（JSON/CSV），属于系统内部处理流程。
C4 定位：Component（系统边界内）
"""
import json
import csv
from typing import List, Dict
from pathlib import Path
from datetime import datetime

from pkg.logger import logger
from pkg.utils import ensure_dir


class ExporterComponent:
    """导出组件：将数据保存为 JSON / CSV 文件"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        ensure_dir(str(self.output_dir))

    def to_json(self, data:List[Dict], filename: str = "") -> str:
        """保存为 JSON 文件"""
        filename = filename or f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"[Component] 已导出 JSON: {path} (共 {len(data)} 条)")
        return str(path)

    def to_csv(self, data: List[Dict], filename: str = "") -> str:
        """保存为 CSV 文件"""
        if not data:
            logger.warning("[Component] 数据为空，跳过 CSV 导出")
            return ""

        filename = filename or f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = self.output_dir / filename
        fieldnames = list(data[0].keys())

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"[Component] 已导出 CSV: {path} (共 {len(data)} 条)")
        return str(path)
