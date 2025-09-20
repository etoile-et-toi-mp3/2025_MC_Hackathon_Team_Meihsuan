using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Media.Imaging;

namespace Loupedeck.MeiPlugin
{
    // 脈衝光效命令類
    public class PulseEffectCommand : PluginDynamicCommand
    {
        private Timer _pulseTimer;
        private int _currentFrame = 0;
        private bool _isRunning = false;
        private readonly object _lockObject = new object();
        
        // 脈衝參數
        private readonly int _maxFrames = 60; // 脈衝週期總幀數
        private readonly int _pulseSpeed = 50; // 毫秒間隔
        
        public PulseEffectCommand() 
            : base("Pulse Effect", "創建脈衝光效", "Effects")
        {
        }

        protected override void RunCommand(string actionParameter)
        {
            lock (_lockObject)
            {
                if (_isRunning)
                {
                    StopPulse();
                }
                else
                {
                    StartPulse();
                }
            }
        }

        private void StartPulse()
        {
            _isRunning = true;
            _currentFrame = 0;
            
            _pulseTimer = new Timer(UpdatePulseFrame, null, 0, _pulseSpeed);
        }

        private void StopPulse()
        {
            _isRunning = false;
            _pulseTimer?.Dispose();
            _pulseTimer = null;
            
            // 重置到默認狀態
            this.ActionImageChanged(string.Empty);
        }

        private void UpdatePulseFrame(object state)
        {
            if (!_isRunning) return;

            lock (_lockObject)
            {
                _currentFrame = (_currentFrame + 1) % _maxFrames;
                
                // 通知 Loupedeck 服務更新圖像
                this.ActionImageChanged(string.Empty);
            }
        }

        protected override BitmapImage GetCommandImage(string actionParameter, PluginImageSize imageSize)
        {
            if (!_isRunning)
            {
                return CreateStaticImage(imageSize, 0.3f); // 靜態時30%亮度
            }

            // 計算脈衝亮度（正弦波）
            float brightness = CalculatePulseBrightness(_currentFrame);
            return CreatePulseImage(imageSize, brightness);
        }

        private float CalculatePulseBrightness(int frame)
        {
            // 使用正弦波創建平滑的脈衝效果
            double angle = (double)frame / _maxFrames * 2 * Math.PI;
            float pulse = (float)(Math.Sin(angle) + 1) / 2; // 0到1之間
            
            // 調整亮度範圍（20%-100%）
            return 0.2f + (pulse * 0.8f);
        }

        private BitmapImage CreatePulseImage(PluginImageSize imageSize, float brightness)
        {
            int size = GetImageSize(imageSize);
            
            using (var bitmap = new Bitmap(size, size))
            using (var graphics = Graphics.FromImage(bitmap))
            {
                graphics.Clear(Color.Black);
                
                // 創建脈衝圓形
                var centerX = size / 2;
                var centerY = size / 2;
                var radius = size / 3;
                
                // 計算顏色（從深藍到亮青藍）
                int blue = (int)(255 * brightness);
                int green = (int)(200 * brightness);
                var pulseColor = Color.FromArgb((int)(255 * brightness), 0, green, blue);
                
                // 創建漸層筆刷
                using (var brush = new SolidBrush(pulseColor))
                {
                    graphics.FillEllipse(brush, centerX - radius, centerY - radius, radius * 2, radius * 2);
                }
                
                // 添加外圈光暈效果
                var glowRadius = (int)(radius * (1 + brightness * 0.5f));
                var glowColor = Color.FromArgb((int)(100 * brightness), 0, green/2, blue/2);
                using (var glowBrush = new SolidBrush(glowColor))
                {
                    graphics.FillEllipse(glowBrush, centerX - glowRadius, centerY - glowRadius, glowRadius * 2, glowRadius * 2);
                }
                
                return BitmapToImageSource(bitmap);
            }
        }

        private BitmapImage CreateStaticImage(PluginImageSize imageSize, float brightness)
        {
            int size = GetImageSize(imageSize);
            
            using (var bitmap = new Bitmap(size, size))
            using (var graphics = Graphics.FromImage(bitmap))
            {
                graphics.Clear(Color.Black);
                
                var centerX = size / 2;
                var centerY = size / 2;
                var radius = size / 3;
                
                var staticColor = Color.FromArgb((int)(255 * brightness), 0, (int)(100 * brightness), (int)(180 * brightness));
                
                using (var brush = new SolidBrush(staticColor))
                {
                    graphics.FillEllipse(brush, centerX - radius, centerY - radius, radius * 2, radius * 2);
                }
                
                return BitmapToImageSource(bitmap);
            }
        }

        private int GetImageSize(PluginImageSize imageSize)
        {
            return imageSize switch
            {
                PluginImageSize.Width60 => 60,
                PluginImageSize.Width80 => 80,
                PluginImageSize.Width90 => 90,
                _ => 80
            };
        }

