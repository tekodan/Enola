"""CLI entrypoint: python -m src.pipeline [seed_pages_file]"""

import logging
import sys

from src.scraper.facebook import FacebookScraper

from .orchestrator import PipelineOrchestrator, load_seed_pages

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    seeds = load_seed_pages(path)

    if not seeds:
        print("No se encontraron páginas seed.")
        sys.exit(1)

    print(f"Ejecutando pipeline con {len(seeds)} páginas seed:")
    for s in seeds:
        print(f"  • {s}")

    scraper = FacebookScraper(max_posts=10, max_comments=20)
    orchestrator = PipelineOrchestrator(scraper=scraper)
    result = orchestrator.run_full_pipeline(seeds)

    print(f"\nPipeline completado: éxito={result.success}")
    print(f"Páginas procesadas: {result.stats.pages_scraped}")
    print(f"Posts encontrados: {result.stats.posts_found}")
    print(f"Violencia detectada: {result.stats.violence_detected_posts}")
    print(f"Nuevas páginas descubiertas: {result.stats.new_pages_discovered}")


if __name__ == "__main__":
    main()
