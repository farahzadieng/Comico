import gradio as gr
from ultralytics import YOLO
import torch

model_id = "mosesb/best-comic-panel-detection"
model = YOLO("best.pt")

def detect_panels(pil_image, conf_threshold, iou_threshold):
    """
    Takes a PIL image and thresholds, runs YOLOv12 object detection,
    and returns the annotated image with bounding boxes.
    """
    # Run inference on the image with the specified thresholds
    results = model.predict(pil_image, conf=conf_threshold, iou=iou_threshold, verbose=False)
    annotated_image = results[0].plot()

    # Gradio's gr.Image component expects an RGB image. The .plot() method
    # returns a BGR image, so we convert it.
    annotated_image_rgb = annotated_image[..., ::-1]

    return annotated_image_rgb



# --- Gradio Interface ---
title = "YOLOv12 Comic Panel Detection"
description = """
This demo showcases a **YOLOv12 object detection model** that has been fine-tuned to detect panels in comic book pages.
Upload an image of a comic page, and the model will draw bounding boxes around each detected panel. 
This can be a useful first step for downstream tasks like Optical Character Recognition (OCR) or character analysis within comics.
"""

article = f"""
<div style='text-align: center;'>
    <p style='text-align: center'>Model loaded from <a href='https://huggingface.co/{model_id}' target='_blank'>{model_id}</a></p>
    <p style='text-align: center'>For more details on the training process, check out the project repository: <a href='https://github.com/mosesab/YOLOV12-Comic-Panel-Detection/blob/main/comic-boundary-detection.ipynb' target='_blank'>Comic Boundary Detection</a></p>
    <p>If you like this demo, consider leaving a star on the <a href='https://github.com/mosesab/YOLOV12-Comic-Panel-Detection' target='_blank'>Github repo</a> or a like on the <a href='https://huggingface.co/{model_id}' target='_blank'>Hugging Face model</a>. It helps me know people are interested and motivates further development.</p>
</div>
"""

# Define the input components for the Gradio interface
inputs = [
    gr.Image(type="pil", label="Upload Comic Page Image"),
    gr.Slider(
        minimum=0.0,
        maximum=1.0,
        value=0.25, # The default confidence threshold in ultralytics
        step=0.05,
        label="Confidence Threshold",
        info="Filters detections. Only boxes with confidence above this value will be shown."
    ),
    gr.Slider(
        minimum=0.0,
        maximum=1.0,
        value=0.7, # The default IoU threshold in ultralytics
        step=0.05,
        label="IoU Threshold",
        info="Controls merging of overlapping boxes. Higher values allow more overlap."
    )
]

examples = [
    ["aura_farmer_1.jpg", 0.25, 0.7],
    ["aura_farmer_2.jpg", 0.25, 0.7],
    ["aura_farmer_3.jpg", 0.25, 0.7],
    ["aura_farmer_4.jpg", 0.25, 0.7],
]

gr.Interface(
    fn=detect_panels,
    inputs=inputs,
    outputs=gr.Image(type="pil", label="Detected Panels"),
    title=title,
    description=description,
    article=article,
    examples=examples,
    allow_flagging="auto"
).launch()