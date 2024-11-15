from src.config import root_path
from src.v3_final.step_2_add_candidate_tables import init_candidate_tables

import concurrent.futures
import os
import pathlib
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table as RichTable

# 在文件开头定义全局 Console 实例
console = Console()

def truncate_filename(filename: str, max_length: int, full_path: str = None) -> str:
    """
    截断文件名，保留扩展名，并可选添加VSCode可点击链接
    """
    if len(filename) <= max_length:
        display_name = filename
    else:
        name, ext = os.path.splitext(filename)
        display_name = name[:max_length-len(ext)-3] + "..." + ext
    
    if full_path:
        # VSCode 终端链接格式
        return f"\x1b]8;;file://{full_path}\x1b\\{display_name}\x1b]8;;\x1b\\"
    return display_name


def process_single_pdf(index: int, pdf_path: pathlib.Path, progress: Progress, task_id, max_filename_length: int) -> Dict:
    """
    处理单个PDF文件
    """
    result = {
        'index': index,
        'name': pdf_path.name,
        'start': None,
        'end': None,
        'success': False,
        'note': ''
    }
    
    def update_page_progress(current_page, total_pages):
        # 更新进度条百分比
        progress.update(
            task_id,
            completed=int(current_page * 100 / total_pages),
            status=f"[blue]{truncate_filename(pdf_path.name, max_filename_length, str(pdf_path.absolute()))} ({current_page}/{total_pages}页)[/]"
        )
    
    try:
        table_data, start_page, end_page = init_candidate_tables(
            pdf_path.name,
            progress_callback=update_page_progress
        )
        result.update({
            'start': start_page,
            'end': end_page,
            'success': True
        })
    except ValueError as e:
        result['note'] = str(e)
    except Exception as e:
        result['note'] = f"处理出错: {str(e)}"
    
    return result

