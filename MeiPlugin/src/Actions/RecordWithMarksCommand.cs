namespace Loupedeck.MeiPlugin
{
    using System;
    using System.Diagnostics;
    using System.IO;
    using System.Timers;

    public sealed class RecordWithMarksCommand : PluginDynamicCommand, IDisposable
    {
        private const string PythonExe  = @"C:\Users\seash\AppData\Local\Programs\Python\Python310\pythonw.exe";
        private const string ScriptPath = @"C:\2025-Autumn\2025_MC_Hackathon_Team_Meihsuan\MeiPlugin\src\Actions\python_scripts\rec.py";
        private static readonly TimeSpan DoubleTapWindow = TimeSpan.FromMilliseconds(600);

        private bool _recording;
        private DateTime _sessionStartUtc;
        private int _markCount;

        // 延後判斷用
        private readonly Timer _tapTimer;
        private bool _tapArmed;

        private readonly Timer _uiTick = new Timer(1000) { AutoReset = true };

        public RecordWithMarksCommand()
            : base("Start Recording", "Start/Mark/Stop via Python helper (Win+Alt+R)", "Commands")
        {
            _uiTick.Elapsed += (_, __) => this.ActionImageChanged();

            _tapTimer = new Timer(DoubleTapWindow.TotalMilliseconds) { AutoReset = false };
            _tapTimer.Elapsed += (_, __) =>
            {
                // 時間窗到期仍只有一次按壓 → 當作單擊 => Mark()
                if (_recording && _tapArmed)
                {
                    _tapArmed = false;
                    Mark();
                }
            };
        }

        protected override void RunCommand(String actionParameter)
        {
            if (!_recording)
            {
                Start();
                return;
            }

            // 錄製中：第一次按 → 武裝雙擊窗；第二次按（窗內）→ Stop()
            if (!_tapArmed)
            {
                _tapArmed = true;
                _tapTimer.Stop();
                _tapTimer.Interval = DoubleTapWindow.TotalMilliseconds;
                _tapTimer.Start();
            }
            else
            {
                _tapArmed = false;
                _tapTimer.Stop();
                Stop();
            }
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
        {
            if (_recording)
            {
                var elapsed = DateTime.UtcNow - _sessionStartUtc;
                return $"REC ●  {Fmt(elapsed)}{Environment.NewLine}Marks: {_markCount}";
            }
            return "Start Recording";
        }

        // --- Actions ---

        private void Start()
        {
            // 清乾淨雙擊狀態
            _tapArmed = false;
            _tapTimer.Stop();

            var (exit, so, se) = RunPy("start");
            if (exit != 0)
            {
                PluginLog.Error($"start: exit={exit} stderr={Trim(se)}");
                return;
            }

            _recording = true;
            _markCount = 0;
            _sessionStartUtc = DateTime.UtcNow;

            if (!string.IsNullOrWhiteSpace(so))
                PluginLog.Info($"start: {Trim(so)}");

            _uiTick.Start();
            this.ActionImageChanged();
        }

        private void Mark()
        {
            var (exit, so, se) = RunPy("mark");

            if (exit != 0)
            {
                PluginLog.Error($"mark: exit={exit} stderr={Trim(se)}");
                if (!string.IsNullOrEmpty(se) && se.Contains("No active session"))
                    ForceStopUi(); // Python 已停，UI 跟上
                return;
            }

            var text = Trim(so);

            // 編輯視窗選 Stop / Save & Stop：Python 會印 __STOPPED__
            if (text.Contains("__STOPPED__"))
            {
                PluginLog.Info("Stopped via editor");
                ForceStopUi();
                return;
            }

            if (text.Equals("Canceled", StringComparison.OrdinalIgnoreCase))
            {
                PluginLog.Info("mark canceled by user");
                return;
            }

            _markCount++;
            if (!string.IsNullOrWhiteSpace(text))
                PluginLog.Info($"mark[{_markCount}]: {text}");

            this.ActionImageChanged();
        }

        private void Stop()
        {
            try
            {
                var (exit, so, se) = RunPy("stop");
                if (exit != 0)
                    PluginLog.Error($"stop: exit={exit} stderr={Trim(se)}");
                else if (!string.IsNullOrWhiteSpace(so))
                    PluginLog.Info($"stop: {Trim(so)}");
            }
            finally
            {
                ForceStopUi();
            }
        }

        private void ForceStopUi()
        {
            _tapArmed = false;
            _tapTimer.Stop();

            _recording = false;
            _uiTick.Stop();
            this.ActionImageChanged();
        }

        // --- Helpers ---

        private static string Fmt(TimeSpan t)
            => (t.TotalHours >= 1) ? $"{(int)t.TotalHours:00}:{t.Minutes:00}:{t.Seconds:00}"
                                   : $"{t.Minutes:00}:{t.Seconds:00}";

        private static string Trim(string s) => s?.Trim() ?? "";

        private static (int exit, string stdout, string stderr) RunPy(string subcmd)
        {
            var psi = new ProcessStartInfo
            {
                FileName = PythonExe,
                Arguments = $"\"{ScriptPath}\" {subcmd}",
                WorkingDirectory = Path.GetDirectoryName(ScriptPath)!,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };

            using var p = new Process { StartInfo = psi };
            p.Start();
            var so = p.StandardOutput.ReadToEnd();
            var se = p.StandardError.ReadToEnd();
            p.WaitForExit();
            return (p.ExitCode, so, se);
        }

        public void Dispose()
        {
            _tapTimer?.Stop();
            _tapTimer?.Dispose();
            _uiTick?.Stop();
            _uiTick?.Dispose();
        }
    }
}
