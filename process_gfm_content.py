#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Flavored Markdown 内容处理脚本

这个脚本用于处理JSON文件中的GitHub Flavored Markdown (GFM) 内容，
将其转换为纯文本格式，去除所有格式字符、超链接等。

功能特性：
- 读取JSON文件中的PR数据
- 将GFM格式的body字段转换为纯文本
- 清理多余的空白字符和格式
- 保持合理的段落结构
- 支持批量处理多个PR记录
- 提供详细的处理统计信息

使用方法：
    python process_gfm_content.py input.json output.json
"""

import json
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import unquote

import markdown
from bs4 import BeautifulSoup


class GFMProcessor:
    """GitHub Flavored Markdown 处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.md = markdown.Markdown(
            extensions=[
                'markdown.extensions.fenced_code',
                'markdown.extensions.tables',
                'markdown.extensions.codehilite',
                'markdown.extensions.toc',
                'markdown.extensions.nl2br'
            ]
        )
    
    def gfm_to_text(self, gfm_content: str) -> str:
        """
        将GitHub Flavored Markdown转换为纯文本
        
        Args:
            gfm_content: GFM格式的内容
            
        Returns:
            转换后的纯文本内容
        """
        if not gfm_content or not gfm_content.strip():
            return ""
        
        try:
            # 将GFM转换为HTML
            html_content = self.md.convert(gfm_content)
            
            # 使用BeautifulSoup解析HTML并提取文本
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 处理特殊元素
            self._process_special_elements(soup)
            
            # 提取纯文本
            text_content = soup.get_text(separator='\n', strip=True)
            
            # 清理文本
            cleaned_text = self._clean_text(text_content)
            
            return cleaned_text
            
        except Exception as e:
            print(f"警告：处理GFM内容时出错: {e}")
            # 如果转换失败，返回原始内容的简单清理版本
            return self._simple_clean(gfm_content)
    
    def _process_special_elements(self, soup: BeautifulSoup):
        """处理HTML中的特殊元素"""
        
        # 处理代码块，保留内容但添加标识
        for code_block in soup.find_all(['pre', 'code']):
            if code_block.name == 'pre':
                # 代码块，保留内容
                code_block.replace_with(f"\n[代码块]\n{code_block.get_text()}\n[/代码块]\n")
            else:
                # 行内代码，保留内容
                code_block.replace_with(f"`{code_block.get_text()}`")
        
        # 处理链接，只保留文本内容
        for link in soup.find_all('a'):
            link_text = link.get_text().strip()
            if link_text:
                link.replace_with(link_text)
            else:
                link.replace_with("")
        
        # 处理图片，保留alt文本或忽略
        for img in soup.find_all('img'):
            alt_text = img.get('alt', '').strip()
            if alt_text:
                img.replace_with(f"[图片: {alt_text}]")
            else:
                img.replace_with("[图片]")
        
        # 处理列表项，保持结构
        for li in soup.find_all('li'):
            li_text = li.get_text().strip()
            if li_text:
                li.replace_with(f"• {li_text}")
        
        # 处理表格，转换为简单文本格式
        for table in soup.find_all('table'):
            table_text = self._table_to_text(table)
            table.replace_with(table_text)
    
    def _table_to_text(self, table: BeautifulSoup) -> str:
        """将HTML表格转换为文本格式"""
        rows = []
        for tr in table.find_all('tr'):
            cells = [td.get_text().strip() for td in tr.find_all(['td', 'th'])]
            if cells:
                rows.append(" | ".join(cells))
        
        if rows:
            return "\n".join(rows) + "\n"
        return ""
    
    def _clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 清理行首行尾空白
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        
        # 重新组合文本
        cleaned_text = '\n'.join(lines)
        
        return cleaned_text.strip()
    
    def _simple_clean(self, text: str) -> str:
        """简单的文本清理（作为备用方案）"""
        if not text:
            return ""
        
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除Markdown链接格式，保留文本
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # 移除Markdown图片格式
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
        
        # 移除Markdown格式字符
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # 粗体
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # 斜体
        text = re.sub(r'`([^`]+)`', r'\1', text)        # 行内代码
        
        # 移除标题标记
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # 移除列表标记
        text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # 清理空白
        return self._clean_text(text)


