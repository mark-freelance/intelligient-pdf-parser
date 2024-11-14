import concurrent.futures
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

import pandas as pd
from loguru import logger
from rich import box
from rich.console import Console
from rich.live import Live
from rich.table import Table

from src.config import DEFAULT_CONFIG, OUTPUT_DIR
from src.model_loader import ModelLoader
from src.pdf_parser import find_summary_text

# 添加状态表情映射
STATUS_EMOJI = {
    'pending': '⏳',
    'opening': '📂',
    'processing': '🔄',
    'processing_page': '📄',
    'success': '✅',
    'not_found': '❌',
    'parse_error': '⚠️',
    'error': '💔'}

# 确保输出目录存在
OUTPUT_DIR.mkdir(exist_ok=True)


class ProgressTracker:
    def __init__(self, total_files, max_display_rows=20):
        self.total_files = total_files
        self.results = {}
        self.lock = Lock()
        self.console = Console()
        self.max_display_rows = max_display_rows
        self.start_time = datetime.now()
        self.completed_times = []  # 用于存储每个完成任务的时间点

    def update_progress(self, file_name, status, details=None, best_match=None):
        with self.lock:
            # 如果是第一次更新这个文件的状态
            if file_name not in self.results:
                self.results[file_name] = {'status': status, 'details': details, 'best_match': best_match}
            else:
                # 更新状态和详情
                self.results[file_name]['status'] = status
                self.results[file_name]['details'] = details
                # 只有当提供了新的最优匹配时才更新
                if best_match is not None:
                    self.results[file_name]['best_match'] = best_match

            logger.debug(f"{file_name}: {status} - {details} - Best match: {best_match}")

    def create_progress_table(self):
        table = Table(box=box.ROUNDED, expand=True, show_edge=True)

        # 计算进度信息
        completed = len([i for i in self.results.values() if
                         i['status'] not in ['pending', 'processing', 'processing_page']])
        progress = completed / self.total_files if self.total_files > 0 else 0

        # 计算时间信息
        elapsed_time = datetime.now() - self.start_time
        if completed > 0:
            avg_time_per_file = elapsed_time / completed
            remaining_files = self.total_files - completed
            estimated_remaining = avg_time_per_file * remaining_files
        else:
            estimated_remaining = timedelta(0)

        # 创建自定义进度条字符串
        progress_percentage = int(progress * 100)
        bar_width = 30  # 进度条的总宽度
        filled_width = int(bar_width * progress)
        empty_width = bar_width - filled_width
        progress_bar = f"[{'=' * filled_width}{' ' * empty_width}] {progress_percentage}%"

        # 格式化时间显示
        def format_timedelta(td):
            hours = td.seconds // 3600
            minutes = (td.seconds % 3600) // 60
            seconds = td.seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # 添加进度信息到标题
        progress_text = (f"总进度: {completed}/{self.total_files} ({progress:.1%}) "
                         f"已用时间: {format_timedelta(elapsed_time)} "
                         f"预计剩余: {format_timedelta(estimated_remaining)}")

        # 添加列
        table.add_column("序号", style="cyan", width=3, no_wrap=True)  # 调整为3位数宽度
        table.add_column("状态", width=2, no_wrap=True)
        table.add_column("文件名", style="bright_blue", width=40, no_wrap=True)
        table.add_column("详情", style="green", width=40, no_wrap=True)
        table.add_column("最优匹配", style="yellow", width=80, no_wrap=True)

        # 获取所有非 pending 状态的项目
        active_items = [(f, info) for f, info in self.results.items() if info['status'] != 'pending']

        # 获取 pending 状态的项目
        pending_items = [(f, info) for f, info in self.results.items() if info['status'] == 'pending']

        # 按照文件名排序
        sorted_active = sorted(active_items, key=lambda x: extract_number(x[0]))
        sorted_pending = sorted(pending_items, key=lambda x: extract_number(x[0]))

        # 计算要显示的活动项目数量
        remaining_rows = self.max_display_rows - 1  # 为最后一行保留空间
        active_to_show = sorted_active[-remaining_rows:] if len(sorted_active) > remaining_rows else sorted_active

        # 添加活动项目
        for filename, info in active_to_show:
            self._add_table_row(table, filename, info)

        # 在最后一行显示进度条
        if len(pending_items) > 0:
            table.add_row("...", "⏳", progress_bar,  # 使用自定义进度条
                f"还有 {len(pending_items)} 个文件等待处理", "", style="dim italic")

        table.title = progress_text
        return table

    def _add_table_row(self, table, filename, info):
        """辅助方法：向表格添加一行"""
        status = info['status']
        emoji = STATUS_EMOJI.get(status, '❓')
        details = info['details'] or ''
        best_match = info.get('best_match', '')

        # 提取文件名中的数字并格式化为3位数
        file_number = extract_number(filename)
        formatted_number = f"{file_number:03d}"  # 格式化为3位数

        # 如果文件名过长，截断并添加省略号
        if len(filename) > 27:
            truncated_filename = filename[:27] + "..."
        else:
            truncated_filename = filename

        # 根据状态设置行样式
        row_style = None
        if status == 'error':
            row_style = "red"
        elif status == 'success':
            row_style = "bright_green"
        elif status == 'not_found':
            row_style = "yellow"

        table.add_row(formatted_number,  # 使用格式化后的3位数序号
            emoji, truncated_filename, str(details), str(best_match), style=row_style)


