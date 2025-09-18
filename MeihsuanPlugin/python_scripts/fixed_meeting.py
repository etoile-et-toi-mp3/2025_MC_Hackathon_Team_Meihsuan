import argparse, time, logging, base64, sys
from dataclasses import dataclass
from typing import List, Optional
import cv2, numpy as np, mediapipe as mp

# OBS v5 client
from obsws_python import ReqClient
import pygetwindow as gw
import keyboard

# ------- meeting hotkeys -------
def _focus(keys, timeout=1.5):
    t0=time.time()
    while time.time()-t0<timeout:
        for title in gw.getAllTitles():
            if any(k.lower() in title.lower() for k in keys):
                for w in gw.getWindowsWithTitle(title):
                    try:
                        w.activate(); time.sleep(0.2)
                        if w.isActive: return True
                    except: pass
        time.sleep(0.2)
    return False

def meet_toggle(mic=True, cam=True):
    if not _focus(["Meet","Google Chrome","Microsoft Edge"]):
        logging.warning("找不到 Meet 視窗"); return False
    if mic: keyboard.press_and_release("ctrl+d")
    if cam: keyboard.press_and_release("ctrl+e")
    return True

def zoom_toggle(mic=True, cam=True):
    if not _focus(["Zoom Meeting","Zoom"]):
        logging.warning("找不到 Zoom 視窗"); return False
    if mic: keyboard.press_and_release("alt+a")
    if cam: keyboard.press_and_release("alt+v")
    return True

# ------- face detection -------
@dataclass
class Face:
    score: float
    area: float

class FaceDet:
    def __init__(self, model_sel=0, min_conf=0.5):
        mpfd=mp.solutions.face_detection
        self.det=mpfd.FaceDetection(model_sel, min_conf)
    
    def detect(self, bgr) -> List[Face]:
        rgb=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        res=self.det.process(rgb)
        out=[]
        if res and res.detections:
            for d in res.detections:
                s=float(d.score[0]) if d.score else 0.0
                rb=d.location_data.relative_bounding_box
                out.append(Face(s, max(rb.width,0)*max(rb.height,0)))
        return out

# ------- 兼容的 OBS 資料存取函數 -------
def safe_get_scenes(client):
    """安全地取得場景列表"""
    try:
        response = client.get_scene_list()
        
        # 嘗試不同的存取方式
        scenes_data = None
        if hasattr(response, 'scenes'):
            scenes_data = response.scenes
        elif isinstance(response, dict) and 'scenes' in response:
            scenes_data = response['scenes']
        else:
            logging.error(f"未知的場景回應格式: {type(response)}")
            return []
        
        # 提取場景名稱
        scene_names = []
        for scene in scenes_data:
            if hasattr(scene, 'sceneName'):
                scene_names.append(scene.sceneName)
            elif isinstance(scene, dict) and 'sceneName' in scene:
                scene_names.append(scene['sceneName'])
            else:
                logging.warning(f"未知的場景項目格式: {type(scene)}")
                
        return scene_names
        
    except Exception as e:
        logging.error(f"取得場景列表失敗: {e}")
        return []

def safe_get_inputs(client):
    """安全地取得輸入來源列表（OBS v5 API 使用 get_input_list）"""
    try:
        response = client.get_input_list()
        
        # 嘗試不同的存取方式
        inputs_data = None
        if hasattr(response, 'inputs'):
            inputs_data = response.inputs
        elif isinstance(response, dict) and 'inputs' in response:
            inputs_data = response['inputs']
        else:
            logging.error(f"未知的輸入來源回應格式: {type(response)}")
            return []
        
        # 提取輸入來源名稱
        input_names = []
        for inp in inputs_data:
            if hasattr(inp, 'inputName'):
                input_names.append(inp.inputName)
            elif isinstance(inp, dict) and 'inputName' in inp:
                input_names.append(inp['inputName'])
            else:
                logging.warning(f"未知的輸入來源項目格式: {type(inp)}")
                
        return input_names
        
    except Exception as e:
        logging.error(f"取得輸入來源列表失敗: {e}")
        return []

def obs_get_source_frame(client: ReqClient, source_name: str, w: int, h: int) -> Optional[np.ndarray]:
    """安全地取得來源截圖 - 使用原始 API 調用"""
    try:
        # 使用原始 API 調用避免 obsws-python 的方法問題
        response = client.send("GetSourceScreenshot", {
            "sourceName": source_name,
            "imageFormat": "png",
            "imageWidth": w,
            "imageHeight": h
        }, raw=True)
        
        if not isinstance(response, dict):
            logging.error(f"截圖回應格式異常: {type(response)}")
            return None
            
        image_data = response.get("imageData")
        if not image_data: 
            logging.error("圖像資料為空")
            return None
            
        # 處理 base64 資料
        if "," in image_data: 
            image_data = image_data.split(",", 1)[1]
            
        img = cv2.imdecode(np.frombuffer(base64.b64decode(image_data), np.uint8),
                           cv2.IMREAD_COLOR)
        return img
        
    except Exception as e:
        logging.error("GetSourceScreenshot 失敗：%s", e)
        return None

