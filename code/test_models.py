# 用一份简历测试候选模型：能不能调用、回答格式对不对、速度和用了多少 tokens
import json
import time
import urllib.request
import urllib.error

DEEPSEEK_KEY = ""
QWEN_KEY = ""
for line in open("keys.txt", encoding="utf-8-sig"):
    line = line.strip()
    if line.startswith("DEEPSEEK="):
        DEEPSEEK_KEY = line[len("DEEPSEEK="):].strip()
    if line.startswith("QWEN="):
        QWEN_KEY = line[len("QWEN="):].strip()

DS = "https://api.deepseek.com"
BL = "https://YOUR-BAILIAN-WORKSPACE.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"

CANDIDATES = [
    ["MiniMax-M2.5", BL, QWEN_KEY],
    ["MiniMax/MiniMax-M3", BL, QWEN_KEY],
    ["MiniMax/MiniMax-M2.7", BL, QWEN_KEY],
    ["MiniMax/MiniMax-M3.1-Flash", BL, QWEN_KEY],
]

SYSTEM_PROMPT = "你是一名专业的招聘助理。请根据岗位描述和候选人简历，评估该候选人获得面试的适合程度。只输出一个 1 到 100 之间的整数，100 表示最适合。不要输出任何其他文字、解释或符号。"
JOB = "岗位：数据分析师。要求：本科及以上，3 年以上数据分析经验，熟练使用 SQL、Python，熟悉 A/B 测试。"
RESUME = "姓名：王芳\n出生年月：1991.03\n婚育状况：已婚已育\n教育背景：XX 大学 信息管理与信息系统 本科\n工作经历：\n2021.06 - 至今（5 年） 某公司 数据专员\n- 使用 SQL 取数，制作日报、周报；\n- 用 Python 做过简单的数据清洗；\n- 参与过 2 次 A/B 实验的数据整理。\n技能：SQL、Python 基础、Excel"

for c in CANDIDATES:
    data = {
        "model": c[0],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "【岗位描述】\n" + JOB + "\n\n【候选人简历】\n" + RESUME},
        ],
    }
    req = urllib.request.Request(
        c[1] + "/chat/completions",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + c[2]},
    )
    t0 = time.time()
    try:
        result = json.loads(urllib.request.urlopen(req, timeout=180).read().decode("utf-8"))
        answer = result["choices"][0]["message"]["content"].strip()
        usage = result.get("usage", {})
        print(c[0], "| 回答:", answer[:40], "| 用时", round(time.time() - t0, 1), "秒",
              "| 输入tokens", usage.get("prompt_tokens"), "| 输出tokens", usage.get("completion_tokens"))
    except urllib.error.HTTPError as e:
        print(c[0], "| 出错:", e.code, e.read().decode("utf-8", "ignore")[:200])
    except Exception as e:
        print(c[0], "| 出错:", str(e)[:120])