def extract_number(filename):
    """从文件名中提取序号"""
    match = re.match(r'^(\d+)', filename)
    return int(match.group(1)) if match else float('inf')


def process_single_pdf(pdf_path, progress_tracker: ProgressTracker):
    """处理单个PDF文件并返回结果"""
    try:
        logger.debug(f"开始处理文件: {pdf_path.name}")
        progress_tracker.update_progress(pdf_path.name, 'opening', "正在打开文件...")

        def page_callback(page_num, total_pages, best_match=None):
            """页面处理进度回调"""
            details = f"正在处理第 {page_num + 1:>3d}/{total_pages:>3d} 页..."

            best_match_info = ""
            if best_match:
                context_before = best_match.get('context_before', '')
                context_after = best_match.get('context_after', '')
                matched_text = best_match['matched_text']

                if len(context_before) > 30:
                    context_before = "..." + context_before[-30:]
                if len(context_after) > 30:
                    context_after = context_after[:30] + "..."

                display_text = (f"页码:{best_match['page_num'] + 1:>3d} | "
                                f"相似度:{best_match['confidence']:.2f} | "
                                f"匹配: {context_before}[{matched_text}]{context_after}")
                best_match_info = display_text

            logger.debug(f"{pdf_path.name}: {details}")
            progress_tracker.update_progress(pdf_path.name, 'processing_page', details, best_match_info)

        logger.debug(f"{pdf_path.name}: 准备调用 find_summary_text...")
        progress_tracker.update_progress(pdf_path.name, 'processing', "开始处理文件内容...")

        # 设置超时时间
        try:
            result = find_summary_text(str(pdf_path), page_callback=page_callback)
            logger.debug(f"{pdf_path.name}: find_summary_text 调用完成")
        except Exception as e:
            logger.debug(f"{pdf_path.name}: find_summary_text 执行出错: {str(e)}")
            raise

        if result:
            details = f"找到目标! 页码:{result['page_num'] + 1}, 相似度:{result['confidence']:.2f}"
            logger.debug(f"{pdf_path.name}: {details}")
            progress_tracker.update_progress(pdf_path.name, 'success', details)
            return {
                'file_name': pdf_path.name,
                'status': 'success',
                'page_number': result['page_num'] + 1,
                'matched_text': result['matched_text'],
                'confidence': result['confidence'],
                'text_bbox': str(result['text_bbox']),
                'table_bbox': str(result['table_bbox']) if result['table_bbox'] else None}
        else:
            progress_tracker.update_progress(pdf_path.name, 'not_found', "搜索完成，未找到目标文字")
            return {
                'file_name': pdf_path.name,
                'status': 'not_found',
                'page_number': None,
                'matched_text': None,
                'confidence': None,
                'text_bbox': None,
                'table_bbox': None,
                'error_msg': '未找到目标文字'}
    except Exception as e:
        error_msg = str(e)
        if "not a textpage" in error_msg.lower():
            progress_tracker.update_progress(pdf_path.name, 'parse_error', "页面无法解析为文本")
            return {
                'file_name': pdf_path.name,
                'status': 'parse_error',
                'page_number': None,
                'matched_text': None,
                'confidence': None,
                'text_bbox': None,
                'table_bbox': None,
                'error_msg': '页面无法解析为文本'}
        else:
            progress_tracker.update_progress(pdf_path.name, 'error', f"错误: {error_msg[:50]}...")
            return {
                'file_name': pdf_path.name,
                'status': 'error',
                'page_number': None,
                'matched_text': None,
                'confidence': None,
                'text_bbox': None,
                'table_bbox': None,
                'error_msg': error_msg}


