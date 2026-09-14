import json
from datetime import datetime
from pathlib import Path

import cv2


from .detector import ComicPanelDetector
from .coverage import CoverageAnalyzer
from .reading_order import ReadingOrderResolver

from .utils import discover_images



class Pipeline:


    def __init__(
        self,
        config
    ):


        self.config=config


        self.detector=ComicPanelDetector(

            config.model_path,

            config.confidence_threshold,

            config.iou_threshold,

            config.device

        )


        self.coverage=CoverageAnalyzer(

            config.missing_panel_threshold

        )


        self.reader=ReadingOrderResolver(

            config.reading_direction

        )



    def run(self):


        images=discover_images(

            self.config.input_directory

        )


        pages=[]

        total_panels=0



        for index,image_path in enumerate(images,1):


            print(
                f"[{index}/{len(images)}] {image_path.name}"
            )


            page={

                "page_number":index,

                "filename":image_path.name,

                "panels":[]

            }



            img=cv2.imread(
                str(image_path)
            )


            if img is None:

                page["error"]="Cannot read image"

                pages.append(page)

                continue



            h,w=img.shape[:2]



            try:


                panels=self.detector.detect(

                    img,

                    w,

                    h

                )


                ordered=self.reader.resolve(
                    panels
                )



                output_panels=[]


                for i,p in enumerate(
                    ordered,
                    1
                ):

                    p.id=f"{index}-{i}"

                    p.order=i


                    output_panels.append({

                        "id":p.id,

                        "order":i,

                        "bbox":{

                            "x1":p.bbox.x1,

                            "y1":p.bbox.y1,

                            "x2":p.bbox.x2,

                            "y2":p.bbox.y2

                        },


                        "width":p.width,

                        "height":p.height,

                        "area":p.area,

                        "area_ratio":p.area_ratio,

                        "confidence":p.confidence,

                        "class_id":p.class_id,

                        "class_name":p.class_name,

                        "source":p.source

                    })


                cov=self.coverage.analyze(

                    ordered,

                    w,

                    h

                )



                page.update({

                    "width":w,

                    "height":h,

                    "coverage":{

                        "covered_ratio":
                        cov.covered_ratio,

                        "uncovered_ratio":
                        cov.uncovered_ratio

                    },

                    "panels":
                    output_panels

                })



                total_panels += len(output_panels)



                print(
                    "Detected panels:",
                    len(output_panels)
                )


            except Exception as e:


                page["error"]=str(e)



            pages.append(page)



        output={


            "version":"1.0",


            "processing_time":
            datetime.now().isoformat(),


            "model_path":
            self.config.model_path,


            "reading_direction":
            self.config.reading_direction,


            "settings":{

                "confidence_threshold":
                self.config.confidence_threshold,

                "iou_threshold":
                self.config.iou_threshold,

                "missing_panel_threshold":
                self.config.missing_panel_threshold

            },


            "total_pages":
            len(pages),


            "total_panels":
            total_panels,


            "pages":pages

        }


        Path(
            self.config.output_file
        ).write_text(

            json.dumps(
                output,
                indent=4,
                ensure_ascii=False
            ),

            encoding="utf-8"

        )


        print("Finished.")