"""CLI entrypoint with mock support: python -m src.pipeline_mock [seed_pages_file] --mock"""

import argparse
import logging
import sys

try:
    from src.scraper.mock_facebook import MockFacebookScraper

    MOCK_AVAILABLE = True
except ImportError:
    MOCK_AVAILABLE = False
    from src.scraper.facebook import FacebookScraper

from src.pipeline.orchestrator import PipelineOrchestrator, load_seed_pages

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de detección de violencia en Facebook")
    parser.add_argument("seed_file", nargs="?", help="Archivo con URLs seed (opcional)")
    parser.add_argument(
        "--mock", action="store_true", help="Usar datos mock en lugar de Facebook real"
    )

    args = parser.parse_args()

    seeds = load_seed_pages(args.seed_file)

    if not seeds:
        print("No se encontraron páginas seed.")
        sys.exit(1)

    print(f"Ejecutando pipeline con {len(seeds)} páginas seed:")
    for s in seeds:
        print(f"  • {s}")

    # Choose scraper
    if args.mock and MOCK_AVAILABLE:
        print("⚠️ Usando MOCK SCRAPER (datos de prueba)")
        scraper = MockFacebookScraper(max_posts=10, max_comments=20, use_mock_data=True)
    elif args.mock and not MOCK_AVAILABLE:
        print("⚠️ Mock scraper no disponible, usando scraper real")
        scraper = FacebookScraper(max_posts=10, max_comments=20)
    else:
        print("Usando scraper real de Facebook")
        scraper = FacebookScraper(max_posts=10, max_comments=20)

    orchestrator = PipelineOrchestrator(scraper=scraper)
    result = orchestrator.run_full_pipeline(seeds)

    print(f"\nPipeline completado: éxito={result.success}")
    print(f"Páginas procesadas: {result.stats.pages_scraped}")
    print(f"Posts encontrados: {result.stats.posts_found}")
    print(f"Comentarios encontrados: {result.stats.comments_found}")
    print(f"Violencia detectada: {result.stats.violence_detected_posts}")
    print(f"Nuevas páginas descubiertas: {result.stats.new_pages_discovered}")

    if result.errors:
        print(f"\nErrores encontrados ({len(result.errors)}):")
        for error in result.errors[:3]:  # Show first 3 errors
            print(f"  • {error}")
        if len(result.errors) > 3:
            print(f"  ... y {len(result.errors) - 3} más")


if __name__ == "__main__":
    main()
