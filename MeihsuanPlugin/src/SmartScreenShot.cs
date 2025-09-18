using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using System.IO;
using System.Diagnostics;
// SmartScreenshotAction.cs
namespace Loupedeck.MeihsuanPlugin{
//---------- python response item ----------
    public class PythonResponse
    {
        public bool success { get; set; }
        public string name { get; set; }
        public string processName { get; set; }
        public string windowTitle { get; set; }

        public string error { get; set; }
    }

// --------- python helper to run script and get result ----------

    public static class PythonHelper //static class -> 不用建立object也可以使用裡面的方法
    //define run python script logic and get the json result
    //resolve a json object and return a PythonResponse list
    {
        // PythonHelper.cs

        public static List<PythonResponse> RunScript(string scriptName, string args)
        {
            try
            {
                var path = Path.GetDirectoryName(typeof(MeihsuanPlugin).Assembly.Location);
                var scriptPath = Path.Combine(path, "python_scripts", scriptName);

                if (!File.Exists(scriptPath))
                {
                    return null;
                }

                ProcessStartInfo start = new ProcessStartInfo
                {
                    FileName = "python.exe",
                    Arguments = $"\"{scriptPath}\" {args}",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                };

                using (Process process = Process.Start(start))
                {
                    string resultJson = process.StandardOutput.ReadToEnd();
                    string error = process.StandardError.ReadToEnd();
                    process.WaitForExit();

                    if (!String.IsNullOrEmpty(error))
                    {
                        PluginLog.Error($"Python script error: {error}");
                    }

                    if (String.IsNullOrEmpty(resultJson))
                    {
                        return null;
                    }

                    // return a list of python response (convert from json)
                    return JsonConvert.DeserializeObject<List<PythonResponse>>(resultJson);
                }
            }
            catch (Exception ex)
            {
                PluginLog.Error(ex, "Error running Python script");
                return null;
            }
        }
    }

// --------- smart screenshot action ----------
    public class SmartScreenshotAction : PluginDynamicCommand
    {
        public SmartScreenshotAction()
            : base("Smart Screenshot", "Tool to find screenshot target", "Productivity")
        {
        }

        protected override void RunCommand(String actionParameter)
        {
            // // 1. TODO: 執行截圖到剪貼簿的邏輯

            // // 2. 呼叫 Python 腳本來處理複雜邏輯
            // // return a list of python response
            // List<PythonResponse> suggestions = PythonHelper.RunScript("history_tracker.py", actionParameter);

            // if (suggestions == null || suggestions.Count == 0)
            // {
            //     this.Plugin.Log.Warning("Python script returned no suggestions.");
            //     return;
            // }
            // // 3. 建立 Action Ring 的項目
            // var actionRingItems = new List<ActionEditorAction>();
            // foreach (var suggestion in suggestions)
            // {
            //     if (suggestion.success) // 只顯示成功的項目
            //     {
            //         // 把整個 suggestion 物件序列化成 JSON 字串，當作 actionParameter
            //         // 這樣在 ApplyAdjustment 中就可以拿到完整的資訊
            //         var itemParameter = JsonConvert.SerializeObject(suggestion);

            //         actionRingItems.Add(
            //             this.CreateCommand(
            //                 itemParameter,          // 參數：包含視窗資訊的JSON字串
            //                 suggestion.name,        // Ring 上顯示的名稱
            //                 suggestion.processName  // Ring 上顯示的群組/描述
            //             )
            //         );
            //         this.Plugin.ClientApplication.ShowActionRing("Select App to Paste", actionRingItems);
            //     }
            // }
            // else
            // {
            //     // 處理 Python 腳本執行失敗的情況
            //     var errorMessage = response?.Error ?? "Unknown error.";
            //     this.Plugin.Log.Error($"Python script failed: {errorMessage}");
            // }
        }
    }
}