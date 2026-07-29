# main.py
"""
Antigravity CLI - Tool de automatización agéntica y gestión de skills.
Inspirado en el curso completo de Google Antigravity & Agentic Workflows.
"""

import asyncio
from pathlib import Path
import typer
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from skills import (
    extraer_via_red,
    normalizar_columnas,
    DBQueueManager,
    auditar_base_datos,
)

app = typer.Typer(help="🚀 Antigravity CLI - Framework agéntico de automatización y scraping para e-SATJE")
console = Console()
db = DBQueueManager()


@app.command("db-init")
def inicializar_entorno():
    """Inicializa las tablas SQLite y la reserva atómica de transacciones."""
    try:
        db.inicializar_bd()
        console.print(Panel.fit("✅ Base de datos transaccional inicializada correctamente.", title="Antigravity DB", style="bold green"))
    except Exception as e:
        console.print(f"[bold red]❌ Error al inicializar la base de datos:[/bold red] {e}")


@app.command("run")
def ejecutar_pipeline(numero_juicio: str = typer.Argument(..., help="Número de causa a procesar")):
    """Ejecuta el flujo agéntico completo para una causa específica."""
    console.print(Panel.fit(f"Iniciando flujo para: [bold cyan]{numero_juicio}[/bold cyan]", title="Antigravity Agent"))
    
    try:
        with Console().status("[bold cyan]Interceptando red en E-SATJE con Playwright...[/bold cyan]"):
            df_crudo = asyncio.run(extraer_via_red(numero_juicio))
        
        if df_crudo.empty:
            console.print("[bold yellow]⚠️ No se interceptaron datos JSON relevantes.[/bold yellow]")
            db.registrar_error(numero_juicio, "Respuesta XHR vacía o sin datos")
            return

        console.print("[dim]Normalizando esquemas y celdas...[/dim]")
        df_limpio = normalizar_columnas(df_crudo)
        
        console.print("[dim]Guardando en la base de datos transaccional...[/dim]")
        db.registrar_extraccion(numero_juicio, df_limpio)
        
        console.print("[bold green]🚀 Operación exitosa. Causa consolidada en SQLite.[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Fallo en el pipeline:[/bold red] {e}")
        db.registrar_error(numero_juicio, str(e))


@app.command("batch")
def ejecutar_lote(
    archivo_fuente: Path = typer.Argument(..., help="Ruta del archivo CSV, Excel o TXT con las causas"),
    columna: str = typer.Option("NUMERO_JUICIO", "--columna", "-c", help="Nombre de la columna en el CSV/Excel")
):
    """Carga y procesa masivamente un lote de causas."""
    if not archivo_fuente.exists():
        console.print(f"[bold red]❌ El archivo {archivo_fuente} no existe.[/bold red]")
        return

    console.print(f"[cyan]Cargando causas desde {archivo_fuente}...[/cyan]")
    causas = []
    
    if archivo_fuente.suffix in [".csv"]:
        df_in = pd.read_csv(archivo_fuente, low_memory=False)
        col_target = columna if columna in df_in.columns else df_in.columns[0]
        causas = df_in[col_target].dropna().astype(str).str.strip().tolist()
    elif archivo_fuente.suffix in [".xlsx", ".xls"]:
        df_in = pd.read_excel(archivo_fuente)
        col_target = columna if columna in df_in.columns else df_in.columns[0]
        causas = df_in[col_target].dropna().astype(str).str.strip().tolist()
    else:
        with open(archivo_fuente, "r", encoding="utf-8") as f:
            causas = [line.strip() for line in f if line.strip()]

    db.poblar_causas(causas)
    console.print(f"[bold green]Poblada la reserva con {len(causas)} causa(s).[/bold green]")

    # Procesar la cola
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Procesando causas pendientes...[/cyan]", total=len(causas))

        while True:
            juicio = db.obtener_siguiente_pendiente()
            if not juicio:
                break
            
            try:
                progress.update(task, description=f"[cyan]Procesando {juicio}...[/cyan]")
                df_crudo = asyncio.run(extraer_via_red(juicio))
                if not df_crudo.empty:
                    df_limpio = normalizar_columnas(df_crudo)
                    db.registrar_extraccion(juicio, df_limpio)
                else:
                    db.registrar_error(juicio, "Red sin respuesta")
            except Exception as e:
                db.registrar_error(juicio, str(e))

            progress.advance(task)

    console.print(Panel.fit("✨ Procesamiento de lote finalizado.", style="bold green"))


@app.command("status")
def mostrar_estado():
    """Muestra el panel de estado de la cola transaccional en SQLite."""
    stats = db.obtener_estadisticas()
    
    table = Table(title="📊 Dashboard de Transacciones Antigravity", header_style="bold magenta")
    table.add_column("Estado", style="cyan", justify="center")
    table.add_column("Cantidad", style="bold white", justify="right")

    colores = {
        "PENDIENTE": "yellow",
        "EN_PROCESO": "blue",
        "EXITO": "green",
        "ERROR": "red"
    }

    total = 0
    for estado, cantidad in stats.items():
        color = colores.get(estado, "white")
        table.add_row(f"[{color}]{estado}[/{color}]", str(cantidad))
        total += cantidad

    table.add_section()
    table.add_row("[bold]TOTAL[/bold]", f"[bold]{total}[/bold]")
    console.print(table)


@app.command("retry")
def reiniciar_fallidos(max_reintentos: int = typer.Option(3, "--max", "-m", help="Límite máximo de reintentos acumulados")):
    """Reinicia causas con estado ERROR de vuelta a PENDIENTE."""
    modificados = db.reiniciar_errores(max_reintentos=max_reintentos)
    console.print(f"[bold green]🔄 Se reiniciaron {modificados} causa(s) de ERROR a PENDIENTE.[/bold green]")


@app.command("audit")
def auditar_sistema():
    """Ejecuta una auditoría de integridad sobre la base de datos."""
    reporte = auditar_base_datos(db.db_path)
    
    table = Table(title="🏥 Auditoría de Calidad e Integridad Antigravity", header_style="bold cyan")
    table.add_column("Métrica", style="bold")
    table.add_column("Valor", style="yellow", justify="right")

    table.add_row("Total Expedientes Guardados", str(reporte["total_expedientes_guardados"]))
    table.add_row("Total en Cola de Reserva", str(reporte["total_reserva"]))
    table.add_row("Errores Registrados", str(reporte["errores_registrados"]))
    table.add_row("Salud Global del Sistema", f"{reporte['salud_porcentaje']}%")

    console.print(table)


@app.command("skills-list")
def listar_skills():
    """Lista las skills disponibles en el repositorio."""
    table = Table(title="🧠 Catálogo de Skills Agénticas Disponibles", header_style="bold green")
    table.add_column("Nombre Skill", style="bold yellow")
    table.add_column("Descripción / Capacidades", style="white")

    skills_dir = Path(__file__).parent / "skills"
    for item in skills_dir.iterdir():
        if item.is_dir() and (item / "SKILL.md").exists():
            skill_md = item / "SKILL.md"
            with open(skill_md, "r", encoding="utf-8") as f:
                content = f.read()
                # extraer descripción simple de la cabecera
                desc = "Skill de automatización"
                for line in content.split("\n"):
                    if line.startswith("description:"):
                        desc = line.replace("description:", "").strip().strip('"')
                        break
            table.add_row(item.name, desc)

    console.print(table)


if __name__ == "__main__":
    app()