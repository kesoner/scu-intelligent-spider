#!/usr/bin/env python3
"""
東吳大學爬蟲專案主程式

提供命令列介面來執行各種爬蟲和資料處理任務
"""

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path

from src.utils import ConfigManager, EnvManager, setup_logger
from src.crawlers import PersonnelCrawler, NewsCrawler
from src.processors import TextProcessor, DataFormatter, VectorProcessor
from src.processors.simple_rag_processor import SimpleRAGProcessor

console = Console()


@click.group()
@click.option('--config', '-c', default=None, help='配置檔案路徑')
@click.option('--verbose', '-v', is_flag=True, help='詳細輸出')
@click.pass_context
def cli(ctx, config, verbose):
    """東吳大學爬蟲系統 - 模組化的網站資料收集與處理工具"""
    
    # 初始化上下文
    ctx.ensure_object(dict)
    
    # 載入環境變數
    env_manager = EnvManager()
    
    # 載入配置
    config_manager = ConfigManager(config)
    if not config_manager.validate_config():
        console.print("[red]配置檔案驗證失敗[/red]")
        ctx.exit(1)
    
    # 設定日誌
    log_config = config_manager.get_logging_config()
    log_level = "DEBUG" if verbose else log_config.get("level", "INFO")
    setup_logger(
        log_file=log_config.get("file"),
        log_level=log_level,
        rotation=log_config.get("rotation", "1 day"),
        retention=log_config.get("retention", "30 days")
    )
    
    # 儲存到上下文
    ctx.obj['config'] = config_manager
    ctx.obj['env'] = env_manager
    
    console.print("[green]東吳大學爬蟲系統已初始化[/green]")


