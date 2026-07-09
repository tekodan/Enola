"""Export module for data export to CSV and JSON."""

import csv
import json
from datetime import datetime
from pathlib import Path

from src.storage.database import Database


class ExportManager:
    """Manager for exporting data to various formats."""

    def __init__(self, database: Database, export_dir: str = "data/exports"):
        """Initialize export manager.

        Args:
            database: Database instance
            export_dir: Directory for export files
        """
        self.database = database
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_to_csv(
        self,
        output_filename: str | None = None,
        include_posts: bool = True,
        include_comments: bool = True,
        include_analysis: bool = True,
    ) -> str:
        """Export data to CSV file.

        Args:
            output_filename: Optional output filename (default: export_YYYYMMDD_HHMMSS.csv)
            include_posts: Include posts in export
            include_comments: Include comments in export
            include_analysis: Include analysis results in export

        Returns:
            Path to the exported file
        """
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"export_{timestamp}.csv"

        output_path = self.export_dir / output_filename

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Posts section
            if include_posts:
                writer.writerow(["=== POSTS ==="])
                writer.writerow(
                    [
                        "ID",
                        "Text",
                        "Author",
                        "Date",
                        "Likes",
                        "Comments",
                        "Shares",
                        "URL",
                        "Page ID",
                    ]
                )

                posts = self.database.get_posts(limit=10000)
                for post in posts:
                    writer.writerow(
                        [
                            post.get("id", ""),
                            post.get("text", "")[:500],  # Limit text length
                            post.get("author", ""),
                            post.get("date", ""),
                            post.get("likes", 0),
                            post.get("comments_count", 0),
                            post.get("shares", 0),
                            post.get("url", ""),
                            post.get("page_id", ""),
                        ]
                    )
                writer.writerow([])  # Empty row separator

            # Comments section
            if include_comments:
                writer.writerow(["=== COMMENTS ==="])
                writer.writerow(["ID", "Text", "Author", "Date", "Likes", "Post ID", "Parent ID"])

                # Get all posts first to iterate comments
                posts = self.database.get_posts(limit=10000)
                for post in posts:
                    comments = self.database.get_comments(post["id"], limit=10000)
                    for comment in comments:
                        writer.writerow(
                            [
                                comment.get("id", ""),
                                comment.get("text", "")[:500],
                                comment.get("author", ""),
                                comment.get("date", ""),
                                comment.get("likes", 0),
                                comment.get("post_id", ""),
                                comment.get("parent_id", ""),
                            ]
                        )
                writer.writerow([])

            # Analysis results section
            if include_analysis:
                writer.writerow(["=== ANALYSIS RESULTS ==="])
                writer.writerow(
                    [
                        "ID",
                        "Content Type",
                        "Content ID",
                        "Violencia",
                        "Categoria (primaria)",
                        "Dimension (primaria)",
                        "Codigo",
                        "Severidad (primaria)",
                        "Confianza",
                        "Justificacion (primaria)",
                        "N° etiquetas",
                    ]
                )

                results = self.database.get_analysis_results()
                for result in results:
                    labels = result.get("labels") or []
                    writer.writerow(
                        [
                            result.get("id", ""),
                            result.get("content_type", ""),
                            result.get("content_id", ""),
                            result.get("tiene_violencia", ""),
                            result.get("categoria", ""),
                            result.get("dimension", "") or "",
                            result.get("codigo", "") or "",
                            result.get("severidad", ""),
                            result.get("confianza", "") or "",
                            result.get("justificacion", "")[:500],
                            len(labels),
                        ]
                    )

                # --- Multi-label detail ---
                writer.writerow([])
                writer.writerow(["=== ANALYSIS LABELS (multi-etiqueta) ==="])
                writer.writerow(
                    [
                        "Analysis Result ID",
                        "Orden",
                        "Categoria",
                        "Dimension",
                        "Severidad",
                        "Confianza",
                        "Score Ajuste",
                        "Falso Positivo Probable",
                        "Regla Disparada",
                        "Marcadores Detectados",
                        "Justificacion",
                        "Evidencia",
                    ]
                )
                for result in results:
                    for lbl in result.get("labels") or []:
                        writer.writerow(
                            [
                                result.get("id", ""),
                                lbl.get("orden", ""),
                                lbl.get("categoria", ""),
                                lbl.get("dimension", "") or "",
                                lbl.get("severidad", ""),
                                lbl.get("confianza", "") or "",
                                lbl.get("score_ajuste", "") or "",
                                lbl.get("es_falso_positivo_probable", "false"),
                                lbl.get("regla_disparada", "") or "",
                                "|".join(lbl.get("marcadores_detectados") or []),
                                (lbl.get("justificacion", "") or "")[:500],
                                (lbl.get("evidencia", "") or "")[:500],
                            ]
                        )

        return str(output_path)

    def export_to_json(
        self,
        output_filename: str | None = None,
        include_posts: bool = True,
        include_comments: bool = True,
        include_analysis: bool = True,
        include_stats: bool = True,
    ) -> str:
        """Export data to JSON file.

        Args:
            output_filename: Optional output filename
            include_posts: Include posts in export
            include_comments: Include comments in export
            include_analysis: Include analysis results in export
            include_stats: Include statistics

        Returns:
            Path to the exported file
        """
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"export_{timestamp}.json"

        output_path = self.export_dir / output_filename

        data = {
            "exported_at": datetime.now().isoformat(),
            "stats": self.database.get_stats() if include_stats else None,
            "posts": None,
            "comments": None,
            "analysis_results": None,
            "seed_pages": None,
        }

        if include_posts:
            data["posts"] = self.database.get_posts(limit=10000)

        if include_comments:
            # Get comments grouped by post
            comments_by_post = {}
            posts = self.database.get_posts(limit=10000)
            for post in posts:
                post_id = post["id"]
                comments_by_post[post_id] = self.database.get_comments(post_id, limit=10000)
            data["comments"] = comments_by_post

        if include_analysis:
            data["analysis_results"] = self.database.get_analysis_results()

        data["seed_pages"] = self.database.get_seed_pages()

        if include_analysis and data.get("analysis_results"):
            # Inject the corrected-label lists per feedback row too.
            data["analysis_feedback"] = self.database.list_feedback()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(output_path)

    def export_violence_report(
        self,
        output_filename: str | None = None,
    ) -> str:
        """Export violence detection report.

        Args:
            output_filename: Optional output filename

        Returns:
            Path to the exported file
        """
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"violence_report_{timestamp}.json"

        output_path = self.export_dir / output_filename

        # Get all analysis results with violence
        results = self.database.get_analysis_results()
        violence_results = [r for r in results if r.get("tiene_violencia") == "true"]

        # Group by category
        by_type: dict[str, list[dict]] = {}
        for result in violence_results:
            tipo = result.get("categoria", "unknown")
            if tipo not in by_type:
                by_type[tipo] = []
            by_type[tipo].append(result)

        # Group by severity
        by_severity = {}
        for result in violence_results:
            severity = result.get("severidad", "unknown")
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(result)

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_violence_detected": len(violence_results),
                "by_type": {tipo: len(items) for tipo, items in by_type.items()},
                "by_severity": {sev: len(items) for sev, items in by_severity.items()},
            },
            "by_type": by_type,
            "by_severity": by_severity,
            "all_results": violence_results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return str(output_path)

    def get_export_files(self) -> list[dict]:
        """Get list of export files with metadata.

        Returns:
            List of dictionaries with file info
        """
        files = []
        for file_path in self.export_dir.glob("*"):
            if file_path.is_file() and not file_path.suffix == ".db":
                stat = file_path.stat()
                files.append(
                    {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )
        return sorted(files, key=lambda x: x["modified"], reverse=True)