def process_all_pdfs(root_dir: str) -> pd.DataFrame:
    """
    并发处理目录下的所有PDF文件，提取评分表格信息
    """
    root_path = pathlib.Path(root_dir)
    
    pdf_files = sorted([f for f in root_path.glob("*.pdf")])
    total_files = len(pdf_files)
    results = [None] * total_files

    console.print(Panel(f"[bold blue]开始处理PDF文件[/]\n"
                       f"目录: {root_dir}\n"
                       f"文件数量: {total_files}"))

    # 计算合适的显示宽度
    term_width = os.get_terminal_size().columns
    max_filename_length = min(50, term_width // 4)  # 文件名占1/4
    progress_bar_width = term_width // 2  # 增加进度条宽度到1/2

    # 定义状态更新函数
    def update_status(task_id: int, status_type: str, filename: str, full_path: str = None):
        """统一处理状态更新"""
        status_colors = {
            'wait': 'white',
            'process': 'blue',
            'success': 'green',
            'fail': 'yellow',
            'error': 'red'
        }
        truncated_name = truncate_filename(filename, max_filename_length, full_path)
        status_text = f"[{status_colors[status_type]}]{truncated_name}[/]"
        progress.update(task_id, status=status_text)

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description: <12}"),  # 进一步缩短描述列
        BarColumn(
            bar_width=progress_bar_width,  # 使用更大的进度条宽度
            complete_style="green",
            finished_style="green"
        ),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%", style="green"),
        TimeRemainingColumn(),
        TextColumn("{task.fields[status]}", justify="left"),
        console=console,
        expand=True,  # 改回 True 以充分利用空间
        refresh_per_second=10
    )

    with progress:
        # 总体进度任务
        overall_task = progress.add_task(
            "[cyan]总进度", 
            total=total_files,
            status="准备中..."
        )
        
        # 为每个工作线程创建任务
        worker_tasks = {}
        max_workers = min(total_files, os.cpu_count())
        for i in range(max_workers):
            task = progress.add_task(
                f"[blue]线程{i+1:<2}",  # 缩短线程描述
                total=100,
                visible=True,
                status="等待任务..."
            )
            worker_tasks[i] = task

        completed = 0
        errors = []
        success_count = 0
        current_tasks = {}  # 记录当前每个线程正在处理的任务
        future_to_idx = {}  # 添加这个字典来跟踪future和任务索引的对应关系
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 初始提交第一批任务
            futures = set()
            for i in range(min(max_workers, total_files)):
                future = executor.submit(
                    process_single_pdf, 
                    i, 
                    pdf_files[i], 
                    progress, 
                    worker_tasks[i],
                    max_filename_length  # 添加这个参数
                )
                futures.add(future)
                current_tasks[i] = i
                future_to_idx[future] = (i, pdf_files[i])
            
            next_task_idx = max_workers
            
            # 处理完成的任务并提交新任务
            while futures:
                done, futures = concurrent.futures.wait(
                    futures, 
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                for future in done:
                    # 找到这个任务是哪个线程的
                    worker_id = None
                    for wid, task_idx in current_tasks.items():
                        if task_idx == future_to_idx[future][0]:
                            worker_id = wid
                            break
                    
                    if worker_id is None:
                        continue
                            
                    idx, pdf_path = future_to_idx[future]
                    try:
                        result = future.result()
                        results[idx] = result
                        if result['success']:
                            success_count += 1
                            # 先更新进度条到100%
                            progress.update(worker_tasks[worker_id], completed=100)
                            # 再更新状态文本
                            update_status(worker_tasks[worker_id], 'success', pdf_path.name, str(pdf_path.absolute()))
                        else:
                            # 同样的模式
                            progress.update(worker_tasks[worker_id], completed=100)
                            update_status(worker_tasks[worker_id], 'fail', pdf_path.name, str(pdf_path.absolute()))
                            errors.append(f"[yellow]• {truncate_filename(pdf_path.name, max_filename_length, str(pdf_path.absolute()))} - {result['note']}[/]")
                    except Exception as e:
                        error_msg = f"执行失败: {str(e)}"
                        results[idx] = {
                            'index': idx,
                            'name': pdf_path.name,
                            'start': None,
                            'end': None,
                            'success': False,
                            'note': error_msg
                        }
                        update_status(worker_tasks[worker_id], 'error', pdf_path.name)
                        errors.append(f"[red]• {truncate_filename(pdf_path.name, max_filename_length, str(pdf_path.absolute()))} - {error_msg}[/]")
                    
                    completed += 1
                    # 更新总进度
                    progress.update(
                        overall_task, 
                        completed=completed,
                        description=f"[cyan]处理PDF文件... (成功: {success_count}/{completed})"
                    )

                    # 在开始新任务时
                    if next_task_idx < total_files:
                        next_file_path = pdf_files[next_task_idx]  # 获取下一个文件路径
                        # 重置进度条
                        progress.update(worker_tasks[worker_id], completed=0)
                        # 更新状态文本
                        update_status(
                            worker_tasks[worker_id], 
                            'wait', 
                            next_file_path.name, 
                            str(next_file_path.absolute())
                        )
                        # 提交新任务
                        new_future = executor.submit(
                            process_single_pdf, 
                            next_task_idx, 
                            next_file_path, 
                            progress, 
                            worker_tasks[worker_id],
                            max_filename_length
                        )
                        futures.add(new_future)
                        current_tasks[worker_id] = next_task_idx
                        future_to_idx[new_future] = (next_task_idx, next_file_path)
                        next_task_idx += 1

        if errors:
            console.print("\n[bold yellow]处理过程中的警告和错误:[/]")
            for error in errors[:10]:
                console.print(error)
            if len(errors) > 10:
                console.print(f"[yellow]...还有 {len(errors) - 10} 个错误未显示[/]")

    df = pd.DataFrame([r for r in results if r is not None])
    df = df.sort_values('index').reset_index(drop=True)

    output_path = pathlib.Path(root_dir) / 'table_extraction_results.csv'
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    return df

if __name__ == "__main__":
    console = Console()
    
    try:
        results_df = process_all_pdfs(root_path)

        # 创建结果统计表格
        table = RichTable(title="处理结果统计", show_header=True, header_style="bold magenta")
        table.add_column("指标", style="cyan", no_wrap=True)
        table.add_column("数值", justify="right", style="green", no_wrap=True)
        
        success_count = results_df['success'].sum()
        fail_count = len(results_df) - success_count
        total_count = len(results_df)
        
        table.add_row("总文件数", str(total_count))
        table.add_row("成功提取", str(success_count))
        table.add_row("失败数量", str(fail_count))
        table.add_row("成功率", f"{(success_count/total_count*100):.1f}%")

        console.print("\n")
        console.print(table)
        
        # 如果有失败的情况，显示失败详情
        if fail_count > 0:
            console.print("\n[bold red]失败详情:[/]")
            failed_cases = results_df[~results_df['success']]
            for _, row in failed_cases.iterrows():
                console.print(f"[red]• {row['name']}[/] - {row['note']}")

        console.print(f"\n[bold green]结果已保存至:[/] {root_path}/table_extraction_results.csv")
        
    except Exception as e:
        console.print(f"[bold red]处理过程中发生错误:[/] {str(e)}")