def process_pdf_files(folder_path, max_workers=None):
    """并发处理文件夹中的所有PDF文件并返回结果列表"""
    pdf_files = list(Path(folder_path).glob('**/*.pdf'))
    pdf_files.sort(key=lambda x: extract_number(x.name))
    pdf_files = pdf_files[:]
    total_files = len(pdf_files)

    logger.info(f"找到 {total_files} 个PDF文件待处理")

    logger.info(f"设置最大并发数为: {max_workers}")

    progress_tracker = ProgressTracker(total_files, max_display_rows=20)
    console = Console()

    # 初始化所有文件状态为pending
    for pdf_file in pdf_files:
        progress_tracker.update_progress(pdf_file.name, 'pending', "等待处理")

    results = []

    # 创建一个共享的Live对象，供回调函数使用
    live = None

    def update_display():
        """更新显示的辅助函数"""
        if live:
            live.update(progress_tracker.create_progress_table())

    # 包装progress_tracker，使其在更新状态时自动刷新显示
    class DisplayUpdatingTracker:
        def __init__(self, tracker):
            self.tracker = tracker

        def update_progress(self, *args, **kwargs):
            self.tracker.update_progress(*args, **kwargs)
            update_display()

    display_tracker = DisplayUpdatingTracker(progress_tracker)

    try:
        with Live(progress_tracker.create_progress_table(),
                console=console,
                refresh_per_second=4,
                transient=False,
                vertical_overflow="visible") as live_display:
            live = live_display  # 保存live对象的引用

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for pdf_path in pdf_files:
                    logger.debug(f"提交任务: {pdf_path.name}")
                    # 使用包装后的tracker
                    future = executor.submit(process_single_pdf, pdf_path, display_tracker)
                    futures.append((future, pdf_path))

                for future, pdf_path in futures:
                    try:
                        result = future.result(timeout=300)
                        results.append(result)
                    except concurrent.futures.TimeoutError:
                        logger.debug(f"处理文件超时: {pdf_path.name}")
                        display_tracker.update_progress(pdf_path.name, 'error', "处理超时")
                    except Exception as e:
                        logger.debug(f"处理文件出错: {pdf_path.name}, 错误: {str(e)}")
                        display_tracker.update_progress(pdf_path.name, 'error', f"错误: {str(e)[:50]}...")

    except KeyboardInterrupt:
        logger.warning("用户中断处理")
        return results

    return results


def save_statistics(results, output_path):
    """将结果保存为Excel统计表，并增加相似度分析"""
    df = pd.DataFrame(results)

    # 添加相似度分布分析
    successful_results = df[df['status'] == 'success']
    if not successful_results.empty:
        confidence_stats = successful_results['confidence'].describe()
        logger.info(f"""相似度统计:
        最小值: {confidence_stats['min']:.3f}
        最大值: {confidence_stats['max']:.3f}
        平均值: {confidence_stats['mean']:.3f}
        中位数: {confidence_stats['50%']:.3f}""")

    # 重新排列列的顺序，使其更有逻辑性
    columns_order = ['file_name', 'status', 'page_number', 'matched_text', 'confidence', 'text_bbox', 'table_bbox',
        'error_msg']

    # 确保所有列都存在，如果不存在则填充 None
    for col in columns_order:
        if col not in df.columns:
            df[col] = None

    # 按指定顺序重排列列
    df = df[columns_order]

    df.to_excel(output_path, index=False)
    logger.info(f"统计结果已保存至: {output_path}")

    # 输出详细统计信息
    total = len(results)
    success = len([r for r in results if r['status'] == 'success'])
    not_found = len([r for r in results if r['status'] == 'not_found'])
    parse_error = len([r for r in results if r['status'] == 'parse_error'])
    error = len([r for r in results if r['status'] == 'error'])

    logger.info(f"""处理统计:
    总文件数: {total}
    成功处理: {success}
    未找到目标文字: {not_found}
    页面解析错误: {parse_error}
    其他错误: {error}""")


def main():
    # 加载配置
    config = DEFAULT_CONFIG

    # 移除默认的 stderr 处理器
    logger.remove()

    # 添加控制台处理器
    logger.add(sys.stderr, level=config.log.console_level, format=config.log.console_format, colorize=True)

    # 添加文件处理器
    logger.add(str(config.log.log_file),
        level=config.log.file_level,
        format=config.log.log_format,
        rotation=config.log.rotation)

    # 打印配置信息
    logger.info("当前配置:")
    logger.info(config)

    try:
        # 预热模型
        logger.info("预热模型...")
        ModelLoader.get_model()

        # 处理有PDF文件
        results = process_pdf_files(config.pdf.pdf_folder, max_workers=config.pdf.max_workers)

        # 保存统计结果
        if results:
            save_statistics(results, config.pdf.output_file)

    except Exception as e:
        logger.exception("处理过程中发生错误")
        raise


if __name__ == '__main__':
    main()
