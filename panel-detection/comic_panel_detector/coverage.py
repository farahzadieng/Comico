import cv2
import numpy as np

from .models import (
    Panel,
    CoverageInfo
)


class CoverageAnalyzer:


    def __init__(
        self,
        missing_threshold=0.10
    ):

        self.missing_threshold = missing_threshold



    def analyze(
        self,
        panels,
        width,
        height
    ):

        mask = np.zeros(
            (height,width),
            dtype=np.uint8
        )


        for panel in panels:

            b = panel.bbox

            cv2.rectangle(
                mask,
                (b.x1,b.y1),
                (b.x2,b.y2),
                255,
                -1
            )


        covered_area = int(
            np.count_nonzero(mask)
        )


        image_area = width * height


        covered_ratio = (
            covered_area /
            image_area
        )


        uncovered_ratio = (
            1 -
            covered_ratio
        )


        return CoverageInfo(

            covered_ratio=covered_ratio,

            uncovered_ratio=uncovered_ratio,

            covered_area=covered_area,

            uncovered_area=
            image_area-covered_area

        )



    def find_missing_regions(
        self,
        panels,
        width,
        height
    ):


        mask = np.zeros(
            (height,width),
            dtype=np.uint8
        )


        for panel in panels:

            b=panel.bbox

            cv2.rectangle(
                mask,
                (b.x1,b.y1),
                (b.x2,b.y2),
                255,
                -1
            )


        inverted=cv2.bitwise_not(mask)


        contours,_ = cv2.findContours(

            inverted,

            cv2.RETR_EXTERNAL,

            cv2.CHAIN_APPROX_SIMPLE

        )


        candidates=[]


        for c in contours:


            x,y,w,h = cv2.boundingRect(c)


            area=w*h


            ratio = (
                area /
                (width*height)
            )


            if ratio < self.missing_threshold:
                continue


            aspect=w/h


            candidates.append({

                "bbox":[
                    x,
                    y,
                    x+w,
                    y+h
                ],

                "area":area,

                "area_ratio":ratio,

                "width":w,

                "height":h,

                "aspect_ratio":aspect

            })


        return candidates