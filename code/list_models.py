# 列出两个平台上可以调用的模型名称（不会显示你的 key）
import json
import urllib.request

DEEPSEEK_KEY = ""
QWEN_KEY = ""
for line in open("keys.txt", encoding="utf-8-sig"):
    line = line.strip()
    if line.startswith("DEEPSEEK="):
        DEEPSEEK_KEY = line[len("DEEPSEEK="):].strip()
    if line.startswith("QWEN="):
        QWEN_KEY = line[len("QWEN="):].strip()

QWEN_URL = "https://YOUR-BAILIAN-WORKSPACE.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"

WORDS = ["qwen", "deepseek", "kimi", "moonshot", "glm", "minimax", "doubao"]

for name, url, key in [["DeepSeek 平台", "https://api.deepseek.com", DEEPSEEK_KEY], ["百炼平台", QWEN_URL, QWEN_KEY]]:
    print("=====", name, "=====")
    try:
        req = urllib.request.Request(url + "/models", headers={"Authorization": "Bearer " + key})
        result = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
        ids = []
        for m in result["data"]:
            ids.append(m["id"])
        ids.sort()
        for i in ids:
            for w in WORDS:
                if w in i.lower():
                    print(i)
                    break
        print("共", len(ids), "个模型")
    except Exception as e:
        print("出错：", e)
