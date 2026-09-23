from .models import Panel



class ReadingOrderResolver:


    def __init__(
        self,
        direction="ltr"
    ):

        self.direction=direction



    def resolve(
        self,
        panels
    ):


        if not panels:
            return []


        rows=[]


        for panel in sorted(
            panels,
            key=lambda p:
            p.bbox.y1
        ):


            placed=False


            cy = (
                panel.bbox.y1 +
                panel.bbox.y2
            ) / 2



            for row in rows:


                row_center=sum(
                    (
                    p.bbox.y1+
                    p.bbox.y2
                    )/2
                    for p in row
                ) / len(row)



                tolerance=max(
                    panel.height,
                    50
                ) * 0.5



                if abs(
                    cy-row_center
                ) < tolerance:


                    row.append(panel)

                    placed=True

                    break



            if not placed:

                rows.append(
                    [panel]
                )



        rows.sort(
            key=lambda row:
            min(
                p.bbox.y1
                for p in row
            )
        )


        ordered=[]


        for row in rows:


            row.sort(

                key=lambda p:
                p.bbox.x1,

                reverse=
                self.direction=="rtl"

            )


            ordered.extend(row)


        return ordered