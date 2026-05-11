import os
import cv2
import pandas as pd
import folium
from ultralytics import YOLO

def main():
    model_path = "model/weights/best.pt"
    input_folder = "Data"
    output_folder = "Output"
    
    min_confidence = 0.278
    min_frame_life = 10
    frame_buffer = 60
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    print("Scanning folder and pairing videos with GPS logs...")
    drive_list = []
    all_files = os.listdir(input_folder)
    videos = [f for f in all_files if f.lower().endswith(".mp4")]
    
    for v_file in videos:
        base_name = os.path.splitext(v_file)[0]
        csv_file = base_name + ".csv"
        v_path = os.path.join(input_folder, v_file)
        c_path = os.path.join(input_folder, csv_file)
        
        if os.path.exists(c_path):
            drive_list.append({"video": v_path, "csv": c_path, "name": base_name})
            print(f"Found pair: {v_file} + {csv_file}")
        else:
            print(f"Missing GPS log for {v_file}, skipping.")
            
    if not drive_list:
        print("No paired data found. Check your file names!")
        return
        
    model = YOLO(model_path)
    all_potholes = []
    global_id = 1

    for drive in drive_list:
        print(f"\nProcessing: {drive['name']}")
        try:
            gps_df = pd.read_csv(drive['csv'])
        except:
            print(f"Error reading CSV: {drive['csv']}")
            continue
            
        cap = cv2.VideoCapture(drive['video'])
        fps = cap.get(cv2.CAP_PROP_FPS)
        active_objects = {}
        frame_number = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: 
                break
                
            frame_number += 1
            current_cts = (frame_number / fps) * 1000
            
            results = model.track(frame, persist=True, imgsz=1280, conf=0.55, verbose=False)
            
            if results[0].boxes.id is not None:
                ids = results[0].boxes.id.cpu().numpy()
                boxes = results[0].boxes.xyxy.cpu().numpy()
                confs = results[0].boxes.conf.cpu().numpy()
                
                for b, tid, c in zip(boxes, ids, confs):
                    tid = int(tid)
                    if tid not in active_objects:
                        active_objects[tid] = {
                            "start": frame_number, "last": frame_number, "cts": current_cts,
                            "max_c": c, "box": b, "img": frame.copy()
                        }
                    else:
                        active_objects[tid]["last"] = frame_number
                        if c > active_objects[tid]["max_c"]:
                            active_objects[tid].update({"max_c": c, "box": b, "img": frame.copy()})
                            
            to_save = [oid for oid, d in active_objects.items() if (frame_number - d["last"]) > frame_buffer]
            
            for oid in to_save:
                data = active_objects.pop(oid)
                life = data["last"] - data["start"]
                
                if life >= min_frame_life and data["max_c"] >= min_confidence:
                    idx = (gps_df['cts'] - data["cts"]).abs().idxmin()
                    row = gps_df.iloc[idx]
                    lat, lon = row['GPS (Lat.) [deg]'], row['GPS (Long.) [deg]']
                    x1, y1, x2, y2 = map(int, data["box"])
                    
                    viz_img = data["img"].copy()
                    cv2.rectangle(viz_img, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    text = f"Pothole #{global_id} ({data['max_c']*100:.1f}%)"
                    cv2.putText(viz_img, text, (x1, max(y1-10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    
                    photo_name = f"pothole_{global_id}_{drive['name']}.jpg"
                    cv2.imwrite(os.path.join(output_folder, photo_name), viz_img)
                    
                    all_potholes.append({
                        "ID": global_id, "Video": drive['name'], "Lat": lat, "Lon": lon,
                        "Conf": data["max_c"], "Photo": photo_name
                    })
                    print(f"Saved pothole #{global_id} (Lat: {lat})")
                    global_id += 1

        cap.release()
        
    if all_potholes:
        print(f"\nGenerating results for {len(all_potholes)} potholes...")
        m = folium.Map(location=[all_potholes[0]["Lat"], all_potholes[0]["Lon"]], 
                       zoom_start=14, tiles='CartoDB positron')
                       
        for v in all_potholes:
            popup_text = f"Pothole #{v['ID']}<br>Video: {v['Video']}<br>Confidence: {v['Conf']*100:.1f}%"
            folium.Marker([v["Lat"], v["Lon"]], popup=popup_text, icon=folium.Icon(color="red")).add_to(m)
            
        m.save(os.path.join(output_folder, "Map_Output.html"))
        pd.DataFrame(all_potholes).to_csv(os.path.join(output_folder, "Potholes.csv"), index=False)
        print(f"Everything completed! Outputs are in: {output_folder}")
    else:
        print("\nNo potholes found meeting the criteria.")

if __name__ == "__main__":
    main()

