import json
from datetime import datetime
from pathlib import Path

import cv2

from .coverage import CoverageAnalyzer
from .detector import ComicPanelDetector
from .reading_order import ReadingOrderResolver
from .utils import discover_comic_directories, discover_images


class Pipeline:
    def __init__(self, config):
        self.config = config

        self.detector = ComicPanelDetector(
            config.model_path,
            config.confidence_threshold,
            config.iou_threshold,
            config.device
        )

        self.coverage = CoverageAnalyzer(
            config.missing_panel_threshold
        )

        self.reader = ReadingOrderResolver(
            config.reading_direction
        )

    def run(self):
        if self.config.recursive:
            self._run_recursive()
        else:
            self._run_single_directory()

    def _run_single_directory(self):
        input_directory = Path(self.config.input_directory)
        output_file = Path(self.config.output_file)

        print("Comic Panel Detection")
        print(f"Input: {input_directory}")
        print("Mode: single directory")

        stats = self._process_collection(
            input_directory=input_directory,
            output_file=output_file,
            collection_index=None,
            collection_count=None,
        )

        print("\nFinished.")
        print(f"Pages processed: {stats['pages_processed']}")
        print(f"Pages failed: {stats['pages_failed']}")
        print(f"Total panels: {stats['total_panels']}")
        print(f"Output: {output_file}")

    def _run_recursive(self):
        root = Path(self.config.input_directory)
        collections = discover_comic_directories(root)

        if not collections:
            raise ValueError(
                f"No supported images found under input directory: {root}"
            )

        print("Comic Panel Detection")
        print(f"Input root: {root}")
        print("Mode: recursive")
        print(f"Found {len(collections)} image collection(s).")

        collections_processed = 0
        collections_failed = 0
        pages_processed = 0
        pages_failed = 0
        total_panels = 0

        for collection_index, directory in enumerate(collections, 1):
            output_file = directory / self.config.output_filename

            try:
                stats = self._process_collection(
                    input_directory=directory,
                    output_file=output_file,
                    collection_index=collection_index,
                    collection_count=len(collections),
                )

                collections_processed += 1
                pages_processed += stats["pages_processed"]
                pages_failed += stats["pages_failed"]
                total_panels += stats["total_panels"]

            except Exception as e:
                collections_failed += 1
                print(
                    f"  ERROR: Failed collection '{directory}': {e}"
                )

        print("\nFinished.")
        print(f"Collections processed: {collections_processed}")
        print(f"Collections failed: {collections_failed}")
        print(f"Pages processed: {pages_processed}")
        print(f"Pages failed: {pages_failed}")
        print(f"Total panels: {total_panels}")

    def _process_collection(
        self,
        input_directory: Path,
        output_file: Path,
        collection_index,
        collection_count,
    ):
        images = discover_images(input_directory)

        if not images:
            raise ValueError(
                f"No supported images found in directory: {input_directory}"
            )

        if collection_index is not None:
            print(
                f"\n[Collection {collection_index}/{collection_count}] "
                f"{input_directory}"
            )

        pages = []
        total_panels = 0
        pages_failed = 0

        for index, image_path in enumerate(images, 1):
            print(
                f"  [{index}/{len(images)}] {image_path.name}"
            )

            page = {
                "page_number": index,
                "filename": image_path.name,
                "panels": [],
            }

            img = cv2.imread(str(image_path))

            if img is None:
                page["error"] = "Cannot read image"
                pages.append(page)
                pages_failed += 1
                print("    ERROR: Cannot read image")
                continue

            h, w = img.shape[:2]

            try:
                panels = self.detector.detect(
                    img,
                    w,
                    h
                )

                ordered = self.reader.resolve(panels)

                output_panels = []

                for i, panel in enumerate(ordered, 1):
                    panel.id = f"{index}-{i}"
                    panel.order = i

                    output_panels.append({
                        "id": panel.id,
                        "order": i,
                        "bbox": {
                            "x1": panel.bbox.x1,
                            "y1": panel.bbox.y1,
                            "x2": panel.bbox.x2,
                            "y2": panel.bbox.y2,
                        },
                        "width": panel.width,
                        "height": panel.height,
                        "area": panel.area,
                        "area_ratio": panel.area_ratio,
                        "confidence": panel.confidence,
                        "class_id": panel.class_id,
                        "class_name": panel.class_name,
                        "source": panel.source,
                    })

                cov = self.coverage.analyze(
                    ordered,
                    w,
                    h
                )

                page.update({
                    "width": w,
                    "height": h,
                    "coverage": {
                        "covered_ratio": cov.covered_ratio,
                        "uncovered_ratio": cov.uncovered_ratio,
                    },
                    "panels": output_panels,
                })

                total_panels += len(output_panels)

                print(
                    f"    Detected panels: {len(output_panels)}"
                )
                print(
                    f"    Coverage: {cov.covered_ratio * 100:.1f}%"
                )

            except Exception as e:
                page["width"] = w
                page["height"] = h
                page["error"] = str(e)
                pages_failed += 1
                print(f"    ERROR: {e}")

            finally:
                # Make it explicit that pages are processed sequentially and
                # the image buffer is not retained between iterations.
                del img

            pages.append(page)

        output = {
            "version": "1.0",
            "processing_time": datetime.now().astimezone().isoformat(),
            "input_directory": str(input_directory),
            "model_path": self.config.model_path,
            "reading_direction": self.config.reading_direction,
            "settings": {
                "confidence_threshold": self.config.confidence_threshold,
                "iou_threshold": self.config.iou_threshold,
                "missing_panel_threshold": self.config.missing_panel_threshold,
                "recursive": self.config.recursive,
            },
            "total_pages": len(pages),
            "pages_failed": pages_failed,
            "total_panels": total_panels,
            "pages": pages,
        }

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        output_file.write_text(
            json.dumps(
                output,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        print(f"    Output: {output_file}")

        return {
            "pages_processed": len(pages),
            "pages_failed": pages_failed,
            "total_panels": total_panels,
        }
