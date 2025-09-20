namespace Loupedeck.ExamplePlugin
{
    using System;
    using System.Diagnostics;
    using System.IO;
    using System.Runtime.InteropServices;

    public class ScreenShotToLatex : PluginDynamicCommand
    {
        public ScreenShotToLatex()
            : base(displayName: "ScreenShot to LaTeX", description: "Convert screenshot to LaTeX", groupName: "ScreenShot")
        {
        }

        protected override void RunCommand(String actionParameter)
        {
            try
            {
                // 執行 latexocr 命令
                string command = "latexocr";
                
                // 執行 bash 命令
                string result = RunBashCommand(command);
                
                PluginLog.Info("LaTeX OCR launched successfully");
                PluginLog.Info($"Command output: {result}");
            }
            catch (Exception ex)
            {
                PluginLog.Error($"Error launching LaTeX OCR: {ex.Message}");
                PluginLog.Error($"Exception details: {ex}");
            }
        }

        private string RunBashCommand(string command)
        {
            string shell, shellArgs;
            
            // 根據作業系統選擇適當的 shell
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                shell = "cmd";
                shellArgs = "/c";
            }
            else
            {
                shell = "bash";
                shellArgs = "-c";
            }

            var processInfo = new ProcessStartInfo(shell, $"{shellArgs} \"{command}\"")
            {
                CreateNoWindow = true,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                WorkingDirectory = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile) // 設定工作目錄為用戶家目錄
            };

            using var process = Process.Start(processInfo);
            
            string output = process.StandardOutput.ReadToEnd();
            string error = process.StandardError.ReadToEnd();
            
            process.WaitForExit();

            if (process.ExitCode != 0 && !string.IsNullOrEmpty(error))
            {
                PluginLog.Warning($"Command warning/error: {error}");
            }

            return output;
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize) =>
            "Screenshot to\nLaTeX OCR";
    }
}
