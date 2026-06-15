"""CLI 入口 — 小说 Agent 命令行工具"""

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .llm import LLMClient, LLMConfig
from .models.character import CharacterCard
from .models.outline import OutlineTree
from .models.summary import SectionSummary
from .models.world import WorldSetting
from .pipeline import NovelAgentPipeline

app = typer.Typer(
    name="novel-agent",
    help="小说写作 Agent 管道 — 准备→创作→审查→修订→润色",
)
console = Console()


# ═══════════════════════════════════════════════════════════
# 子命令：run — 执行完整管道
# ═══════════════════════════════════════════════════════════

@app.command()
def run(
    section_id: str = typer.Option(
        ..., "--section", "-s", help="当前要写的 section ID"
    ),
    outline_file: Path = typer.Option(
        ..., "--outline", "-o", help="大纲 JSON 文件路径"
    ),
    characters_file: Path = typer.Option(
        ..., "--characters", "-c", help="角色 JSON 文件路径"
    ),
    world_file: Path = typer.Option(
        ..., "--world", "-w", help="世界观 JSON 文件路径"
    ),
    summaries_file: Optional[Path] = typer.Option(
        None, "--summaries", help="已完成章节摘要 JSON 文件路径"
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", "-k", help="DeepSeek API Key（也可通过 DEEPSEEK_API_KEY 环境变量设置）",
        envvar="DEEPSEEK_API_KEY",
    ),
    model: str = typer.Option(
        "deepseek-chat", "--model", "-m", help="模型名称"
    ),
    no_llm: bool = typer.Option(
        False, "--no-llm", help="不使用 LLM，仅用占位输出测试管道"
    ),
    content_file: Optional[Path] = typer.Option(
        None, "--content", help="手动提供正文（跳过创作者）"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="显示详细日志"
    ),
):
    """执行完整的写作管道：准备 → 创作 → 审查 → 修订 → 润色"""
    # 加载数据
    outline_data = _load_json(outline_file)
    characters_data = _load_json(characters_file)
    world_data = _load_json(world_file)
    summaries_data = _load_json(summaries_file) if summaries_file else []

    outline_tree = OutlineTree(**outline_data)
    characters = [CharacterCard(**c) for c in characters_data]
    world_settings = [WorldSetting(**w) for w in world_data]
    summaries = [SectionSummary(**s) for s in summaries_data]

    content_override = None
    if content_file:
        content_override = content_file.read_text(encoding="utf-8")

    # 创建 LLM 客户端
    llm = None
    if not no_llm:
        actual_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        if not actual_key:
            console.print(
                "[yellow]警告：未设置 API Key，将使用占位模式。"
                "请通过 --api-key 或环境变量 DEEPSEEK_API_KEY 设置。[/yellow]"
            )
        else:
            config = LLMConfig(api_key=actual_key, model=model)
            llm = LLMClient(config)
            console.print(f"[green]LLM 已连接: {model}[/green]")

    # 执行管道
    pipeline = NovelAgentPipeline(llm=llm)
    result = pipeline.run(
        section_id=section_id,
        outline_tree=outline_tree,
        characters=characters,
        world_settings=world_settings,
        summaries=summaries,
        content_override=content_override,
    )

    # 输出结果
    _print_result(result, verbose=verbose)

    # 输出最终正文到文件
    output_path = Path(f"output_{section_id}.txt")
    output_path.write_text(result.final_content, encoding="utf-8")
    console.print(f"\n[green]最终正文已保存到: {output_path}[/green]")


# ═══════════════════════════════════════════════════════════
# 子命令：preview — 预览 prompt
# ═══════════════════════════════════════════════════════════

@app.command()
def preview(
    section_id: str = typer.Option(
        ..., "--section", "-s", help="当前要写的 section ID"
    ),
    outline_file: Path = typer.Option(
        ..., "--outline", "-o", help="大纲 JSON 文件路径"
    ),
    characters_file: Path = typer.Option(
        ..., "--characters", "-c", help="角色 JSON 文件路径"
    ),
    world_file: Path = typer.Option(
        ..., "--world", "-w", help="世界观 JSON 文件路径"
    ),
    summaries_file: Optional[Path] = typer.Option(
        None, "--summaries", help="已完成章节摘要 JSON 文件路径"
    ),
    agent: str = typer.Option(
        "all", "--agent", "-a", help="指定 Agent: preparer/writer/reviewer/reviser/polisher/all"
    ),
):
    """预览各 Agent 将接收到的 prompt 内容（不实际执行）"""
    outline_data = _load_json(outline_file)
    characters_data = _load_json(characters_file)
    world_data = _load_json(world_file)
    summaries_data = _load_json(summaries_file) if summaries_file else []

    outline_tree = OutlineTree(**outline_data)
    characters = [CharacterCard(**c) for c in characters_data]
    world_settings = [WorldSetting(**w) for w in world_data]
    summaries = [SectionSummary(**s) for s in summaries_data]

    pipeline = NovelAgentPipeline()
    step_results = pipeline.run_step_by_step(
        section_id=section_id,
        outline_tree=outline_tree,
        characters=characters,
        world_settings=world_settings,
        summaries=summaries,
    )

    if agent in ("all", "preparer"):
        console.print(Panel.fit("[准备者输出 (JSON)]", style="blue"))
        console.print_json(json.dumps(step_results["preparation"], ensure_ascii=False))

    if agent in ("all", "writer"):
        console.print(Panel.fit("[创作者 Prompt]", style="cyan"))
        console.print(step_results["writer_prompt"])

    if agent in ("all", "reviewer"):
        console.print(Panel.fit("[审查者 Prompt]", style="yellow"))
        console.print(step_results["reviewer_prompt"])

    if agent in ("all", "reviser"):
        console.print(Panel.fit("[修订者 Prompt]", style="magenta"))
        console.print(step_results["reviser_prompt"])

    if agent in ("all", "polisher"):
        console.print(Panel.fit("[润色者 Prompt]", style="green"))
        console.print(step_results["polisher_prompt"])


