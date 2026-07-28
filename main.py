import typer
import asyncio
from rich.console import Console
from rich.panel import Panel

# Ajuste de importaciones: Todas las piezas vienen de la carpeta skills
from skills import red_interceptor, data_cleaner, db_manager

app = typer.Typer()
console = Console()

@app.command("db-init")
def inicializar_entorno():
    """Inicializa las tablas y la estructura transaccional de reserva."""
    try:
        db_manager.inicializar_bd()
        console.print("[bold green]✅ Base de datos y tabla de reserva inicializadas correctamente.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]❌ Error al inicializar la base de datos:[/bold red] {e}")

@app.command("run")
def ejecutar_pipeline(numero_juicio: str = typer.Argument(..., help="Número de expediente a extraer")):
    console.print(Panel.fit(f"Iniciando extracción para: [bold cyan]{numero_juicio}[/bold cyan]"))
    
    try:
        # 1. Extracción asíncrona (El puente hacia Playwright)
        console.print("[dim]Interceptando red en E-SATJE...[/dim]")
        df_crudo = asyncio.run(red_interceptor.extraer_via_red(numero_juicio))
        
        if df_crudo.empty:
            console.print("[bold yellow]⚠️ No se interceptaron datos JSON relevantes.[/bold yellow]")
            return

        # 2. Limpieza síncrona (Pandas)
        console.print("[dim]Normalizando esquemas y cabeceras...[/dim]")
        df_limpio = data_cleaner.normalizar_columnas(df_crudo)
        
        # 3. Transacción a base de datos (SQLite)
        console.print("[dim]Ejecutando inserción transaccional...[/dim]")
        db_manager.registrar_extraccion(numero_juicio, df_limpio)
        
        console.print("[bold green]🚀 Operación exitosa. Datos consolidados y reserva actualizada.[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Fallo en el pipeline:[/bold red] {e}")

if __name__ == "__main__":
    app()