import atexit
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

from v1_plain.src.config import DEFAULT_CONFIG, STATUS_EMOJI
from v1_plain.src import ModelLoader
from v1_plain.src.pdf_parser.search_text import find_summary_text


class ProgressTracker:
    def __init__(self, total_files, max_display_rows=20, keywords: str = None):
        self.keywords = keywords
        self.total_files = total_files
        self.results = {}
        self.lock = Lock()
        self.console = Console()
        self.max_display_rows = max_display_rows
        self.start_time = datetime.now()
        self.completed_times = []  # 用于存储个完成任务的时间点
        self.last_save_count = 0  # 新增：记录上次保存的数量
        self.file_page_progress = {}  # 新增：记录每个文件的页面处理进度
        self.best_matches = {}  # 新增：记录每个文件的最佳匹配结果

    def update_progress(self, file_name, status, details=None, best_match=None, current_page=None, total_pages=None):
        with self.lock:
            if file_name not in self.results:
                self.results[file_name] = {
                    'status': status,
                    'details': details,
                    'best_match': best_match,
                    'last_page': current_page,  # 新增：记录最后处理的页面
                    'total_pages': total_pages  # 新增：总页数
                }
            else:
                self.results[file_name].update({
                    'status': status,
                    'details': details,
                    'last_page': current_page,
                    'total_pages': total_pages})

                # 更新最佳匹配（如果新的匹配更好）
                if best_match is not None:
                    current_best = self.results[file_name].get('best_match')
                    if (not current_best or (best_match.get('confidence', 0) > current_best.get('confidence', 0))):
                        self.results[file_name]['best_match'] = best_match

            logger.debug(f"{file_name}: {status} - {details} - Best match: {best_match}")

    def create_progress_table(self):
        table = Table(box=box.ROUNDED, expand=True, show_edge=True)

        # 计算进度信息
        completed = len([i for i in self.results.values() if
                         i['status'] not in ['pending', 'processing', 'processing_page']])
        progress = completed / self.total_files if self.total_files > 0 else 0

        # 创建自定义进度条字符串
        progress_percentage = int(progress * 100)
        bar_width = 30  # 进度条的总宽度
        filled_width = int(bar_width * progress)
        empty_width = bar_width - filled_width
        progress_bar = f"[{'=' * filled_width}{' ' * empty_width}] {progress_percentage}%"

        # 计算时间信息
        elapsed_time = datetime.now() - self.start_time
        if completed > 0:
            avg_time_per_file = elapsed_time / completed
            remaining_files = self.total_files - completed
            estimated_remaining = avg_time_per_file * remaining_files
        else:
            estimated_remaining = timedelta(0)

        # 格式时间显示
        def format_timedelta(td):
            hours = td.seconds // 3600
            minutes = (td.seconds % 3600) // 60
            seconds = td.seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # 添加进度信息到标题，包含保存信息
        save_info = f"已保存: {self.last_save_count}" if self.last_save_count > 0 else ""
        progress_text = ("，".join(filter(None,
                                         [f"总进度: {completed}/{self.total_files} ({progress:.1%})",
                                             f"已用时间: {format_timedelta(elapsed_time)}",
                                             f"预计剩余: {format_timedelta(estimated_remaining)}",
                                             f"目标匹配: {self.keywords}", save_info])))

        # 添加列
        table.add_column("序号", style="cyan", width=3)
        table.add_column("状态", width=2)
        table.add_column("文件名", style="bright_blue", width=30)
        table.add_column("详情", style="green", width=30)
        table.add_column("最优匹配", style="yellow", width=60, overflow="fold")

        # 获取所有非 pending 状态的项目
        active_items = [(f, info) for f, info in self.results.items() if info['status'] != 'pending']

        # 取 pending 状态的项目
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
            table.add_row("...", "⏳", progress_bar,  # 现在 progress_bar 已定义
                          f"还有 {len(pending_items)} 个文件等待处理", "", style="dim italic")

        table.title = progress_text
        return table

    def _add_table_row(self, table, filename, info):
        """辅助方法：向表格添加一行"""
        status = info['status']
        emoji = STATUS_EMOJI.get(status, '❓')
        details = str(info['details'] or '')  # 确保 details 是字符串

        # 如果是错误状态，直接显示错误信息
        if status in ['error', 'parse_error']:
            best_match = info.get('error_msg', '')
        else:
            # 对于其他状态，显示最佳匹配信息
            best_match = info.get('best_match', {})  # 确保是字典，默认为空字典
            if isinstance(best_match, dict):
                # 如果是字典，格式化显示（限制长度）
                matched_text = best_match.get('matched_text', '')
                # 处理换行符
                matched_text = matched_text.replace('\n', '\\n')
                if len(matched_text) > 30:  # 限制匹配文本长度
                    matched_text = matched_text[:30] + "..."

                best_match = (f"页码:{best_match.get('page_num', 0) + 1:>3d} "
                              f"相似度:{best_match.get('confidence', 0):.2f} "
                              f"匹配:{matched_text}")
            else:
                best_match = str(best_match)  # 确保转换为字符串
                best_match = best_match.replace('\n', '\\n')  # 处理可能存在的换行符

        # 提取文件名中的数字并格式化为3位数
        file_number = extract_number(filename)
        formatted_number = f"{file_number:03d}"

        # 如果文件名过长，截断并添加��
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

        table.add_row(formatted_number,
            emoji,
            truncated_filename,
            details,
            best_match,
            style=row_style,
            end_section=False
            # 禁止行分隔
        )

    def update_save_count(self, count):
        """更新已保存的数量"""
        self.last_save_count = count