# ═══════════════════════════════════════════════════════════
# 子命令：validate — 验证数据
# ═══════════════════════════════════════════════════════════

@app.command()
def validate(
    outline_file: Path = typer.Option(
        ..., "--outline", "-o", help="大纲 JSON 文件路径"
    ),
    characters_file: Path = typer.Option(
        ..., "--characters", "-c", help="角色 JSON 文件路径"
    ),
    world_file: Path = typer.Option(
        ..., "--world", "-w", help="世界观 JSON 文件路径"
    ),
    summaries_file: Optional[Path] = typer.Option(
        None, "--summaries", help="已完成章节摘要 JSON 文件路径"
    ),
):
    """验证 JSON 数据文件的结构是否正确"""
    errors: list[str] = []

    try:
        outline_data = _load_json(outline_file)
        outline_tree = OutlineTree(**outline_data)
        sections = outline_tree.get_ordered_sections()
        console.print(
            f"[green][OK][/green] 大纲 ({len(outline_tree.volumes)} 卷, {len(sections)} 节)"
        )
    except Exception as e:
        errors.append(f"大纲: {e}")

    try:
        characters_data = _load_json(characters_file)
        characters = [CharacterCard(**c) for c in characters_data]
        console.print(f"[green][OK][/green] 角色 ({len(characters)} 个)")
    except Exception as e:
        errors.append(f"角色: {e}")

    try:
        world_data = _load_json(world_file)
        world_settings = [WorldSetting(**w) for w in world_data]
        console.print(f"[green][OK][/green] 世界观 ({len(world_settings)} 个)")
    except Exception as e:
        errors.append(f"世界观: {e}")

    if summaries_file:
        try:
            summaries_data = _load_json(summaries_file)
            summaries = [SectionSummary(**s) for s in summaries_data]
            console.print(f"[green][OK][/green] 摘要 ({len(summaries)} 条)")
        except Exception as e:
            errors.append(f"摘要: {e}")

    if errors:
        console.print("\n[red]校验失败:[/red]")
        for err in errors:
            console.print(f"  [red][FAIL][/red] {err}")
        raise typer.Exit(code=1)


# ═══════════════════════════════════════════════════════════
# 子命令：generate-sample
# ═══════════════════════════════════════════════════════════

@app.command()
def generate_sample(
    output_dir: Path = typer.Option(
        Path("sample_data"), "--output", help="输出目录"
    ),
):
    """生成示例 JSON 数据文件"""
    from .sample_data import generate_all_samples
    generate_all_samples(output_dir)
    console.print(f"[green]示例数据已生成到: {output_dir}[/green]")


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════

def _load_json(filepath: Path) -> dict | list:
    if not filepath.exists():
        console.print(f"[red]文件不存在: {filepath}[/red]")
        raise typer.Exit(code=1)
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        console.print(f"[red]JSON 解析错误 ({filepath}): {e}[/red]")
        raise typer.Exit(code=1)


def _print_result(result, verbose: bool = False):
    prep = result.preparation

    prep_table = Table(title="[准备者] 写作准备", show_header=False)
    prep_table.add_column("项目", style="cyan")
    prep_table.add_column("内容")
    prep_table.add_row("当前节", prep.current_section_title)
    prep_table.add_row("起始状态", prep.starting_state[:200])
    prep_table.add_row("要写什么", prep.what_to_write[:200])
    prep_table.add_row("终止状态", prep.ending_state[:200])
    prep_table.add_row(
        "涉及角色",
        ", ".join(c.name for c in prep.involved_characters) or "(无)",
    )
    prep_table.add_row(
        "涉及世界观",
        ", ".join(w.name for w in prep.involved_world_settings) or "(无)",
    )
    console.print(prep_table)

    review = result.review_result
    if review.issues:
        issue_table = Table(title=f"[审查者] 发现 {len(review.issues)} 个问题")
        issue_table.add_column("严重度", style="red")
        issue_table.add_column("类型")
        issue_table.add_column("描述")
        for issue in review.issues:
            issue_table.add_row(issue.severity, issue.issue_type, issue.description[:100])
        console.print(issue_table)
    else:
        console.print("[审查者] [green]未发现问题[/green]")

    console.print(Panel.fit("最终正文:", style="green"))
    content_preview = (
        result.final_content[:500] + "..."
        if len(result.final_content) > 500
        else result.final_content
    )
    console.print(content_preview)

    if verbose:
        console.print(Panel.fit("\n".join(result.logs), title="执行日志"))


def main():
    app()


if __name__ == "__main__":
    main()
