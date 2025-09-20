using System;
using System.Threading;
using System.Windows.Media.Imaging;

namespace Loupedeck.MeiPlugin
{
    public class PulseEffectCommand : PluginDynamicCommand
    {
        // === 私有成員變數 ===
        private Timer _pulseTimer;
        private int _currentFrameIndex = 0;
        private bool _isPlaying = false;
        private readonly object _lockObject = new object();
        
        // 圖片資源路徑陣列 - 按照官方範例格式
        private readonly string[] _imageResourcePaths;
        private readonly int _intervalMs = 50;  // 50毫秒間隔
        private readonly int _totalFrames = 120; // 總共120幀

        // === 建構函式 - 按照官方範例格式 ===
        public PulseEffectCommand() 
            : base(displayName: "Pulse Effect", description: "自動播放脈衝動畫效果", groupName: "Animation")
        {
            // 按照官方範例：在建構函式中初始化圖片資源路徑
            _imageResourcePaths = new string[_totalFrames];
            
            // 載入所有圖片資源路徑
            LoadImageResourcePaths();
            
            // 自動開始播放脈衝動畫
            StartAutoPlay();
        }

        // === 載入圖片資源路徑 - 按照官方 PluginResources.FindFile() 方式 ===
        private void LoadImageResourcePaths()
        {
            for (int i = 0; i < _totalFrames; i++)
            {
                try
                {
                    // 按照官方文件：使用 PluginResources.FindFile() 找到嵌入資源
                    // 圖片檔案命名：001.png, 002.png, ..., 120.png
                    string fileName = $"{(i + 1):D3}.png";
                    _imageResourcePaths[i] = PluginResources.FindFile(fileName);
                }
                catch (Exception ex)
                {
                    // 如果圖片檔案不存在，設為 null
                    _imageResourcePaths[i] = null;
                    System.Diagnostics.Debug.WriteLine($"找不到圖片檔案: {(i + 1):D3}.png - {ex.Message}");
                }
            }
        }

        // === 自動開始播放 ===
        private void StartAutoPlay()
        {
            // 延遲 500ms 後開始播放，確保系統已完全載入
            var startTimer = new Timer((state) =>
            {
                lock (_lockObject)
                {
                    if (!_isPlaying)
                    {
                        StartPulse();
                    }
                }
            }, null, 500, Timeout.Infinite);
        }

        // === 按鍵處理 - 按照官方範例格式 ===
        protected override void RunCommand(string actionParameter)
        {
            lock (_lockObject)
            {
                if (_isPlaying)
                {
                    // 如果正在播放，則暫停
                    PausePulse();
                }
                else
                {
                    // 如果暫停中，則繼續播放
                    ResumePulse();
                }
            }
            
            // 按照官方文件：狀態改變時必須呼叫 ActionImageChanged
            this.ActionImageChanged();
        }

        // === 開始脈衝動畫 ===
        private void StartPulse()
        {
            _isPlaying = true;
            _currentFrameIndex = 0;
            
            // 立即更新第一幀
            this.ActionImageChanged();
            
            // 建立計時器，每50ms切換下一張圖片
            _pulseTimer = new Timer(UpdatePulseFrame, null, _intervalMs, _intervalMs);
        }

        // === 暫停脈衝動畫 ===
        private void PausePulse()
        {
            _isPlaying = false;
            _pulseTimer?.Dispose();
            _pulseTimer = null;
        }

        // === 恢復脈衝動畫 ===
        private void ResumePulse()
        {
            if (!_isPlaying)
            {
                _isPlaying = true;
                // 從當前位置繼續播放
                _pulseTimer = new Timer(UpdatePulseFrame, null, _intervalMs, _intervalMs);
            }
        }

        // === 更新脈衝幀 - Timer 回調函式 ===
        private void UpdatePulseFrame(object state)
        {
            if (!_isPlaying) return;

            lock (_lockObject)
            {
                // 移動到下一張圖片（循環播放）
                _currentFrameIndex = (_currentFrameIndex + 1) % _totalFrames;
                
                // 按照官方文件：呼叫 ActionImageChanged 通知系統重繪
                this.ActionImageChanged();
            }
        }

        // === 核心顯示函式 - 按照官方 GetCommandImage 格式 ===
        protected override BitmapImage GetCommandImage(string actionParameter, PluginImageSize imageSize)
        {
            if (_isPlaying)
            {
                // 播放模式：顯示當前脈衝幀
                return LoadCurrentPulseFrame(imageSize);
            }
            else
            {
                // 暫停模式：顯示暫停狀態
                return CreatePausedImage(imageSize);
            }
        }

        // === 載入當前脈衝幀 - 按照官方 PluginResources.ReadImage 方式 ===
        private BitmapImage LoadCurrentPulseFrame(PluginImageSize imageSize)
        {
            try
            {
                string resourcePath = _imageResourcePaths[_currentFrameIndex];
                
                if (resourcePath != null)
                {
                    // 按照官方文件：使用 PluginResources.ReadImage 載入嵌入的圖片
                    return PluginResources.ReadImage(resourcePath);
                }
                else
                {
                    // 圖片檔案不存在，使用程式生成的預設脈衝圖片
                    return CreateDefaultPulseImage(_currentFrameIndex, imageSize);
                }
            }
            catch (Exception ex)
            {
                // 載入失敗，顯示錯誤圖片
                System.Diagnostics.Debug.WriteLine($"載入脈衝圖片失敗: {ex.Message}");
                return CreateErrorImage(_currentFrameIndex, imageSize);
            }
        }

        // === 創建暫停狀態圖片 - 按照官方 BitmapBuilder 用法 ===
        private BitmapImage CreatePausedImage(PluginImageSize imageSize)
        {
            using (var bitmapBuilder = new BitmapBuilder(imageSize))
            {
                // 按照官方文件：DrawText 不使用可選參數
                bitmapBuilder.DrawText($"PAUSED\nFrame {_currentFrameIndex + 1}");
                
                return bitmapBuilder.ToImage();
            }
        }

        // === 創建預設脈衝圖片（當嵌入圖片不存在時）===
        private BitmapImage CreateDefaultPulseImage(int frameIndex, PluginImageSize imageSize)
        {
            using (var bitmapBuilder = new BitmapBuilder(imageSize))
            {
                // 計算脈衝強度（0-1之間的正弦波）
                double pulseIntensity = (Math.Sin((double)frameIndex / _totalFrames * 2 * Math.PI) + 1) / 2;
                
                // 調整為 20%-100% 的強度範圍
                pulseIntensity = 0.2 + (pulseIntensity * 0.8);
                
                // 顯示脈衝效果文字和強度
                string intensityBar = new string('█', (int)(pulseIntensity * 10));
                bitmapBuilder.DrawText($"PULSE\n{intensityBar}\n{frameIndex + 1}/{_totalFrames}");
                
                return bitmapBuilder.ToImage();
            }
        }

        // === 創建錯誤圖片 ===
        private BitmapImage CreateErrorImage(int frameIndex, PluginImageSize imageSize)
        {
            using (var bitmapBuilder = new BitmapBuilder(imageSize))
            {
                bitmapBuilder.DrawText($"ERROR\nFrame {frameIndex + 1}\nLoad Failed");
                
                return bitmapBuilder.ToImage();
            }
        }
    }
}