class JSONProcessor:
    """JSON文件处理器"""
    
    def __init__(self, gfm_processor: GFMProcessor):
        """初始化处理器"""
        self.gfm_processor = gfm_processor
    
    def process_json_file(self, input_file: str, output_file: str) -> Dict[str, Any]:
        """
        处理JSON文件中的GFM内容
        
        Args:
            input_file: 输入JSON文件路径
            output_file: 输出JSON文件路径
            
        Returns:
            处理统计信息
        """
        print(f"正在读取文件: {input_file}")
        
        try:
            # 尝试读取为JSON Lines格式（每行一个JSON对象）
            records = []
            with open(input_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        records.append(record)
                    except json.JSONDecodeError as e:
                        print(f"警告：第{line_num}行JSON解析失败: {e}")
                        continue
        except Exception as e:
            print(f"错误：无法读取JSON文件: {e}")
            return {"error": str(e)}
        
        # 处理数据
        processed_data = []
        stats = {
            "total_records": len(records),
            "processed_records": 0,
            "skipped_records": 0,
            "errors": 0
        }
        
        for i, record in enumerate(records, 1):
            print(f"正在处理记录 {i}/{len(records)}...")
            
            try:
                processed_record = self._process_record(record)
                if processed_record:
                    processed_data.append(processed_record)
                    stats["processed_records"] += 1
                else:
                    stats["skipped_records"] += 1
            except Exception as e:
                print(f"警告：处理记录 {i} 时出错: {e}")
                stats["errors"] += 1
                # 保留原始记录
                processed_data.append(record)
        
        # 保存处理后的数据
        print(f"正在保存到文件: {output_file}")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for record in processed_data:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            print("文件保存成功！")
        except Exception as e:
            print(f"错误：无法保存文件: {e}")
            stats["error"] = str(e)
        
        return stats
    
    def _process_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理单个记录"""
        if not isinstance(record, dict):
            return None
        
        # 创建记录副本
        processed_record = record.copy()
        
        # 处理prData.body字段
        if 'prData' in processed_record and isinstance(processed_record['prData'], dict):
            pr_data = processed_record['prData']
            if 'body' in pr_data and pr_data['body']:
                print(f"  处理PR #{pr_data.get('prID', 'unknown')} 的body内容")
                pr_data['body'] = self.gfm_processor.gfm_to_text(pr_data['body'])
        
        # 处理comments中的body字段
        if 'comments' in processed_record and isinstance(processed_record['comments'], dict):
            comments = processed_record['comments']
            if 'nodes' in comments and isinstance(comments['nodes'], list):
                for comment in comments['nodes']:
                    if isinstance(comment, dict) and 'body' in comment:
                        comment['body'] = self.gfm_processor.gfm_to_text(comment['body'])
        
        # 处理reviewThreads中的comments
        if 'reviewThreads' in processed_record and isinstance(processed_record['reviewThreads'], dict):
            review_threads = processed_record['reviewThreads']
            if 'nodes' in review_threads and isinstance(review_threads['nodes'], list):
                for thread in review_threads['nodes']:
                    if isinstance(thread, dict) and 'comments' in thread:
                        thread_comments = thread['comments']
                        if 'nodes' in thread_comments and isinstance(thread_comments['nodes'], list):
                            for comment in thread_comments['nodes']:
                                if isinstance(comment, dict) and 'body' in comment:
                                    comment['body'] = self.gfm_processor.gfm_to_text(comment['body'])
        
        return processed_record


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description="处理JSON文件中的GitHub Flavored Markdown内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python process_gfm_content.py input.json output.json
  python process_gfm_content.py "output/jabref_merged_prs copy.json" "output/processed_prs.json"
        """
    )
    
    parser.add_argument(
        'input_file',
        help='输入JSON文件路径'
    )
    
    parser.add_argument(
        'output_file',
        help='输出JSON文件路径'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细处理信息'
    )
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not Path(args.input_file).exists():
        print(f"错误：输入文件不存在: {args.input_file}")
        sys.exit(1)
    
    # 创建处理器
    gfm_processor = GFMProcessor()
    json_processor = JSONProcessor(gfm_processor)
    
    # 处理文件
    print("开始处理GitHub Flavored Markdown内容...")
    stats = json_processor.process_json_file(args.input_file, args.output_file)
    
    # 显示统计信息
    print("\n处理完成！统计信息:")
    print(f"  总记录数: {stats.get('total_records', 0)}")
    print(f"  成功处理: {stats.get('processed_records', 0)}")
    print(f"  跳过记录: {stats.get('skipped_records', 0)}")
    print(f"  错误数量: {stats.get('errors', 0)}")
    
    if 'error' in stats:
        print(f"  处理错误: {stats['error']}")
        sys.exit(1)
    
    print(f"\n处理后的文件已保存到: {args.output_file}")


if __name__ == "__main__":
    main() 