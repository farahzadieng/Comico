import argparse


from comic_panel_detector.config import load_config
from comic_panel_detector.pipeline import Pipeline



def main():

    parser=argparse.ArgumentParser()


    parser.add_argument(

        "--config",

        required=True

    )


    args=parser.parse_args()



    config=load_config(
        args.config
    )


    pipeline=Pipeline(
        config
    )


    pipeline.run()



if __name__=="__main__":

    main()