@cli.command()
@click.pass_context
def crawl_personnel(ctx):
    """爬取人事資料"""
    config = ctx.obj['config']
    
    console.print("[blue]開始爬取人事資料...[/blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("爬取人事資料中...", total=None)
        
        try:
            with PersonnelCrawler(config) as crawler:
                result = crawler.crawl()
            
            if result.get("success"):
                progress.update(task, description="✅ 人事資料爬取完成")
                
                # 顯示結果統計
                table = Table(title="人事資料爬取結果")
                table.add_column("項目", style="cyan")
                table.add_column("數量", style="green")
                
                table.add_row("類別數量", str(result.get("total_categories", 0)))
                table.add_row("文件總數", str(result.get("total_documents", 0)))
                table.add_row("唯一連結", str(result.get("unique_pdf_links", 0)))
                
                console.print(table)
            else:
                progress.update(task, description="❌ 人事資料爬取失敗")
                console.print(f"[red]錯誤: {result.get('error', '未知錯誤')}[/red]")
                
        except Exception as e:
            progress.update(task, description="❌ 人事資料爬取失敗")
            console.print(f"[red]錯誤: {e}[/red]")


@cli.command()
@click.option('--pages', '-p', default=None, type=int, help='爬取頁數（預設使用配置檔案設定）')
@click.pass_context
def crawl_news(ctx, pages):
    """爬取新聞資料"""
    config = ctx.obj['config']
    
    # 更新頁數設定
    if pages:
        config._config['websites']['news']['max_pages'] = pages
    
    max_pages = config.get_news_max_pages()
    console.print(f"[blue]開始爬取新聞資料（最多 {max_pages} 頁）...[/blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("爬取新聞資料中...", total=None)
        
        try:
            with NewsCrawler(config) as crawler:
                result = crawler.crawl()
            
            if result.get("success"):
                progress.update(task, description="✅ 新聞資料爬取完成")
                
                # 顯示結果統計
                table = Table(title="新聞資料爬取結果")
                table.add_column("項目", style="cyan")
                table.add_column("數量", style="green")
                
                table.add_row("爬取頁數", str(result.get("total_pages", 0)))
                table.add_row("文章總數", str(result.get("total_articles", 0)))
                
                console.print(table)
            else:
                progress.update(task, description="❌ 新聞資料爬取失敗")
                console.print(f"[red]錯誤: {result.get('error', '未知錯誤')}[/red]")
                
        except Exception as e:
            progress.update(task, description="❌ 新聞資料爬取失敗")
            console.print(f"[red]錯誤: {e}[/red]")


@cli.command()
@click.pass_context
def crawl_all(ctx):
    """爬取所有資料（人事 + 新聞）"""
    console.print("[blue]開始爬取所有資料...[/blue]")
    
    # 執行人事資料爬取
    ctx.invoke(crawl_personnel)
    
    console.print()  # 空行分隔
    
    # 執行新聞資料爬取
    ctx.invoke(crawl_news)
    
    console.print("[green]所有資料爬取完成！[/green]")


@cli.command()
@click.option('--format', '-f', multiple=True, default=['json'], 
              help='輸出格式 (json, csv, txt)')
@click.pass_context
def process_data(ctx, format):
    """處理和格式化爬取的資料"""
    config = ctx.obj['config']
    
    console.print("[blue]開始處理資料...[/blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("處理資料中...", total=None)
        
        try:
            formatter = DataFormatter(config)
            data_dirs = config.get_data_directories()
            file_names = config.get_file_names()
            
            # 載入原始資料
            from src.utils import FileHandler
            
            personnel_file = f"{data_dirs['raw']}/{file_names['personnel_data']}"
            news_file = f"{data_dirs['raw']}/{file_names['news_data']}"
            
            personnel_data = FileHandler.load_json_file(personnel_file) or {}
            news_data = FileHandler.load_json_file(news_file) or {}
            
            if not personnel_data and not news_data:
                console.print("[yellow]沒有找到可處理的資料[/yellow]")
                return
            
            # 格式化資料
            formatted_personnel = formatter.format_personnel_data(personnel_data)
            formatted_news = formatter.format_news_data(news_data)
            
            # 合併資料
            merged_data = formatter.merge_datasets(formatted_personnel, formatted_news)
            
            # 匯出資料
            output_files = formatter.export_to_formats(
                merged_data, 
                data_dirs['processed'], 
                list(format)
            )
            
            progress.update(task, description="✅ 資料處理完成")
            
            # 顯示結果
            table = Table(title="資料處理結果")
            table.add_column("格式", style="cyan")
            table.add_column("檔案路徑", style="green")
            
            for fmt, file_path in output_files.items():
                table.add_row(fmt.upper(), file_path)
            
            console.print(table)
            
        except Exception as e:
            progress.update(task, description="❌ 資料處理失敗")
            console.print(f"[red]錯誤: {e}[/red]")


@cli.command()
@click.pass_context
def build_index(ctx):
    """建立向量搜尋索引"""
    config = ctx.obj['config']
    
    console.print("[blue]開始建立向量索引...[/blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("建立向量索引中...", total=None)
        
        try:
            vector_processor = VectorProcessor(config)
            
            # 載入處理後的資料
            from src.utils import FileHandler
            data_dirs = config.get_data_directories()
            
            # 尋找最新的處理資料檔案
            processed_dir = Path(data_dirs['processed'])
            json_files = list(processed_dir.glob("scu_data_*.json"))
            
            if not json_files:
                console.print("[yellow]沒有找到處理後的資料檔案，請先執行 process-data[/yellow]")
                return
            
            # 使用最新的檔案
            latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
            data = FileHandler.load_json_file(latest_file)
            
            if not data:
                console.print("[red]無法載入資料檔案[/red]")
                return
            
            # 建立索引
            success = vector_processor.create_vector_index(data)
            
            if success:
                progress.update(task, description="✅ 向量索引建立完成")
                console.print("[green]向量搜尋索引建立成功！[/green]")
            else:
                progress.update(task, description="❌ 向量索引建立失敗")
                console.print("[red]向量索引建立失敗[/red]")
                
        except Exception as e:
            progress.update(task, description="❌ 向量索引建立失敗")
            console.print(f"[red]錯誤: {e}[/red]")


@cli.command()
@click.argument('query')
@click.option('--top-k', '-k', default=5, help='返回結果數量')
@click.option('--threshold', '-t', default=0.3, help='相似度閾值 (0.0-1.0)')
@click.pass_context
def search(ctx, query, top_k, threshold):
    """搜尋資料"""
    config = ctx.obj['config']
    
    console.print(f"[blue]搜尋: {query}[/blue]")
    
    try:
        vector_processor = VectorProcessor(config)
        
        # 載入索引
        if not vector_processor.load_vector_index():
            console.print("[yellow]向量索引不存在，請先執行 build-index[/yellow]")
            return
        
        # 執行搜尋
        results = vector_processor.search(query, top_k=top_k, similarity_threshold=threshold)
        
        if not results:
            console.print("[yellow]沒有找到相關結果[/yellow]")
            return
        
        # 顯示結果
        for i, result in enumerate(results, 1):
            console.print(f"\n[cyan]結果 {i} (相似度: {result['score']:.3f})[/cyan]")
            console.print(f"[green]{result['content'][:200]}...[/green]")
            
            metadata = result.get('metadata', {})
            if metadata:
                console.print(f"[dim]來源: {metadata.get('source', 'unknown')} | "
                            f"標題: {metadata.get('title', 'unknown')}[/dim]")
        
    except Exception as e:
        console.print(f"[red]搜尋失敗: {e}[/red]")


@cli.command()
@click.pass_context
def status(ctx):
    """顯示系統狀態"""
    config = ctx.obj['config']
    
    table = Table(title="系統狀態")
    table.add_column("項目", style="cyan")
    table.add_column("狀態", style="green")
    
    # 檢查資料目錄
    data_dirs = config.get_data_directories()
    for name, path in data_dirs.items():
        exists = Path(path).exists()
        status_text = "✅ 存在" if exists else "❌ 不存在"
        table.add_row(f"{name} 目錄", status_text)
    
    # 檢查資料檔案
    file_names = config.get_file_names()
    for name, filename in file_names.items():
        file_path = Path(data_dirs['raw']) / filename
        exists = file_path.exists()
        status_text = "✅ 存在" if exists else "❌ 不存在"
        table.add_row(f"{name} 檔案", status_text)
    
    # 檢查向量索引
    vector_index_path = Path(data_dirs['vector_db']) / "index"
    exists = vector_index_path.exists()
    status_text = "✅ 存在" if exists else "❌ 不存在"
    table.add_row("向量索引", status_text)
    
    console.print(table)


@cli.command()
@click.argument('question')
@click.option('--top-k', '-k', default=5, help='檢索結果數量')
@click.option('--threshold', '-t', default=0.3, help='相似度閾值 (0.0-1.0)')
@click.pass_context
def ask(ctx, question, top_k, threshold):
    """RAG 問答系統 - 基於檢索資料的智能問答"""
    config = ctx.obj['config']

    console.print(f"[blue]❓ 問題: {question}[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("分析問題並檢索相關資料...", total=None)

        try:
            # 初始化簡化 RAG 處理器
            rag_processor = SimpleRAGProcessor(config)

            # 執行問答
            result = rag_processor.answer_question(
                question,
                top_k=top_k,
                similarity_threshold=threshold
            )

            progress.update(task, description="✅ 分析完成")

            if result.get("success"):
                # 顯示答案
                console.print(f"\n[green]🤖 回答:[/green]")
                console.print(f"[white]{result['answer']}[/white]")

                # 顯示資料來源
                sources = result.get("sources", [])
                if sources:
                    console.print(f"\n[cyan]📚 參考資料 ({len(sources)} 個來源):[/cyan]")

                    for i, source in enumerate(sources, 1):
                        console.print(f"\n[yellow]{i}. {source['title']}[/yellow]")
                        console.print(f"   [dim]來源: {source['source']} | 相似度: {source['score']:.3f}[/dim]")
                        console.print(f"   [dim]{source['content_preview']}[/dim]")
                        if source['url']:
                            console.print(f"   [dim]連結: {source['url']}[/dim]")

                # 顯示統計資訊
                console.print(f"\n[dim]檢索到 {result['retrieved_count']} 個相關文件[/dim]")

            else:
                progress.update(task, description="❌ 回答失敗")
                console.print(f"[red]❌ 錯誤: {result.get('error', '未知錯誤')}[/red]")

                # 顯示建議
                suggestions = result.get("suggestions", [])
                if suggestions:
                    console.print(f"\n[yellow]💡 建議嘗試以下關鍵字:[/yellow]")
                    for suggestion in suggestions:
                        console.print(f"   • {suggestion}")

        except Exception as e:
            progress.update(task, description="❌ 回答失敗")
            console.print(f"[red]錯誤: {e}[/red]")


@cli.command()
@click.pass_context
def chat(ctx):
    """進入互動式問答模式"""
    config = ctx.obj['config']

    console.print(f"[green]🤖 東吳大學智能助理[/green]")
    console.print("[dim]基於檢索資料的智能問答系統[/dim]")
    console.print("[dim]輸入 'quit' 或 'exit' 退出[/dim]")
    console.print()

    try:
        rag_processor = SimpleRAGProcessor(config)

        while True:
            # 獲取使用者輸入
            question = console.input("[blue]❓ 請輸入您的問題: [/blue]")

            if question.lower() in ['quit', 'exit', '退出', '結束']:
                console.print("[green]再見！[/green]")
                break

            if not question.strip():
                continue

            # 執行問答
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("思考中...", total=None)

                result = rag_processor.answer_question(question)

                progress.update(task, description="✅ 回答完成")

            if result.get("success"):
                console.print(f"\n[green]🤖 回答:[/green]")
                console.print(f"[white]{result['answer']}[/white]")

                # 簡化的來源顯示
                sources = result.get("sources", [])
                if sources:
                    console.print(f"\n[dim]📚 基於 {len(sources)} 個相關資料來源[/dim]")
            else:
                console.print(f"[red]❌ {result.get('error', '無法回答此問題')}[/red]")

            console.print()  # 空行分隔

    except KeyboardInterrupt:
        console.print("\n[green]再見！[/green]")
    except Exception as e:
        console.print(f"[red]聊天模式錯誤: {e}[/red]")


if __name__ == '__main__':
    cli()
