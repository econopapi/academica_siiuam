import argparse
import json
import os
import time
from datetime import datetime
from typing import List

from main import SIIAScraper


def get_total_courses() -> int:
    """Open one session to discover how many UEA are available."""
    scraper = SIIAScraper()
    try:
        scraper.login()
        cursos_data = scraper.access_courses()
        return len(cursos_data)
    finally:
        scraper.driver.quit()


def run_single_course(course_index: int, ui_settle_seconds: float = 0.0) -> dict:
    """Run one programmatic execution equivalent to choosing a single UEA."""
    scraper = SIIAScraper()
    result = {
        "index": course_index,
        "course_name": None,
        "status": "error",
        "error": None,
    }

    try:
        scraper.login()
        cursos_data = scraper.access_courses()

        if course_index >= len(cursos_data):
            raise IndexError(
                f"Indice {course_index} fuera de rango. Total disponible: {len(cursos_data)}"
            )

        selected_course = cursos_data[course_index]
        result["course_name"] = selected_course.get("name_text")

        print(
            f"\n>>> Ejecutando UEA [{course_index}] - {result['course_name']}"
        )
        if ui_settle_seconds > 0:
            print(f"> Esperando {ui_settle_seconds:.1f}s para estabilizar interfaz...")
            time.sleep(ui_settle_seconds)

        scraper.scrape_all_groups(selected_course)

        result["status"] = "ok"
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result
    finally:
        scraper.driver.quit()


def parse_indices(raw_indices: str) -> List[int]:
    """Parse a comma-separated list like '0,2,5' into sorted unique ints."""
    parsed = []
    for piece in raw_indices.split(","):
        item = piece.strip()
        if not item:
            continue
        parsed.append(int(item))
    if not parsed:
        raise ValueError("No se encontraron indices validos en --only-indices")
    return sorted(set(parsed))


def load_failed_indices(summary_path: str) -> List[int]:
    """Load failed indices from a previously generated run_summary JSON."""
    with open(summary_path, "r", encoding="utf-8") as file:
        summary = json.load(file)

    results = summary.get("results", [])
    failed_indices = [
        item["index"]
        for item in results
        if item.get("status") != "ok" and isinstance(item.get("index"), int)
    ]

    if not failed_indices:
        raise ValueError("No hay indices fallidos en el resumen proporcionado.")

    return sorted(set(failed_indices))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Ejecuta main.py de forma programatica para todas las UEA "
            "(de 0 hasta N-1) y guarda resultados en una carpeta raiz."
        )
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Nombre de la carpeta raiz donde se guardaran todos los resultados.",
    )
    parser.add_argument(
        "--retry-failed-from",
        help=(
            "Ruta a un run_summary.json previo para reintentar solo indices fallidos. "
            "Ejemplo: TDCSH/run_summary.json"
        ),
    )
    parser.add_argument(
        "--only-indices",
        help=(
            "Lista de indices a ejecutar separados por coma. "
            "Ejemplo: 1,3,7"
        ),
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help=(
            "Numero maximo de intentos por indice cuando falla (default: 3)."
        ),
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=4.0,
        help=(
            "Segundos de espera entre intentos fallidos (default: 4.0)."
        ),
    )
    parser.add_argument(
        "--ui-settle-seconds",
        type=float,
        default=1.5,
        help=(
            "Espera previa antes de abrir la UEA para reducir stale por refresco (default: 1.5)."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.max_retries < 1:
        raise ValueError("--max-retries debe ser >= 1")
    if args.retry_delay < 0:
        raise ValueError("--retry-delay no puede ser negativo")
    if args.ui_settle_seconds < 0:
        raise ValueError("--ui-settle-seconds no puede ser negativo")

    output_root = os.path.abspath(args.name)
    os.makedirs(output_root, exist_ok=True)

    print("\n>>> [RUNNER AUTOMATICO SIIA]")
    print(f"> Carpeta de salida: {output_root}")

    original_cwd = os.getcwd()
    os.chdir(output_root)

    try:
        indices_to_run = None
        if args.retry_failed_from:
            summary_path = os.path.abspath(args.retry_failed_from)
            indices_to_run = load_failed_indices(summary_path)
            print(f"> Reintento desde resumen: {summary_path}")
            print(f"> Indices fallidos detectados: {indices_to_run}")
        elif args.only_indices:
            indices_to_run = parse_indices(args.only_indices)
            print(f"> Ejecucion parcial de indices: {indices_to_run}")

        if indices_to_run is None:
            total_courses = get_total_courses()
            indices_to_run = list(range(total_courses))
            print(f"> UEA detectadas: {total_courses}")
        else:
            total_courses = len(indices_to_run)
            print(f"> UEA a ejecutar en esta corrida: {total_courses}")

        run_results = []
        for index in indices_to_run:
            result = None
            for attempt in range(1, args.max_retries + 1):
                if attempt > 1:
                    print(
                        f"> Reintentando indice {index} (intento {attempt}/{args.max_retries})..."
                    )

                result = run_single_course(
                    index, ui_settle_seconds=args.ui_settle_seconds
                )

                if result["status"] == "ok":
                    result["attempts"] = attempt
                    break

                print(
                    f"> Detalle intento {attempt}/{args.max_retries} para indice {index}: {result['error']}"
                )

                if attempt < args.max_retries:
                    print(
                        f"> Fallo indice {index}. Esperando {args.retry_delay:.1f}s antes del siguiente intento..."
                    )
                    time.sleep(args.retry_delay)

            if result is None:
                # Defensive fallback, should never happen.
                result = {
                    "index": index,
                    "course_name": None,
                    "status": "error",
                    "error": "No se pudo ejecutar el indice.",
                    "attempts": args.max_retries,
                }
            elif "attempts" not in result:
                result["attempts"] = args.max_retries

            run_results.append(result)

            if result["status"] == "ok":
                print(
                    f"> OK [{index}] {result['course_name']} (intentos: {result['attempts']})"
                )
            else:
                print(
                    f"> ERROR [{index}] {result['course_name']}: {result['error']} "
                    f"(intentos: {result['attempts']})"
                )

        summary = {
            "generated_at": datetime.now().isoformat(),
            "output_root": output_root,
            "total_courses": total_courses,
            "indices_executed": indices_to_run,
            "successful": sum(1 for r in run_results if r["status"] == "ok"),
            "failed": sum(1 for r in run_results if r["status"] != "ok"),
            "results": run_results,
        }

        summary_path = os.path.join(output_root, "run_summary.json")
        with open(summary_path, "w", encoding="utf-8") as file:
            json.dump(summary, file, ensure_ascii=False, indent=2)

        print(f"\n> Resumen guardado en: {summary_path}")
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    main()
