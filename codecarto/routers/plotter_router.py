from fastapi import APIRouter

from codecarto.models.plot_data import PlotOptions
from codecarto.models.source_data import Directory, Folder, File
from codecarto.services.parser_service import ParserService
from codecarto.services.palette_service import apply_styles
from codecarto.services.graph_serializer import GraphSerializer
from codecarto.util.exceptions import proc_exception
from codecarto.util.utilities import Log, generate_return

PlotterRouter = APIRouter()


@PlotterRouter.post("/whole_repo")
async def plot_whole_repo(directory: Directory, options: PlotOptions):
    try:
        # Select parser based on parse_by option
        if options.parse_by == "ast":
            # AST mode - parse code structure
            graph = await ParserService.parse_code_directory(directory)
        elif options.parse_by == "dependencies":
            # Dependencies mode - parse import relationships
            graph = await ParserService.parse_dependancy(directory)
        else:
            # Default: directory mode - parse filesystem structure
            graph = await ParserService.parse_directory(directory)

        styled_graph = apply_styles(graph)

        gjgf = GraphSerializer.serialize_to_gjgf(styled_graph, options)
        metadata = GraphSerializer.create_metadata(styled_graph, options)

        return generate_return(results={
            "graph": gjgf,
            "metadata": metadata
        })
    except Exception as exc:
        proc_exception(
            "plot_whole_repo",
            "Error when plotting GitHub repo",
            {"directory": directory},
            exc,
        )


@PlotterRouter.post("/whole_repo_deps")
async def plot_whole_repo_deps(directory: Directory, options: PlotOptions):
    try:
        graph = await ParserService.parse_dependancy(directory)
        styled_graph = apply_styles(graph)

        gjgf = GraphSerializer.serialize_to_gjgf(styled_graph, options, isDependencyPlot=True)
        metadata = GraphSerializer.create_metadata(styled_graph, options)

        return generate_return(results={
            "graph": gjgf,
            "metadata": metadata
        })
    except Exception as exc:
        proc_exception(
            "plot_whole_repo_deps",
            "Error when plotting GitHub repo dependencies",
            {"directory": directory},
            exc,
        )


@PlotterRouter.post("/folder")
async def plot_folder(folder: Folder, options: PlotOptions) -> dict:
    try:
        graph = await ParserService.parse_code(folder)
        styled_graph = apply_styles(graph)

        gjgf = GraphSerializer.serialize_to_gjgf(styled_graph, options)
        metadata = GraphSerializer.create_metadata(styled_graph, options)

        return generate_return(results={
            "graph": gjgf,
            "metadata": metadata
        })
    except Exception as e:
        return proc_exception(
            "plot_folder",
            "Error generating plot",
            {"folder": folder.name},
            e,
        )


@PlotterRouter.post("/file")
async def plot_file(file: File, options: PlotOptions) -> dict:
    try:
        folder = Folder(name="root", size=0, files=[file], folders=[])
        graph = await ParserService.parse_code(folder)
        styled_graph = apply_styles(graph)

        gjgf = GraphSerializer.serialize_to_gjgf(styled_graph, options)
        metadata = GraphSerializer.create_metadata(styled_graph, options)

        return generate_return(results={
            "graph": gjgf,
            "metadata": metadata
        })
    except Exception as e:
        return proc_exception(
            "plot_file",
            "Error generating plot",
            {"file": file.name},
            e,
        )


@PlotterRouter.post("/url")
async def plot_url(url: str, options: PlotOptions) -> dict:
    try:
        graph = await ParserService.parse_raw(url)
        styled_graph = apply_styles(graph)

        gjgf = GraphSerializer.serialize_to_gjgf(styled_graph, options)
        metadata = GraphSerializer.create_metadata(styled_graph, options)

        return generate_return(results={
            "graph": gjgf,
            "metadata": metadata
        })
    except Exception as e:
        return proc_exception(
            "plot_url",
            "Error generating plot",
            {"url": url},
            e,
        )


@PlotterRouter.post("/local_directory")
async def plot_local_directory(path: str, options: PlotOptions) -> dict:
    """
    Plot a local directory from filesystem path.
    Reads directory contents and parses based on selected mode.
    """
    try:
        from pathlib import Path
        import os

        # Validate path exists
        dir_path = Path(path)
        if not dir_path.exists():
            return generate_return(
                status=404,
                message=f"Directory not found: {path}",
                results=None
            )

        if not dir_path.is_dir():
            return generate_return(
                status=400,
                message=f"Path is not a directory: {path}",
                results=None
            )

        # Convert filesystem directory to Directory model
        directory = await ParserService.parse_local_directory(str(dir_path))

        # Select parser based on parse_by option
        if options.parse_by == "ast":
            graph = await ParserService.parse_code_directory(directory)
        elif options.parse_by == "dependencies":
            graph = await ParserService.parse_dependancy(directory)
        else:
            graph = await ParserService.parse_directory(directory)

        styled_graph = apply_styles(graph)

        gjgf = GraphSerializer.serialize_to_gjgf(styled_graph, options)
        metadata = GraphSerializer.create_metadata(styled_graph, options)

        return generate_return(results={
            "graph": gjgf,
            "metadata": metadata
        })
    except Exception as e:
        return proc_exception(
            "plot_local_directory",
            "Error plotting local directory",
            {"path": path},
            e,
        )
