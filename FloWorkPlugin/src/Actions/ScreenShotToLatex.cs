namespace Loupedeck.FloWorkPlugin 
{
    using System;
    using System.Diagnostics;
    using System.IO;
    using System.Runtime.InteropServices;

    public class ScreenShotToLatex : PluginDynamicCommand
    {
        private const string LATEXOCR_PATH = @"D:\download\2025_MC_Hackathon_Team_Meihsuan\MeiPlugin\.venv39\Scripts\latexocr.exe";

        public ScreenShotToLatex()
            : base(displayName: "Image-to-LaTeX", description: "Convert screenshot to LaTeX", groupName: "Study")
        {
        }

        protected override void RunCommand(String actionParameter)
        {
            try
            {
                // 檢查 latexocr.exe 是否存在
                if (!File.Exists(LATEXOCR_PATH))
                {
                    PluginLog.Error($"LaTeX OCR executable not found at: {LATEXOCR_PATH}");
                    return;
                }

                // 執行 latexocr 命令
                string result = RunBashCommand(LATEXOCR_PATH);

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
                PluginLog.Warning($"Exit code: {process.ExitCode}");
            }

            // 如果有錯誤輸出但沒有標準輸出，返回錯誤信息
            if (string.IsNullOrEmpty(output) && !string.IsNullOrEmpty(error))
            {
                return $"Error: {error}";
            }

            return output;
        }

        protected override String GetCommandDisplayName(String actionParameter, PluginImageSize imageSize) =>
            "Image to\nLaTeX OCR";
    }
}