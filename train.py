from ultralytics import YOLO

def main():
    model = YOLO(r"model/weights/best.pt")
    model.train(
        data="dataset/data.yaml",
        epochs=200,
        imgsz=1280,        
        batch=4,
        workers=2,
        device=0,
        cache=False,
        project="Bakalarka_Potholes",
        name="model",
        plots=True
    )

if __name__ == '__main__':
    main()