def extract_number(filename):
    """从文件名中提取序号"""
    match = re.match(r'^(\d+)', filename)
    return int(match.group(1)) if match else float('inf')


def load_page_progress(progress_file):
    """加载文件处理进度和最优匹配信息"""
    if progress_file.exists():
        try:
            df = pd.read_csv(progress_file)
            progress = {}
            best_matches = {}

            for _, row in df.iterrows():
                fname = row['file_name']
                progress[fname] = row['last_page']

                # 重建最优匹配信息
                if pd.notna(row['best_match_confidence']):
                    best_matches[fname] = {
                        'page_num': int(row['best_match_page']) if pd.notna(row['best_match_page']) else None,
                        'confidence': float(row['best_match_confidence']),
                        'matched_text': row['best_match_text'],
                        'text_bbox': eval(row['best_match_bbox']) if pd.notna(row['best_match_bbox']) else None,
                        'table_bbox': eval(row['best_match_table_bbox']) if pd.notna(
                            row['best_match_table_bbox']) else None}

            logger.info(f"已加载 {len(progress)} 个文件的处理进度")
            return progress, best_matches
        except Exception as e:
            logger.warning(f"读取页面进度失败: {e}")
    return {}, {}


def save_page_progress(page_progress, progress_file, progress_tracker):
    """保存文件处理进度，包括页码和最优匹配"""
    try:
        records = []
        for fname, page in page_progress.items():
            # 获取文件的当前信息，包括最优匹配
            current_info = progress_tracker.results.get(fname, {})
            best_match = current_info.get('best_match', {})

            record = {
                'file_name': fname,
                'last_page': page,
                'best_match_page': best_match.get('page_num') if best_match else None,
                'best_match_confidence': best_match.get('confidence') if best_match else None,
                'best_match_text': best_match.get('matched_text') if best_match else None,
                'best_match_bbox': str(best_match.get('text_bbox')) if best_match else None,
                'best_match_table_bbox': str(best_match.get('table_bbox')) if best_match else None}
            records.append(record)

        df = pd.DataFrame(records)
        df.to_csv(progress_file, index=False)
        logger.debug(f"已保存页面进度到 {progress_file}")
    except Exception as e:
        logger.error(f"保存页面进度失败: {e}")


def process_single_pdf(pdf_path, progress_tracker: ProgressTracker, start_page=0):
    """修改处理单个PDF的函数，支持从指定页面开始"""
    try:
        logger.debug(f"开始处理文件: {pdf_path.name}, 从第 {start_page + 1} 页开始")
        progress_tracker.update_progress(pdf_path.name, 'opening', f"正在打开文件，从第 {start_page + 1} 页开始...")

        def page_callback(page_num, total_pages, best_match=None):
            """页面处理进度回调"""
            details = f"正在处理第 {page_num + 1:>3d}/{total_pages:>3d} 页..."
            progress_tracker.update_progress(pdf_path.name,
                'processing_page',
                details,
                best_match,
                # 直接传递 best_match 字典
                current_page=page_num,
                total_pages=total_pages)

        # 修改 find_summary_text 调用，添加 start_page 参数
        result = find_summary_text(str(pdf_path), page_callback=page_callback, start_page=start_page)

        if result:
            details = f"找到目标! 页码:{result['page_num'] + 1}, 相似度:{result['confidence']:.2f}"
            # 直接传递 result 作为 best_match
            progress_tracker.update_progress(pdf_path.name, 'success', details, result  # 直接传递结果字典
            )
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


def load_previous_results(output_file):
    """加载之前处理结果"""
    if output_file.exists():
        try:
            df = pd.read_csv(output_file)
            # 转换为字典列表格式
            results = df.to_dict('records')
            logger.info(f"加载到 {len(results)} 条已处理记录")
            return results
        except Exception as e:
            logger.warning(f"读取历史记录失败: {e}")
    return []


def save_results_to_csv(results, output_file):
    """保存结果到CSV文件"""
    if results:
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False)
        logger.debug(f"已保存 {len(results)} 条处理记录到 {output_file}")


