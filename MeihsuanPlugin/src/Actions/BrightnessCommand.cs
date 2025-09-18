namespace Loupedeck.MeihsuanPlugin 
{
    using System;
    using System.Diagnostics;
    using System.Threading.Tasks;

    public class BrightnessCommand : PluginDynamicCommand
    {
        private Process _brightnessProcess = null;
        private bool _isRunning = false;

        public BrightnessCommand()
            : base(displayName: "Auto Brightness", description: "Launch/Stop automatic brightness adjustment", groupName: "Commands")
        {
        }

        protected override void RunCommand(String actionParameter)
        {
            try
            {
                if (_isRunning && _brightnessProcess != null && !_brightnessProcess.HasExited)
                {
                    _brightnessProcess.Kill();
                    _brightnessProcess.Dispose();
                    _brightnessProcess = null;
                    _isRunning = false;
                    PluginLog.Info("Brightness adjustment stopped");
                    this.ActionImageChanged();
                }
                else
                {
                    var processStartInfo = new ProcessStartInfo
                    {
                        FileName = @"C:\Users\miche\AppData\Local\Microsoft\WindowsApps\python.exe",
                        Arguments = @"brightness.py",
                        WorkingDirectory = @"D:\2025_MC_Hackathon_Team_Meihsuan\MeihsuanPlugin\ExamplePlugin\src\Actions\",
                        UseShellExecute = false,
                        CreateNoWindow = true, 
                        RedirectStandardOutput = true,
                        RedirectStandardError = true
                    };

                    _brightnessProcess = Process.Start(processStartInfo);
                    _isRunning = true;
                    
                    PluginLog.Info("Brightness adjustment launched successfully");

                    if (_brightnessProcess != null)
                    {
                        _brightnessProcess.EnableRaisingEvents = true;
                        _brightnessProcess.Exited += (sender, e) =>
                        {
                            var exitCode = _brightnessProcess.ExitCode;
                            var output = "";
                            var error = "";
                            
                            try
                            {
                                output = _brightnessProcess.StandardOutput.ReadToEnd();
                                error = _brightnessProcess.StandardError.ReadToEnd();
                            }
                            catch { }

                            _isRunning = false;
                            _brightnessProcess?.Dispose();
                            _brightnessProcess = null;
                            this.ActionImageChanged();
                            
                            PluginLog.Info($"Brightness adjustment process exited with code: {exitCode}");
                            if (!string.IsNullOrEmpty(output)) PluginLog.Info($"Output: {output}");
                            if (!string.IsNullOrEmpty(error)) PluginLog.Info($"Error: {error}");
                        };
                        
                        Task.Run(async () =>
                        {
                            await Task.Delay(1000);
                            if (_brightnessProcess?.HasExited == true)
                            {
                                PluginLog.Info("Brightness process exited quickly, checking for errors");
                            }
                        });
                    }
                    this.ActionImageChanged();
                }
            }
            catch (Exception ex)
            {
                PluginLog.Info($"Error managing brightness adjustment: {ex.Message}");
                _isRunning = false;
                _brightnessProcess = null;
            }
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize)
        {
            return _isRunning ? "Stop Brightness" : "Auto Brightness";
        }

        ~BrightnessCommand()
        {
            CleanupProcess();
        }

        private void CleanupProcess()
        {
            if (_brightnessProcess != null && !_brightnessProcess.HasExited)
            {
                try
                {
                    _brightnessProcess.Kill();
                    _brightnessProcess.Dispose();
                }
                catch { }
                finally
                {
                    _brightnessProcess = null;
                    _isRunning = false;
                }
            }
        }
    }
}
