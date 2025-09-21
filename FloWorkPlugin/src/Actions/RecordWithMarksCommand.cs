namespace Loupedeck.FloWorkPlugin
{
    using System;
    using System.Diagnostics;
    using System.IO;
    using System.Timers;

    public sealed class RecordWithMarksCommand : PluginDynamicCommand, IDisposable
    {
        private const string PythonExe  = @"C:\Users\miche\AppData\Local\Microsoft\WindowsApps\pythonw.exe";
        private const string ScriptPath = @"D:\FloWorkPlugin\src\Actions\python_scripts\rec.py";
        private static readonly TimeSpan DoubleTapWindow = TimeSpan.FromMilliseconds(600);

        private bool _recording;
        private int _markCount;

        private readonly Timer _tapTimer;
        private bool _tapArmed;

        // state watching from Python
        private FileSystemWatcher _stateWatcher;
        private Timer _statePoll;
        private readonly string _baseDir;
        private readonly string _statePath;

        public RecordWithMarksCommand()
            : base("Sync-note Recorder", "Start/Mark/Stop via Python helper (Win+Alt+R)", "Meeting")
        {
            _tapTimer = new Timer(DoubleTapWindow.TotalMilliseconds) { AutoReset = false };
            _tapTimer.Elapsed += (_, __) =>
            {
                if (_recording && _tapArmed)
                {
                    _tapArmed = false;
                    Mark();
                }
            };

            _baseDir = ResolveBaseDir();
            _statePath = Path.Combine(_baseDir, "session_state.json");
        }

        protected override void RunCommand(String actionParameter)
        {
            if (!_recording)
            {
                Start();
                return;
            }

            // 錄製中：單擊 = Mark；雙擊 = Stop
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
                return $"REC● Marks: {_markCount}";
            return "Start Recording";
        }

        // --- Actions ---

        private void Start()
        {
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

            if (!string.IsNullOrWhiteSpace(so))
                PluginLog.Info($"start: {Trim(so)}");

            StartStateWatchers();
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
            StopStateWatchers();
            this.ActionImageChanged();
        }

        // --- Helpers ---

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

        // -------- state watch (stop signal from Python) --------

        private void StartStateWatchers()
        {
            try { Directory.CreateDirectory(_baseDir); } catch { }

            _stateWatcher?.Dispose();
            _stateWatcher = new FileSystemWatcher(_baseDir)
            {
                Filter = "session_state.json",
                NotifyFilter = NotifyFilters.FileName | NotifyFilters.LastWrite | NotifyFilters.Size
            };
            _stateWatcher.Deleted += (_, __) => OnStateGone("deleted");
            _stateWatcher.Renamed += (_, __) => OnStateGone("renamed");
            _stateWatcher.Changed += (_, __) => { /* 可加：偵測 recording=false 的版本 */ };
            _stateWatcher.EnableRaisingEvents = true;

            _statePoll?.Stop();
            _statePoll = new Timer(800) { AutoReset = true };
            _statePoll.Elapsed += (_, __) =>
            {
                if (!_recording) return;
                if (!File.Exists(_statePath))
                    OnStateGone("missing_poll");
            };
            _statePoll.Start();
        }

        private void StopStateWatchers()
        {
            try { _stateWatcher?.Dispose(); } catch { }
            _stateWatcher = null;
            try { _statePoll?.Stop(); _statePoll?.Dispose(); } catch { }
            _statePoll = null;
        }

        private void OnStateGone(string reason)
        {
            PluginLog.Info($"state gone: {reason}");
            this.ForceStopUi();
        }

        private static string ResolveBaseDir()
        {
            // 對齊 rec.py:
            // BASE = MEI_LOG_DIR or %USERPROFILE%\Documents\Loupedeck\MeiPlugin\ScreenRecordMarks
            var env = Environment.GetEnvironmentVariable("MEI_LOG_DIR");
            if (!string.IsNullOrWhiteSpace(env))
                return env;

            var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            return Path.Combine(home, "Documents", "Loupedeck", "MeiPlugin", "ScreenRecordMarks");
        }

        public void Dispose()
        {
            _tapTimer?.Stop();
            _tapTimer?.Dispose();
            StopStateWatchers();
        }
    }
}