def process_pdf_files(folder_path, keywords: str, max_workers=None):
    """修改主处理函数，支持页面级别的续传"""
    config = DEFAULT_CONFIG
    progress_file = config.pdf.progress_file
    page_progress_file = config.pdf.page_progress_file

    # 加载已处理的结果和页面进度
    previous_results = load_previous_results(progress_file)
    page_progress, best_matches = load_page_progress(page_progress_file)
    processed_files = {r['file_name'] for r in previous_results if r['status'] == 'success'}

    # 获取所有PDF文件并过滤掉完全处理完的
    pdf_files = list(Path(folder_path).glob('**/*.pdf'))
    pdf_files.sort(key=lambda x: extract_number(x.name))
    pdf_files = [f for f in pdf_files if f.name not in processed_files]

    total_files = len(pdf_files)
    logger.info(f"找到 {total_files} 个未处理的PDF文件")

    if not pdf_files:
        logger.info("所有文件已处理完成")
        return previous_results

    progress_tracker = ProgressTracker(total_files, max_display_rows=20, keywords=keywords)
    console = Console()

    # 初始化结果列表，包含之前的结果
    results = previous_results.copy()

    # 初始化所有文件状态为pending，并恢复最优匹配信息
    for pdf_file in pdf_files:
        initial_status = 'pending'
        initial_details = "等待处理"
        best_match = best_matches.get(pdf_file.name)

        progress_tracker.update_progress(pdf_file.name, initial_status, initial_details, best_match=best_match)

    # 注册程序退出时的保存函数
    def save_on_exit():
        save_results_to_csv(results, progress_file)
        save_page_progress(page_progress, page_progress_file, progress_tracker)

    atexit.register(save_on_exit)

    # 创建一个共享的Live对象，供回调使用
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
        with Live(progress_tracker.create_progress_table(), console=console, refresh_per_second=4) as live_display:
            live = live_display

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []

                # 提交任务时考虑页面进度
                for pdf_path in pdf_files:
                    start_page = page_progress.get(pdf_path.name, 0)
                    logger.debug(f"提交任务: {pdf_path.name}, 从第 {start_page + 1} 页开始")
                    future = executor.submit(process_single_pdf, pdf_path, display_tracker, start_page=start_page)
                    futures.append((future, pdf_path))

                # 处理完成的任务
                for future in concurrent.futures.as_completed([f for f, _ in futures]):
                    try:
                        # 找到对应的 pdf_path
                        pdf_path = next(p for f, p in futures if f == future)
                        result = future.result(timeout=300)

                        # 更新页面进度和最优匹配
                        current_info = progress_tracker.results.get(pdf_path.name, {})
                        current_page = current_info.get('last_page')
                        best_match = current_info.get('best_match')

                        if current_page is not None:
                            page_progress[pdf_path.name] = current_page

                        # 只有在成功找到目标时才添加到结果中
                        if result['status'] == 'success':
                            results.append(result)
                            # 从页面进度中移除已完成的文件
                            page_progress.pop(pdf_path.name, None)

                        # 定期保存进度
                        if len(results) % 2 == 0:
                            save_results_to_csv(results, progress_file)
                            save_page_progress(page_progress, page_progress_file, progress_tracker)
                            progress_tracker.update_save_count(len(results))

                    except concurrent.futures.TimeoutError:
                        logger.error(f"处理文件超时: {pdf_path.name}")
                        save_current_progress(pdf_path, progress_tracker, page_progress, page_progress_file)

                    except Exception as e:
                        logger.error(f"处理文件出错: {pdf_path.name}, 错误: {str(e)}")
                        save_current_progress(pdf_path, progress_tracker, page_progress, page_progress_file)

    except KeyboardInterrupt:
        logger.warning("用户中断处理")
        # 保存所有正在处理的文件的进度
        for pdf_path in pdf_files:
            save_current_progress(pdf_path, progress_tracker, page_progress, page_progress_file)
        save_results_to_csv(results, progress_file)
        return results
    except Exception as e:
        logger.error(f"发生未预期的错误: {str(e)}")
        # 保存所有正在处理的文件的进度
        for pdf_path in pdf_files:
            save_current_progress(pdf_path, progress_tracker, page_progress, page_progress_file)
        save_results_to_csv(results, progress_file)
        raise
    finally:
        # 确保最终保存一次进度
        save_results_to_csv(results, progress_file)
        save_page_progress(page_progress, page_progress_file, progress_tracker)

    return results


def save_current_progress(pdf_path, progress_tracker, page_progress, page_progress_file):
    """保存当前处理进度的辅助函数"""
    try:
        current_info = progress_tracker.results.get(pdf_path.name, {})
        current_page = current_info.get('last_page')
        if current_page is not None:
            page_progress[pdf_path.name] = current_page
            save_page_progress(page_progress, page_progress_file, progress_tracker)
    except Exception as e:
        logger.error(f"保存进度时发生错误: {str(e)}")


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

    # 确保所有列存在，如果不存在则填充 None
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
        results = process_pdf_files(config.pdf.pdf_folder,
                                    keywords=config.target.table_name,
                                    max_workers=config.pdf.max_workers)

        # 保存统计结果
        if results:
            save_statistics(results, config.pdf.output_file)

    except Exception as e:
        logger.exception("处理过程中发生错误")
        raise


if __name__ == '__main__':
    main()
