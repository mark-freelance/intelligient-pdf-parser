import os
import hashlib
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import base64

from loguru import logger
from anthropic import Anthropic
import PyPDF2

class ClaudePDFProcessor:
    def __init__(self, api_key: str = os.environ['ANTHROPIC_API_KEY']):
        self.client = Anthropic(api_key=api_key)
        self._setup_logger()
        self.cache_dir = Path("./cache")
        self.cache_dir.mkdir(exist_ok=True)
        
    def _setup_logger(self):
        """设置logger配置"""
        logger.add(
            "logs/claude_pdf_{time}.log",
            rotation="500 MB",
            retention="10 days",
            level="INFO"
        )

    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件的SHA256哈希值作为唯一标识"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _get_cache_path(self, file_hash: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{file_hash}.json"

    def _read_from_cache(self, file_hash: str) -> Optional[Dict]:
        """从缓存中读取结果"""
        cache_path = self._get_cache_path(file_hash)
        if cache_path.exists():
            logger.info(f"Found cached result for file hash: {file_hash}")
            import json
            with open(cache_path) as f:
                return json.load(f)
        return None

    def _save_to_cache(self, file_hash: str, result: Dict):
        """保存结果到缓存"""
        cache_path = self._get_cache_path(file_hash)
        import json
        with open(cache_path, "w") as f:
            json.dump(result, f)
        logger.info(f"Saved result to cache for file hash: {file_hash}")

    def _split_pdf_content(self, pdf_content: bytes, chunk_size: int = 80) -> List[bytes]:
        """将PDF内容分割成多个不超过chunk_size页的部分
        claude 规定是 100，但是有可能导致 prompt 超过 200k，所以我们小一点        
        """
        import io
        from PyPDF2 import PdfReader, PdfWriter
        
        reader = PdfReader(io.BytesIO(pdf_content))
        total_pages = len(reader.pages)
        print(f"Total pages: {total_pages}")
        chunks = []
        
        for start in range(0, total_pages, chunk_size):
            end = min(start + chunk_size, total_pages)
            writer = PdfWriter()
            
            for page_num in range(start, end):
                writer.add_page(reader.pages[page_num])
            
            output = io.BytesIO()
            writer.write(output)
            chunks.append(output.getvalue())
            
        return chunks

    def _merge_results(self, results: List[Dict]) -> Dict:
        """合并多个处理结果"""
        if not results:
            return {}
            
        merged = results[0].copy()
        
        # 合并表格数据
        if merged.get('table') and merged['table'].get('data'):
            all_data = []
            for result in results:
                if result.get('table') and result['table'].get('data'):
                    all_data.extend(result['table']['data'])
            
            # 更新合并后的表格数据
            merged['table']['data'] = all_data
            
            # 更新表格元数据
            if merged['table'].get('metadata'):
                merged['table']['metadata'].update({
                    'start_page': min(r['table']['metadata'].get('start_page', float('inf')) 
                                    for r in results if r.get('table') and r['table'].get('metadata')),
                    'end_page': max(r['table']['metadata'].get('end_page', 0) 
                                  for r in results if r.get('table') and r['table'].get('metadata')),
                    'confidence': max(r['table']['metadata'].get('confidence', 0) 
                                   for r in results if r.get('table') and r['table'].get('metadata'))
                })
        
        return merged

    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """处理PDF文件并返回结构化数据"""
        start_time = time.time()
        
        try:
            # 检查文件是否存在
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            # 计算文件哈希
            file_hash = self._calculate_file_hash(pdf_path)
            logger.info(f"Processing PDF: {pdf_path} (hash: {file_hash})")
            
            # 检查缓存
            cached_result = self._read_from_cache(file_hash)
            if cached_result:
                return cached_result

            # 读取PDF文件内容
            with open(pdf_path, "rb") as f:
                pdf_content = f.read()

            # 分割PDF内容
            pdf_chunks = self._split_pdf_content(pdf_content)
            logger.info(f"Split PDF into {len(pdf_chunks)} chunks")

            results = []
            for i, chunk in enumerate(pdf_chunks):
                logger.info(f"Processing chunk {i+1}/{len(pdf_chunks)}")
                
                # 构造提示词
                prompt = """Please analyze this PDF document and provide the following information in a structured format:

1. Find the distribution date (usually at the bottom of the first page) in YYYY-MM format. If not found, return None.

2. Locate the table most semantically similar to "Summary of project findings and ratings". This table should contain "Summary Assessment" and "Rating" columns. The first column is typically labeled "Criterion". Create a pivoted structure with four columns (L1, L2, SummaryAssessment, Rating) where bold items in the first column are L1 indicators and non-bold items are L2 indicators.

3. Provide metadata about the found table including:
   - Start page
   - End page
   - Table name
   - Confidence score (0-1) that this is the target table
   If no matching table is found, return None.

Please format your response as a JSON object with this structure:
{
    "file": {
        "name": "filename",
        "total_pages": number,
        "distribution_date": "YYYY-MM"
    },
    "table": {
        "metadata": {
            "start_page": number,
            "end_page": number,
            "table_name": "string",
            "confidence": float
        },
        "data": [
            {
                "L1": "string",
                "L2": "string",
                "SummaryAssessment": "string",
                "Rating": "string"
            }
        ]
    }
}"""

                # 调用Claude API
                chunk_data = base64.standard_b64encode(chunk).decode("utf-8")
                message = self.client.beta.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    betas=["pdfs-2024-09-25"],
                    max_tokens=1024,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "document",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "application/pdf",
                                        "data": chunk_data
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                )

                text = message.content
                print(f"Chunk {i+1} response:", text)

                try:
                    import json
                    chunk_result = json.loads(text)
                    results.append(chunk_result)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Claude response as JSON for chunk {i+1}: {e}")
                    continue

            # 合并所有结果
            result = self._merge_results(results)

            # 添加元数据
            result["metadata"] = {
                "exec_time": time.time() - start_time,
                "success": True,
                "note": "Successfully processed PDF"
            }

            # 保存到缓存
            self._save_to_cache(file_hash, result)
            
            logger.info(f"Successfully processed PDF in {result['metadata']['exec_time']:.2f} seconds")
            return result

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return {
                "file": None,
                "table": None,
                "metadata": {
                    "exec_time": time.time() - start_time,
                    "success": False,
                    "note": str(e)
                }
            }



if __name__ == "__main__":
    ClaudePDFProcessor().process_pdf('/Users/mark/Documents/Terminal evaluation report/1.10321_2024_ValTR_unep_gef_msp.pdf')