def main():
    ap=argparse.ArgumentParser("Presence via OBS v5")
    ap.add_argument("--mode", choices=["meet","zoom"], required=True)
    ap.add_argument("--obs-host", default="127.0.0.1")
    ap.add_argument("--obs-port", type=int, default=4455)
    ap.add_argument("--obs-password", required=True)
    ap.add_argument("--camera-source-name", required=True)
    ap.add_argument("--live-scene", default="Live")
    ap.add_argument("--brb-scene", default="BRB")
    ap.add_argument("--shot-width", type=int, default=640)
    ap.add_argument("--shot-height", type=int, default=360)
    ap.add_argument("--poll-ms", type=int, default=200)
    ap.add_argument("--conf-in", type=float, default=0.55)
    ap.add_argument("--conf-out", type=float, default=0.65)
    ap.add_argument("--area-in", type=float, default=0.010)
    ap.add_argument("--area-out", type=float, default=0.007)
    ap.add_argument("--debounce", type=int, default=8)
    ap.add_argument("--return-warmup", type=int, default=8)
    ap.add_argument("--cooldown-sec", type=float, default=2.0)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--log-level", default="INFO",
                    choices=["DEBUG","INFO","WARNING","ERROR"])
    ap.add_argument("--logfile", default=None)
    args=ap.parse_args()

    handlers=[logging.StreamHandler()]
    if args.logfile: handlers.append(logging.FileHandler(args.logfile,encoding="utf-8"))
    logging.basicConfig(level=getattr(logging,args.log_level),
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        handlers=handlers)

    toggle = meet_toggle if args.mode=="meet" else zoom_toggle

    # connect OBS v5
    try:
        client = ReqClient(host=args.obs_host, port=args.obs_port,
                           password=args.obs_password, timeout=3)
        logging.info("已連線 OBS WebSocket v5")
    except Exception as e:
        logging.error(f"OBS 連接失敗: {e}")
        return

    # sanity check: 來源與場景是否存在 - 使用安全存取函數
    scenes = safe_get_scenes(client)
    if args.live_scene not in scenes or args.brb_scene not in scenes:
        logging.error("找不到場景 Live/BRB。現有場景：%s", scenes)
        return
        
    inputs = safe_get_inputs(client)
    if args.camera_source_name not in inputs:
        logging.error("找不到輸入來源：%s。現有輸入來源：%s", args.camera_source_name, inputs)
        return

    det = FaceDet(min_conf=min(args.conf_in,args.conf_out))
    state="PRESENT"; hist=[]; warm=0; last=time.time()

    def single_present(faces: List[Face]) -> bool:
        conf = args.conf_in if state=="ABSENT" else args.conf_out
        area = args.area_in if state=="ABSENT" else args.area_out
        return any(f.score>=conf and f.area>=area for f in faces)

    logging.info("開始偵測：來源=%s  Live=%s  BRB=%s",
                 args.camera_source_name, args.live_scene, args.brb_scene)

    try:
        while True:
            t0=time.time()
            frame = obs_get_source_frame(client, args.camera_source_name,
                                         args.shot_width, args.shot_height)
            if frame is None:
                logging.warning("抓不到來源畫面（請檢查來源名稱/設定）")
                time.sleep(0.3); continue

            faces = det.detect(frame)
            present = single_present(faces)

            hist.append(1 if present else 0)
            if len(hist)>args.debounce: hist.pop(0)

            switched=None
            if time.time()-last>=args.cooldown_sec and len(hist)==args.debounce:
                if state=="PRESENT" and sum(hist)==0:
                    state="ABSENT"; switched="ABSENT"
                elif state=="ABSENT" and sum(hist)==args.debounce:
                    # 用 warmup 控制回來
                    pass

            if switched=="ABSENT":
                logging.info("STATE_CHANGED: ABSENT")
                try:
                    client.set_current_program_scene(args.brb_scene)
                    toggle(mic=True, cam=True)
                except Exception as e:
                    logging.error(f"切換場景/控制會議失敗: {e}")
                last=time.time(); hist.clear(); warm=0

            if state=="ABSENT":
                warm = warm+1 if present else 0
                if warm>=args.return_warmup and time.time()-last>=args.cooldown_sec:
                    logging.info("STATE_CHANGED: PRESENT（偵測你回來）")
                    try:
                        client.set_current_program_scene(args.live_scene)
                        toggle(mic=True, cam=True)
                    except Exception as e:
                        logging.error(f"切換場景/控制會議失敗: {e}")
                    state="PRESENT"; last=time.time(); hist.clear(); warm=0

            if args.show:
                vis=frame.copy()
                h_img, w_img = vis.shape[:2]
                
                # 狀態顏色和文字
                if state == "PRESENT":
                    color = (0, 255, 0)  # 綠色
                    status_text = "在場 (PRESENT)"
                else:
                    color = (0, 0, 255)  # 紅色  
                    status_text = "離開 (ABSENT)"
                
                # 詳細資訊
                info_lines = [
                    f"狀態: {status_text}",
                    f"偵測到人臉: {len(faces)}",
                    f"最高信心度: {max([f.score for f in faces], default=0.0):.2f}",
                    f"最大面積: {max([f.area for f in faces], default=0.0):.3f}",
                    f"暖身計數: {warm}/{args.return_warmup}",
                    f"歷史緩衝: {sum(hist)}/{len(hist)}"
                ]
                
                # 繪製資訊
                y_offset = 25
                for i, line in enumerate(info_lines):
                    cv2.putText(vis, line, (10, y_offset + i*22), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                # 狀態指示器（右上角大圓點）
                cv2.circle(vis, (w_img - 30, 30), 15, color, -1)
                
                cv2.imshow("人臉偵測狀態", vis)
                if cv2.waitKey(1) & 0xFF in (ord('q'), 27): 
                    break

            # 控制頻率
            dt=time.time()-t0
            sleep=max(0.0, args.poll_ms/1000.0 - dt)
            if sleep>0: time.sleep(sleep)
            
    except KeyboardInterrupt:
        logging.info("使用者中斷")
    except Exception as e:
        logging.error(f"執行過程出錯: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cv2.destroyAllWindows()
        logging.info("已停止。")

if __name__=="__main__":
    main()
