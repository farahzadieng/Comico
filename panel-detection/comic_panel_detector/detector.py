from ultralytics import YOLO

from .models import (
    Panel,
    BoundingBox
)

from .utils import validate_bbox



class ComicPanelDetector:


    def __init__(
        self,
        model_path,
        confidence,
        iou,
        device="auto"
    ):

        self.model = YOLO(model_path)

        self.confidence = confidence

        self.iou = iou

        self.device = (
            None
            if device=="auto"
            else device
        )



    def detect(
        self,
        image,
        image_width,
        image_height
    ):


        results = self.model.predict(

            image,

            conf=self.confidence,

            iou=self.iou,

            device=self.device,

            verbose=False

        )


        panels=[]


        for result in results:


            boxes=result.boxes


            for box in boxes:


                coords = box.xyxy[0].tolist()


                bbox = validate_bbox(

                    *coords,

                    image_width,

                    image_height
                )


                if bbox is None:
                    continue


                x1,y1,x2,y2=bbox


                cls=int(
                    box.cls[0]
                )


                conf=float(
                    box.conf[0]
                )


                name = (
                    result.names.get(
                        cls,
                        str(cls)
                    )
                )


                panels.append(

                    Panel(

                        id=None,

                        order=0,

                        bbox=BoundingBox(
                            x1,
                            y1,
                            x2,
                            y2
                        ),

                        width=x2-x1,

                        height=y2-y1,

                        area=(x2-x1)*(y2-y1),

                        area_ratio=
                        (
                            (x2-x1)*(y2-y1)
                            /
                            (image_width*image_height)
                        ),

                        confidence=conf,

                        class_id=cls,

                        class_name=name

                    )
                )


        return panels