        private BitmapImage BitmapToImageSource(Bitmap bitmap)
        {
            using (var stream = new MemoryStream())
            {
                bitmap.Save(stream, ImageFormat.Png);
                stream.Position = 0;
                
                var bitmapImage = new BitmapImage();
                bitmapImage.BeginInit();
                bitmapImage.CacheOption = BitmapCacheOption.OnLoad;
                bitmapImage.StreamSource = stream;
                bitmapImage.EndInit();
                bitmapImage.Freeze();
                
                return bitmapImage;
            }
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                StopPulse();
            }
            base.Dispose(disposing);
        }
    }

    // 多彩脈衝效果命令
    public class RainbowPulseCommand : PluginDynamicCommand
    {
        private Timer _timer;
        private int _hueShift = 0;
        private bool _isActive = false;
        
        public RainbowPulseCommand() 
            : base("Rainbow Pulse", "彩虹脈衝效果", "Effects")
        {
        }

        protected override void RunCommand(string actionParameter)
        {
            if (_isActive)
            {
                StopRainbowPulse();
            }
            else
            {
                StartRainbowPulse();
            }
        }

        private void StartRainbowPulse()
        {
            _isActive = true;
            _timer = new Timer(UpdateRainbow, null, 0, 100);
        }

        private void StopRainbowPulse()
        {
            _isActive = false;
            _timer?.Dispose();
            _timer = null;
            this.ActionImageChanged(string.Empty);
        }

        private void UpdateRainbow(object state)
        {
            if (!_isActive) return;
            
            _hueShift = (_hueShift + 10) % 360;
            this.ActionImageChanged(string.Empty);
        }

        protected override BitmapImage GetCommandImage(string actionParameter, PluginImageSize imageSize)
        {
            int size = GetImageSize(imageSize);
            
            using (var bitmap = new Bitmap(size, size))
            using (var graphics = Graphics.FromImage(bitmap))
            {
                graphics.Clear(Color.Black);
                
                if (_isActive)
                {
                    // 創建彩虹脈衝
                    var centerX = size / 2;
                    var centerY = size / 2;
                    var maxRadius = size / 2;
                    
                    for (int ring = 0; ring < 5; ring++)
                    {
                        var radius = maxRadius - (ring * 8);
                        if (radius <= 0) continue;
                        
                        var hue = (_hueShift + (ring * 60)) % 360;
                        var color = HslToRgb(hue, 100, 50);
                        
                        using (var brush = new SolidBrush(Color.FromArgb(150, color)))
                        {
                            graphics.FillEllipse(brush, centerX - radius, centerY - radius, radius * 2, radius * 2);
                        }
                    }
                }
                else
                {
                    // 靜態彩虹圓
                    var centerX = size / 2;
                    var centerY = size / 2;
                    var radius = size / 3;
                    
                    using (var brush = new SolidBrush(Color.FromArgb(100, 128, 0, 255)))
                    {
                        graphics.FillEllipse(brush, centerX - radius, centerY - radius, radius * 2, radius * 2);
                    }
                }
                
                return BitmapToImageSource(bitmap);
            }
        }

        private Color HslToRgb(int hue, int saturation, int lightness)
        {
            double h = hue / 360.0;
            double s = saturation / 100.0;
            double l = lightness / 100.0;
            
            double r, g, b;
            
            if (s == 0)
            {
                r = g = b = l;
            }
            else
            {
                Func<double, double, double, double> hue2rgb = (p, q, t) =>
                {
                    if (t < 0) t += 1;
                    if (t > 1) t -= 1;
                    if (t < 1.0/6) return p + (q - p) * 6 * t;
                    if (t < 1.0/2) return q;
                    if (t < 2.0/3) return p + (q - p) * (2.0/3 - t) * 6;
                    return p;
                };
                
                var q = l < 0.5 ? l * (1 + s) : l + s - l * s;
                var p = 2 * l - q;
                r = hue2rgb(p, q, h + 1.0/3);
                g = hue2rgb(p, q, h);
                b = hue2rgb(p, q, h - 1.0/3);
            }
            
            return Color.FromArgb((int)(r * 255), (int)(g * 255), (int)(b * 255));
        }

        private int GetImageSize(PluginImageSize imageSize)
        {
            return imageSize switch
            {
                PluginImageSize.Width60 => 60,
                PluginImageSize.Width80 => 80,
                PluginImageSize.Width90 => 90,
                _ => 80
            };
        }

        private BitmapImage BitmapToImageSource(Bitmap bitmap)
        {
            using (var stream = new MemoryStream())
            {
                bitmap.Save(stream, ImageFormat.Png);
                stream.Position = 0;
                
                var bitmapImage = new BitmapImage();
                bitmapImage.BeginInit();
                bitmapImage.CacheOption = BitmapCacheOption.OnLoad;
                bitmapImage.StreamSource = stream;
                bitmapImage.EndInit();
                bitmapImage.Freeze();
                
                return bitmapImage;
            }
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                StopRainbowPulse();
            }
            base.Dispose(disposing);
        }
    }

    // 主插件類
    public class PulseEffectPlugin : Plugin
    {
        public override void Load()
        {
            // 註冊脈衝效果命令
            this.AddCommand(new PulseEffectCommand());
            this.AddCommand(new RainbowPulseCommand());
        }

        public override void Unload()
        {
            // 清理資源
        }
    }
}
