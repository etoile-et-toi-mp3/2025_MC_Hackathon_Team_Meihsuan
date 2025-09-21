# Meeting Auto Guard

自動偵測人臉，離開座位時切換到 BRB 場景，回到座位時恢復 Live 場景。

## 使用目的

解決會議中臨時離開座位的問題。當你離開攝影機前時，系統自動切換到 "Be Right Back" 畫面並靜音麥克風；回到座位時自動恢復正常。

關鍵是使用 OBS Virtual Camera，讓系統能在關閉鏡頭後仍持續偵測人臉，實現真正的自動恢復功能。

## 設定步驟

### OBS 設定
1. 建立場景 `Live` 和 `BRB`
2. 在 Live 場景新增攝影機來源，命名為 `Video Capture Device`
3. Tools → WebSocket Server Settings，啟用並設定密碼
4. 啟動 Virtual Camera

### 會議軟體設定
將攝影機改為 `OBS Virtual Camera`：
- Google Meet: 設定 → Camera → OBS Virtual Camera
- Zoom: 攝影機選項 → Choose Camera → OBS Virtual Camera
