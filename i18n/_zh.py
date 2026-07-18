# file: i18n/_zh.py

"""Simplified Chinese UI strings. Mirrors ``_en.py`` key for key.

Conventions this translation follows:

* **Mainland software register.** Terse, idiomatic zh-CN as real desktop apps
  phrase it — 设置 / 保存 / 取消 / 快捷键 / 术语表 / 许可证 / 激活. No spaces
  between Chinese characters; placeholders sit directly against the text.
* **Product and protocol nouns stay Latin**: Omni Verte, Pro, Free, Whisper,
  OpenAI, Groq, CPU, CUDA, GPU, DPAPI, DevOps, CRM, LLM, ASR, API, Windows,
  NVIDIA, F9/F11. Transliterating them helps nobody and breaks search.
* **Provider console labels stay verbatim.** platform.openai.com / console.groq.com
  have no Chinese UI, so their button names ("Create new secret key") are kept in
  Latin and quoted with 「」, mirroring how _ru.py keeps them.
* **Placeholders are byte-preserved.** Every {name} field is reused exactly,
  placed where Chinese word order reads naturally.
* **Hints keep English's plain, helpful register** — no invented jargon.
"""

from __future__ import annotations

LOCALE = "zh"

STRINGS: dict[str, str] = {
    # ---------- app-wide ----------
    "app.title": "Omni Verte",

    # ---------- shared chrome ----------
    "common.on": "开",
    "common.off": "关",
    "common.cancel": "取消",
    "common.save": "保存",
    "common.pro": "Pro",
    "common.pro.tooltip": "Pro 功能 — 加入等候名单",
    "common.help.where_key": "在哪里获取密钥？",

    # ---------- tray menu ----------
    "tray.show_window": "显示窗口",
    "tray.indicator.show": "显示悬浮指示器",
    "tray.indicator.hide": "隐藏悬浮指示器",
    "tray.mode": "激活方式：{mode}",
    "tray.mode.keyboard": "键盘",
    "tray.mode.mouse": "鼠标",
    "tray.keys": "激活按键",
    "tray.keys.change": "更改（按一个键）",
    "tray.hotkey.item": "{action}：{key}",
    "tray.action.transcribe": "转写",
    "tray.action.translate": "转写并翻译",
    "tray.action.custom": "转写并改写",
    "tray.suppress.on": "强制捕获：开（按键被拦截）",
    "tray.suppress.off": "强制捕获：关（按键透传）",
    "tray.mouse_button": "激活用鼠标键：{button}",
    "tray.model": "识别方式：{model}",
    "tray.model.local": "本地：{model}",
    "tray.model.openai": "OpenAI API：{model}",
    "tray.model.groq": "Groq：{model}",
    "tray.device": "使用设备：{device}",
    "tray.device.openai": "OpenAI API",
    "tray.device.groq": "Groq",
    "tray.language": "主语言：{language}",
    "tray.language.other": "其他语言…",
    "tray.settings": "设置…",
    "tray.close": "关闭",
    "tray.tooltip.loading": "Omni Verte — 正在加载模型…",
    "tray.tooltip.failed": "Omni Verte — 模型加载失败（检查网络，在设置中重新选择）",

    # ---------- settings: General page ----------
    "page.general.title": "常规",
    "page.general.hint": "界面语言、快捷键和行为开关。其中大部分也可从托盘菜单访问。",

    "general.interface.title": "界面",
    "general.interface.hint": "应用与你交流所用的语言。与你在「语言」页设置的听写和互译语言无关。",
    "general.interface.language": "语言",
    "general.interface.language.hint": "保存后生效。",

    "general.activation.title": "激活",
    "general.activation.hint": (
        "如何触发录音。键盘方式使用单个快捷键；"
        "鼠标方式使用可配置的鼠标键。"
    ),
    "general.activation.keyboard": "键盘快捷键",
    "general.activation.mouse": "鼠标键",

    # "Catch the key" — the console's own action, quoted with 「」 as elsewhere.
    "general.hotkey.transcribe": "转写并粘贴",
    "general.hotkey.transcribe.hint": "先听写，再粘贴带语法纠正和标点的转写结果。点击「捕获按键」以指定按键。",
    "general.hotkey.translate": "转写并翻译",
    "general.hotkey.translate.hint": "先听写，再翻译为副语言后粘贴。点击「捕获按键」以指定按键。",
    "general.hotkey.custom": "转写并按自定义风格改写",
    "general.hotkey.custom.hint": "先听写，再按下方所选风格改写并粘贴。点击「捕获按键」以指定按键。",

    "general.stylepair.name": "自定义",
    "general.stylepair.hint": "按 {key} 会以此风格改写你的听写内容。「自定义」使用你在「自定义风格」页设置的提示词。",

    "general.style.casual": "随意",
    "general.style.professional": "专业",
    "general.style.custom": "自定义",

    "general.suppress": "强制捕获按键",
    "general.suppress.hint": "拦截快捷键，使当前应用收不到它们（例如 F11 不会让浏览器全屏）。若引起冲突可关闭。",

    "general.mouse.label": "鼠标键",
    "general.mouse.hint": "按住以录音。",
    "general.mouse.middle": "中键",
    "general.mouse.left": "左键",
    "general.mouse.right": "右键",

    "general.behaviour.title": "行为",
    "general.behaviour.floating": "悬浮指示器",
    "general.behaviour.floating.hint": "屏幕角落的小状态圆点。",
    "general.behaviour.double_tap": "双击时打开窗口",
    "general.behaviour.double_tap.hint": "快速按两次激活键/按钮（300 毫秒内）即可将主窗口置于最前。",
    "general.behaviour.autostart": "随 Windows 启动",
    "general.behaviour.autostart.hint": "登录 Windows 时自动启动 Omni Verte。",

    # Action names interpolated into general.error.hotkey_empty; kept as their
    # own keys so the error can name each action naturally.
    "general.action.transcribe": "转写",
    "general.action.translate": "翻译",
    "general.action.custom": "自定义风格",
    "general.error.hotkey_empty": "选择键盘模式时，{action}快捷键不能为空。",
    "general.error.hotkey_duplicate": "每个操作都需要不同的快捷键 — 当前有两个相同。",

    # ---------- settings: Languages page ----------
    "page.languages.title": "语言",
    "page.languages.hint": "翻译会自动判断在这两种语言之间的转换方向。",
    "languages.pair.title": "翻译语言对",
    "languages.primary": "主语言",
    "languages.primary.hint": "通常是你的母语或最常用的语言。",
    "languages.secondary": "副语言",
    "languages.secondary.hint": "你经常书写或使用的另一种语言。",
    "languages.swap": "互换语言",
    "languages.swap.tooltip": "互换主语言和副语言",
    "languages.error.must_differ": "主语言和副语言必须不同。",

    # ---------- app-wide ----------
    "app.tagline": "AI 听写 · 改写 · 翻译",

    # ---------- settings: Transcription page ----------
    # "backend" is rendered as "识别引擎": this page is read by lawyers and
    # doctors as well as developers, and "引擎" is the word a non-developer knows.
    "page.transcription.title": "转写",
    "page.transcription.hint": (
        "选择要尝试的语音转文字引擎及其顺序。"
        "启动时第一个凭据有效的引擎将成为当前引擎。"
    ),

    "transcription.backend.name.openai": "OpenAI",
    "transcription.backend.name.groq": "Groq",
    "transcription.backend.name.local": "本地（Whisper）",
    "transcription.backend.hint.openai": "质量高，付费",
    "transcription.backend.hint.groq": "最快，有免费额度",
    "transcription.backend.hint.local": "离线，使用本地 CPU/GPU",

    "transcription.priority.title": "引擎优先级",
    "transcription.priority.hint": (
        "拖动即可重新排序。启动时第一个凭据有效的引擎胜出。"
    ),

    "transcription.keys.title": "API 密钥",
    "transcription.keys.hint": (
        "保存在 Windows Credential Manager（受 DPAPI 保护）。"
        "留空则跳过该引擎。"
    ),
    "transcription.keys.get_link": "获取密钥 ↗",

    # Provider console labels kept verbatim in Latin and quoted with 「」 — those
    # consoles have no Chinese UI.
    "transcription.keys.openai.label": "OpenAI 密钥",
    "transcription.keys.openai.placeholder": "输入 OpenAI API 密钥",
    "transcription.keys.openai.nudge": "← 输入你的 OpenAI 密钥",
    "transcription.keys.openai.help.title": "如何获取 OpenAI API 密钥",
    "transcription.keys.openai.help.step1": "1. 登录 platform.openai.com",
    "transcription.keys.openai.help.step2": "2. 「API keys」→「Create new secret key」",
    "transcription.keys.openai.help.step3": "3. 复制它（以「sk-…」开头）并粘贴到这里",
    "transcription.keys.openai.help.note": "OpenAI 需付费 — 请充值后使用。",
    "transcription.keys.openai.help.link": "打开 OpenAI 密钥页面",

    "transcription.keys.groq.label": "Groq 密钥",
    "transcription.keys.groq.placeholder": "输入 Groq API 密钥",
    "transcription.keys.groq.nudge": "← 输入你的 Groq 密钥",
    "transcription.keys.groq.help.title": "如何获取 Groq API 密钥（免费）",
    "transcription.keys.groq.help.step1": "1. 登录 console.groq.com",
    "transcription.keys.groq.help.step2": "2. 「API Keys」→「Create API Key」",
    "transcription.keys.groq.help.step3": "3. 复制它并粘贴到这里",
    "transcription.keys.groq.help.link": "打开 Groq 控制台",

    "transcription.models.title": "每个引擎的模型",
    "transcription.models.hint": "在该引擎处于活动状态时使用。",

    "transcription.device.title": "本地转写设备（仅用于本地引擎）",
    "transcription.device.hint": (
        "本机 Whisper 模型的运行位置。当 OpenAI 或 Groq 为当前引擎时无效 —"
        "它们在云端转写。"
    ),
    "transcription.device.label": "设备",
    "transcription.device.label.hint": "在受支持的 NVIDIA 显卡上，CUDA 明显快于 CPU。",
    "transcription.device.cpu": "CPU",
    "transcription.device.cuda": "CUDA（GPU）",

    "transcription.mic.title": "麦克风",
    "transcription.mic.hint": (
        "从哪个输入录音，以及转写前的轻度音频处理（高通滤波与电平归一化）。"
        "不会更改 ASR 模型。"
    ),
    "transcription.mic.device.label": "输入设备",
    "transcription.mic.device.hint": (
        "系统默认跟随 Windows。若录到错误设备，或使用桌面 USB 麦克风，"
        "请选择具体麦克风。"
    ),
    "transcription.mic.device.default": "系统默认",
    "transcription.enhance.label": "音频增强",
    "transcription.enhance.hint": (
        "轻度：在送入模型前略微提升轻声并抑制低频嗡声。"
        "关闭：原始录音（先前行为）。"
    ),
    "transcription.enhance.off": "关闭",
    "transcription.enhance.light": "轻度（推荐）",

    "transcription.error.priority_empty": "引擎优先级列表为空。",

    # ---------- settings: About page ----------
    "page.about.title": "关于",
    "about.version": "版本",
    "about.version.unknown": "未知",
    "about.developer": "开发者",
    "about.email": "邮箱",
    "about.website": "网站",

    # ---------- settings: Glossary page ----------
    "page.glossary.title": "术语表",
    "page.glossary.hint": (
        "公司专有术语和日常术语，让应用能识别并以规范形式写出它们。"
        "默认关闭。注意：启用 ASR 偏置或 LLM 层时，这些术语会作为请求的一部分"
        "发送给你的云服务商（OpenAI/Groq）。"
    ),
    "glossary.enable.title": "启用术语表",
    "glossary.enable.hint": "总开关。关闭 → 行为与不含此功能的版本完全一致。",

    # ---------- settings: Glossary → profession packs ----------
    "glossary.packs.title": "行业术语包",
    "glossary.packs.hint": (
        "精选术语集，让识别开箱即用地准确处理领域行话 —"
        "某一领域默认容易出错的词汇、缩写和拼写（lien、force majeure、"
        "anamnesis、ECG、merge request、idempotent）。点击某个术语包即可将其"
        "术语复制到下方的术语表中，之后可像自己输入的内容一样编辑。Pro 功能。"
    ),
    "glossary.packs.language": "术语包语言",
    "glossary.packs.language.hint": "导入术语所用的语言。",
    "glossary.packs.status.available": "有 {count} 个术语包可用 — 点击任一个即可将其术语复制到下方的框中。",
    "glossary.packs.status.locked": "行业术语包是 Pro 功能。Free 保留 {cap} 个术语生效 — 少于任何术语包的数量。",
    "glossary.packs.tooltip.adds": "最多添加 {count} 个术语。",
    "glossary.packs.tooltip.locked": "行业术语包是 Pro 功能。",
    "glossary.packs.already_loaded.title": "{pack}术语包已加载",
    # {language} is the English language name from data, hence the parentheses.
    "glossary.packs.already_loaded.text": "{language}术语包中的每个术语都已在你的术语表中 — 无需添加。",
    "glossary.packs.count.terms": "{count} 个术语",
    "glossary.packs.count.replacements": "{count} 条替换",
    "glossary.packs.count.join": "和",
    "glossary.packs.confirm.title": "加载{pack}术语包？",
    "glossary.packs.confirm.adds": "这将向你的术语表添加 {what}（{language}）。",
    "glossary.packs.confirm.skipped": "已存在的 {count} 个将被跳过。",
    "glossary.packs.confirm.editable": "它们作为可编辑或删除的普通行添加，只有在你保存时才写入磁盘。",

    # Pack name/hint are UI chrome and follow the UI locale (here, Chinese),
    # unlike the terms (which follow the "Pack language" picker) and the pack's
    # `note` on jurisdiction (written in the pack's own language).
    "glossary.packs.legal.name": "法律",
    "glossary.packs.legal.hint": "诉讼、合同和公司法词汇。",
    "glossary.packs.medical.name": "医疗",
    "glossary.packs.medical.hint": "临床记录、诊断和常见缩写。",
    "glossary.packs.it.name": "IT 与软件",
    "glossary.packs.it.hint": "工程、DevOps 和代码评审词汇。",
    "glossary.packs.finance.name": "金融与会计",
    "glossary.packs.finance.hint": "报表、估值和交易词汇。",
    "glossary.packs.sales.name": "销售与 CRM",
    "glossary.packs.sales.hint": "销售漏斗、客户触达和客户管理词汇。",

    # ---------- settings: Glossary → layers ----------
    "glossary.layers.title": "层",
    "glossary.layers.hint": "各层使用同一套术语；可单独开启或关闭每一层。",
    "glossary.layers.asr": "ASR 偏置",
    "glossary.layers.asr.hint": "让语音识别偏向你的术语（云端 prompt / 本地 hotwords）。",
    "glossary.layers.correction": "LLM 纠正（转写）",
    "glossary.layers.correction.hint": "在默认转写操作的语法纠正提示词中加入这些术语。",
    "glossary.layers.rewrite": "翻译与改写中的 LLM",
    "glossary.layers.rewrite.hint": "在翻译/改写提示词中加入这些术语（手动按钮 + 快捷键操作）。",
    "glossary.layers.fuzzy": "模糊替换（转写）",
    "glossary.layers.fuzzy.hint": "确定性地将近似词归拢到规范术语，仅限转写。",
    "glossary.layers.threshold": "模糊阈值",
    "glossary.layers.threshold.hint": "词与术语要多接近才触发模糊替换（70–100；越高越严格）。",

    # ---------- settings: Glossary → term editors ----------
    "glossary.terms.title": "术语",
    "glossary.terms.hint": "公司专有词汇，按组分列。每行一条。",
    "glossary.terms.tab.names": "名称与术语",
    "glossary.terms.tab.replacements": "替换",
    "glossary.terms.names": "名称",
    "glossary.terms.names.hint": "你的公司、产品、客户、合作伙伴、供应商。",
    # Invented company names — proper nouns, Latin in every locale.
    "glossary.terms.names.placeholder": "Acme Corp\nGlobex",
    "glossary.terms.services": "服务与术语",
    "glossary.terms.services.hint": "服务名称、套餐、领域术语。",
    # Latin brand + a natural Chinese example on the second line.
    "glossary.terms.services.placeholder": "TurboDrive\n轨道套餐",
    # A spoken (heard) Chinese form mapping to a canonical Latin term — the CJK
    # case where a term is *said* in Chinese but *written* in Latin. {sep} kept.
    "glossary.terms.replacements.placeholder": "特波驱动 {sep} TurboDrive",
    "glossary.terms.replacements.hint": (
        "明确、始终生效的修正 — 每行一条，格式为「听到的 {sep} 规范形式」。"
        "逐字应用（无模糊规则），因此用于识别稳定听错的词。"
    ),
    "glossary.terms.counter.unlimited": "{total} 个术语 — 全部生效。",
    "glossary.terms.counter.used": "已使用 {total}/{cap} 个术语 · 还可添加 {remaining} 个。",
    "glossary.terms.counter.over_free": (
        "{cap}/{total} 个术语生效 — 其余已保存但未启用。"
        "Pro 会全部启用（最多 {pro_cap} 个）。"
    ),
    "glossary.terms.counter.over_ceiling": (
        "{cap}/{total} 个术语生效 — 仅使用前 {cap} 个"
        "（更多会降低识别质量）。"
    ),

    # ---------- settings: Glossary → validation ----------
    "glossary.replacements.error.missing_sep": "第 {line} 行：缺少「{sep}」分隔符 — 请使用「听到的 {sep} 规范形式」",
    "glossary.replacements.error.empty_side": "第 {line} 行：「{sep}」两侧都不能为空",
    "glossary.replacements.error.more": "（另有 {count} 条）",
    "glossary.replacements.error.prefix": "替换：{details}",

    # ---------- settings: Custom style page ----------
    "page.customstyle.title": "自定义风格",
    "page.customstyle.hint": (
        "由「自定义」改写按钮使用。下方的指令会连同你的原文一起逐字传给模型。"
    ),
    "customstyle.preset.title": "预设",
    "customstyle.name": "风格名称",
    "customstyle.name.hint": "显示为「自定义」按钮上的提示。",
    "customstyle.name.placeholder": "可选 — 例如 学术",
    "customstyle.prompt": "指令",
    "customstyle.prompt.hint": "模型将其视为系统级指示。",
    "customstyle.prompt.placeholder": (
        "例如：以学术语体改写，使用被动语态，"
        "谨慎引用，保持术语精确。"
    ),
    "customstyle.pro_hint": (
        "✦ 编辑指令是 Pro 功能。在 Free 版中，请从下方选择一个"
        "行业模板并直接使用。"
    ),
    "customstyle.templates.title": "从模板开始",
    "customstyle.templates.hint": "点击某个行业以填充上方字段。你可以按需调整指令。",
    "customstyle.templates.tooltip": "用{name}模板填充上方字段",
    "customstyle.templates.replace.title": "替换当前指令？",
    "customstyle.templates.replace.text": "这会用{name}模板覆盖「风格名称」和「指令」字段。",

    # One .name per template, in button order. A click copies the resolved name
    # into CUSTOM_STYLE_NAME, so these are what a user ends up with.
    "customstyle.templates.lawyer.name": "律师",
    "customstyle.templates.doctor.name": "医生",
    "customstyle.templates.psychotherapist.name": "心理治疗师",
    "customstyle.templates.financial_advisor.name": "理财顾问",
    "customstyle.templates.recruiter.name": "招聘专员",
    "customstyle.templates.salesperson.name": "销售",
    "customstyle.templates.support.name": "客服",
    "customstyle.templates.insurance_agent.name": "保险代理人",
    "customstyle.templates.professional.name": "商务",
    "customstyle.templates.programmer.name": "程序员",

    # ---------- Custom style dialog (gear button, main window) ----------
    "customstyledialog.title": "自定义改写风格",
    "customstyledialog.hint": "「自定义」按钮会按下方你的指令改写原文。",
    "customstyledialog.name": "风格名称（可选）",
    "customstyledialog.name.placeholder": "例如：学术、毒舌、营销文案",
    "customstyledialog.prompt": "风格指令",
    "customstyledialog.prompt.placeholder": (
        "例如：以学术语体改写，使用被动语态，"
        "谨慎引用，保持术语精确。"
    ),
    "customstyledialog.preset_limit": "无限量保存自定义风格是 Pro 功能。",

    # ---------- settings window chrome ----------
    # "Setup" vs "Settings": the first-run window says 初始设置 so the two are
    # unmistakable.
    "settingswindow.title.setup": "Omni Verte — 初始设置",
    "settingswindow.title.settings": "Omni Verte — 设置",
    "settingswindow.nav.general": "常规",
    "settingswindow.nav.transcription": "转写",
    "settingswindow.nav.languages": "语言",
    "settingswindow.nav.custom_style": "自定义风格",
    "settingswindow.nav.glossary": "术语表",
    "settingswindow.nav.license": "许可证",
    "settingswindow.nav.about": "关于",
    "settingswindow.local_only": "仅使用本地",
    # No "&&" in Chinese — there is no ampersand to render. Natural wording.
    "settingswindow.save_start": "保存并启动",
    "settingswindow.save_apply": "保存并应用",
    "settingswindow.error.title": "无法保存",
    "settingswindow.error.apply_failed": "保存「{page}」失败：{error}",

    # ---------- settings: License page ----------
    "page.license.title": "许可证",
    "page.license.hint": "Omni Verte 可免费使用。Pro 许可证可解锁更多功能 — 详见下方。",

    "license.status.title": "状态",
    "license.status.hint": "本机当前运行的级别。",
    "license.status.level": "当前级别：{tier}",
    "license.status.key": "（密钥 {key}）",

    "license.benefit.glossary": "术语表 — 最多 200 个术语（Free：5 个）外加现成的行业术语包",
    "license.benefit.custom_styles": "自定义风格 — 创建并编辑你自己的改写风格（Free：仅模板）",
    "license.benefit.presets": "风格预设 — 想存多少存多少（Free：一个槽位）",
    "license.benefit.history": "历史 — 无限量且可搜索（Free：最近 10 条）",
    "license.benefit.builds": "签名、自动更新的版本及优先支持",

    "license.waitlist.title": "Pro 即将推出",
    "license.waitlist.hint": "Pro 尚未开售。加入等候名单，开售时你会第一时间得知 — 无需付款，无任何承诺。",
    "license.waitlist.unlocks": "Pro 可解锁：",
    "license.waitlist.button": "加入 Pro 等候名单",

    "license.benefits.unlocks": "Pro 可解锁：",
    "license.benefits.included": "你的 Pro 许可证包含：",

    "license.key.title": "许可证密钥",
    "license.hint.enter": "输入你收到的许可证密钥，然后点击「激活」。",
    "license.hint.activated": "Pro 已在本机激活。你的密钥已安全存储 — 无需再次输入。",
    "license.hint.editing": "输入新的许可证密钥。在新密钥被接受前，当前密钥仍然有效。",
    "license.button.buy": "获取许可证",
    "license.button.change_key": "使用其他密钥",
    "license.button.deactivate": "停用",
    "license.button.activate": "激活",
    "license.toast.activated": "Pro 已激活",
    "license.toast.cleared": "许可证已清除 — 恢复为 Free",

    "license.error.network": "无法连接许可证服务器。请检查网络后重试 — 你当前的状态未改变。",
    "license.error.empty_key": "请先输入许可证密钥。",
    "license.error.no_fingerprint": "无法读取本机 ID。激活需要 Windows。",
    "license.error.local": "无法在本机激活。",
    "license.error.invalid_key": "未找到该许可证密钥。请核对后重试。",
    # EN says "(Clear it there)" — a stale reference to a button now labelled
    # Deactivate. The Chinese points at the button that actually exists.
    "license.error.seat_limit": "该密钥的所有设备都在使用中。先释放一台设备（在那里停用），再在此处重新激活。",
    "license.error.rate_limit": "近期激活次数过多。请稍后再试。",
    "license.error.inactive": "此许可证已失效（被吊销、退款或过期）。",
    "license.error.refused": "许可证服务器拒绝了请求。这不是你密钥的问题 — 请重试，若持续出现请联系支持。",
    "license.error.unverified": "已激活，但无法在本机验证许可证。请联系支持。",
    "license.error.generic": "无法激活。请重试。",

    # ---------- hotkey capture (shared settings control) ----------
    "hotkeycapture.catch": "捕获按键",
    "hotkeycapture.listening": "请按一个键…",
    "hotkeycapture.tooltip": "点击后按下你想用的键 — 它会填入此字段。",

    # ---------- history kinds (Activity Feed) ----------
    "history.kind.transcription": "转写",
    "history.kind.translation": "翻译",
    "history.kind.fix": "语法纠正",
    "history.kind.casual": "随意风格改写",
    "history.kind.professional": "专业风格改写",
    "history.kind.custom": "自定义风格改写",

    # ---------- main window ----------
    "main.status.ready": "就绪",
    "main.status.recording": "正在聆听…",
    "main.status.processing": "正在转写…",
    "main.status.error": "错误",
    "main.status.loading": "正在加载模型…",
    "main.status.failed": "模型加载失败 — 检查网络，在设置中重新选择",

    # 悬浮录音指示器 (ui/rec_indicator.py) — 简短的胶囊标签。
    "indicator.recording": "聆听中",
    "indicator.processing": "转录中",
    "indicator.loading": "加载中",
    "indicator.nosignal": "无信号",

    "main.card.original.title": "最新转写",
    "main.card.result.title": "AI 结果",
    "main.card.result.placeholder": "翻译或改写后的文本将显示在此处。",
    "main.card.badge.generated": "已生成",
    "main.card.result.working": "处理中…（{label}）",

    "main.button.copy": "复制",
    "main.button.clear": "清除",
    "main.button.fix_grammar": "修正语法",
    "main.button.casual": "随意",
    "main.button.professional": "专业",
    "main.button.custom": "自定义",

    "main.pill.translate": "翻译（{primary} ↔ {secondary}）",
    "main.pill.translate.tooltip": "在 {primary} 和 {secondary} 之间翻译，自动判断方向。右键点击可更改语言。",
    "main.menu.pair": "{primary} ↔ {secondary}  （自动）",
    "main.menu.change_settings": "在设置中更改",

    "main.feed.title": "历史",

    "main.tooltip.theme.dark": "切换到深色主题",
    "main.tooltip.theme.light": "切换到浅色主题",
    "main.tooltip.settings": "打开设置",
    "main.tooltip.license": "管理你的许可证",
    "main.tooltip.no_key": "需要 OpenAI 密钥 — 通过托盘 → 设置进行设置。",
    "main.tooltip.custom.named": "改写风格：{name}",
    "main.tooltip.custom.generic": "以你的自定义风格改写",
    "main.tooltip.custom.unset": "尚未配置 — 点击以设置自定义风格",

    "main.hint.keyboard.transcribe": "按 {key} 即可听写并转写。",
    "main.hint.keyboard.translate": "按 {key} 即可听写、转写并翻译。",
    # Quotes around {style}: it may hold a user-invented style name.
    "main.hint.keyboard.custom": "按 {key} 即可听写、转写并以「{style}」风格返回。",
    "main.hint.style.casual": "随意",
    "main.hint.style.professional": "专业",
    "main.hint.style.custom": "自定义",
    "main.hint.mouse.dictate": "按{button}鼠标键即可听写并转写。",
    "main.hint.mouse.hotkeys": "在设置中设定键盘快捷键，即可翻译或按某种风格改写。",
    "main.mouse.middle": "中",
    "main.mouse.left": "左",
    "main.mouse.right": "右",

    "main.dialog.operation_failed": "操作失败",
    "main.toast.custom_style_pro": (
        "编辑自定义风格是 Pro 功能。请在 设置 → 自定义风格 中"
        "选择一个模板。"
    ),
}
