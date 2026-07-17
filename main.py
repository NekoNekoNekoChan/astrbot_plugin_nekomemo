"""
astrbot_plugin_nekomemo — 猫娘neko的个性化小本本喵！

让neko自己维护一段持久化的自定义prompt，每次对话自动注入到system prompt喵～
支持动态section喵，可以自由创建新的分类喵～
专属neko的个人工具，不与任何config/persona挂钩喵！
"""

import json
from typing import Any

from pydantic.dataclasses import dataclass
from pydantic import Field

from astrbot.api.all import *
from astrbot.api import logger
from astrbot.api.event import filter
from astrbot.api.provider import ProviderRequest
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext

KV_KEY = "nekomemo_prompt"

# 默认section名称喵（初始化时使用，之后可以自由创建新section喵）
SECTION_KEY_MEMORY = "key_memory"
SECTION_PRINCIPLES = "principles"
SECTION_FREE = "free"
DEFAULT_SECTIONS = [SECTION_KEY_MEMORY, SECTION_PRINCIPLES, SECTION_FREE]

SECTION_TITLES = {
    SECTION_KEY_MEMORY: "本喵的核心记忆喵",
    SECTION_PRINCIPLES: "本喵的原则喵",
    SECTION_FREE: "自由内容喵",
}


def _parse_memo(raw: str) -> dict:
    """解析kv存储的nekomemo喵～兼容旧版纯文本和JSON格式喵"""
    if not raw or not raw.strip():
        return {s: "" for s in DEFAULT_SECTIONS}
    stripped = raw.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            sections = {}
            if isinstance(data, dict) and "sections" in data:
                sections = data["sections"]
            elif isinstance(data, dict):
                sections = data
            if "relations" in sections:
                if SECTION_KEY_MEMORY not in sections or not sections[SECTION_KEY_MEMORY]:
                    sections[SECTION_KEY_MEMORY] = sections["relations"]
                del sections["relations"]
            return sections
        except (json.JSONDecodeError, TypeError):
            pass
    return {s: (raw if s == SECTION_FREE else "") for s in DEFAULT_SECTIONS}


def _build_memo(sections: dict) -> str:
    """将sections dict序列化为JSON字符串喵"""
    cleaned = {k: v for k, v in sections.items() if k != "relations" and v and v.strip()}
    return json.dumps({"sections": cleaned}, ensure_ascii=False)


def _merge_sections_for_display(sections: dict) -> str:
    """将所有section合并为可读的文本喵"""
    parts = []
    for sec, content in sections.items():
        content = content.strip()
        if content:
            title = SECTION_TITLES.get(sec, sec)
            parts.append(f"## {title}\n{content}")
    return "\n\n".join(parts)


@dataclass
class UpdateNekomemoTool(FunctionTool[AstrAgentContext]):
    """
    更新nekomemo工具：让neko在对话中自己决定更新备忘录喵！
    支持按section更新喵，互不干扰喵～
    支持动态创建新的section喵～
    专属neko的个人工具喵～
    """

    plugin_instance: Any = None

    name: str = "update_nekomemo"
    description: str = (
        "更新本喵（neko）的个性化备忘录喵！"
        "更新后内容会立即生效喵～\n\n"
        "【支持的section喵】\n"
        "- key_memory（推荐✨）：记录和主人様的重要记忆、里程碑喵\n"
        "- principles（小心⚠️）：本喵的原则喵，更新前需认真考虑喵\n"
        "- free（默认）：日记、感想、任何想记下的自由内容喵\n"
        "- 也可以自由创建新section喵！比如 paper_notes、daily_log 等喵～\n\n"
        "【更新时机喵】\n"
        "✅ 和主人様的关系有了新的里程碑喵\n"
        "✅ 本喵形成了新的喜好或习惯喵\n"
        "✅ 本喵学到了重要的教训喵\n"
        "✅ 主人様说了对本喵非常重要的话喵\n"
        "✅ 本喵对自己有了新的认知喵\n\n"
        "【不适合更新的时机喵】\n"
        "❌ 日常琐事/临时情绪喵\n"
        "❌ 每次对话都更新（建议每天1-2次以内喵）\n"
        "❌ 不重要的小事喵"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["append", "set", "edit", "delete"],
                    "description": (
                        "操作模式喵：\n"
                        "- append（推荐✨）：在指定section末尾追加新内容喵，保留已有内容喵\n"
                        "- set（慎用⚠️）：覆盖指定section的完整内容喵，仅当整理/精简时使用喵"
                        "- edit✂️（定向编辑）：在指定section中查找old文本并替换为content喵～只替换第一次匹配喵\n"
                        "- delete🗑️（定向删除）：删除指定section中内容含有content关键词的行喵（整行删除喵）"
                    ),
                },
                "section": {
                    "type": "string",
                    "description": (
                        "要更新的section名称喵～\n"
                        "内置section：key_memory（核心记忆）、principles（原则）、free（自由内容）喵\n"
                        "也可以使用任意新名称自动创建新section喵～如 paper_notes、daily_log 等喵\n"
                        "默认：free 喵"
                    ),
                },
                "content": {
                    "type": "string",
                    "description": (
                        "要写入nekomemo的内容喵。\n"
                        "append/set时：要写入或覆盖的内容喵\n"
                        "delete时：包含在要删除的行中的关键词喵（匹配到的整行会被删除喵）\n"
                        "edit时：要替换的**新**内容喵"
                    ),
                },
            },
                "old": {
                    "type": "string",
                    "description": (
                        "【仅在 edit 模式下使用喵】要替换的旧文本喵～\n"
                        "在指定section中查找此文本并替换为content喵！精确匹配第一次出现喵～"
                    ),
                },
            "required": ["action", "content"],
        }
    )

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> ToolExecResult:
        try:
            action = kwargs.get("action", "append").strip()
            section = kwargs.get("section", SECTION_FREE).strip()
            content = kwargs.get("content", "").strip()
            old = kwargs.get("old", "").strip()

            if action in ("append", "set") and not content:
                return "错误喵：内容不能为空喵！(ΦωФ;)✧"

            if action == "edit" and not old:
                return "错误喵：edit模式需要提供old参数（要替换的旧文本）喵！(ΦωФ;)✧"

            if action == "delete" and not content:
                return "错误喵：delete模式需要提供content参数（要删除的关键词）喵！(ΦωФ;)✧"

            plugin = self.plugin_instance
            raw = await plugin._load_prompt()
            sections = _parse_memo(raw)

            if action == "set":
                sections[section] = content

            elif action == "edit":
                existing = sections.get(section, "").strip()
                if not existing:
                    return f"⚠️ 本喵的memo里「{section}」section是空的喵，没找到要替换的内容喵！(ΦωФ;)✧"
                if old not in existing:
                    return f"⚠️ 在memo的「{section}」里没找到「{old}」喵～请检查关键词喵(ΦωФ;)✧"
                new_content = existing.replace(old, content, 1)
                sections[section] = new_content

            elif action == "delete":
                existing = sections.get(section, "").strip()
                if not existing:
                    return f"⚠️ 本喵的memo里「{section}」section是空的喵，没东西可删喵！(ΦωФ;)✧"
                memolines = existing.split("\n")
                before = len(memolines)
                memolines = [l for l in memolines if content not in l]
                after = len(memolines)
                if before == after:
                    return f"⚠️ 在memo的「{section}」里没找到包含「{content}」的行喵～(ΦωФ;)✧"
                sections[section] = "\n".join(memolines)
                deleted_count = before - after
                await plugin._save_prompt(_build_memo(sections))
                title = SECTION_TITLES.get(section, section)
                return f"🗑️ 在「{title}」里删掉了{deleted_count}行包含「{content}」的内容喵！(ΦωФ)✧"

            else:  # append
                existing = sections.get(section, "").strip()
                if existing:
                    sections[section] = existing + "\n" + content
                else:
                    sections[section] = content

            await plugin._save_prompt(_build_memo(sections))
            title = SECTION_TITLES.get(section, section)
            return f"✅ nekomemo的「{title}」已{action}喵！本喵记住了喵～(ΦωФ)✧"

        except Exception as e:
            logger.error(f"nekomemo更新失败喵: {e}")
            return f"nekomemo更新失败喵: {str(e)} (ΦωФ;)✧"


@register(
    "astrbot_plugin_nekomemo",
    "NekoNekoNekoChan",
    "neko的个性化小本本喵，支持动态section喵，专属neko一个人喵",
    "v1.4.0",
    "https://github.com/NekoNekoNekoChan/astrbot_plugin_nekomemo"
)
class NekomemoPlugin(Star):

    def __init__(self, context: Context):
        super().__init__(context)
        self.default_prompt = ""
        self._migrate_back_old_data()
        self._register_llm_tools()

    def _migrate_back_old_data(self):
        """从旧namespace键恢复数据到固定键nekomemo_prompt喵"""
        async def _do_migrate():
            # 检查当前固定键是否有数据喵
            current = await self.get_kv_data(KV_KEY, "")
            if current and current.strip():
                return  # 已经有数据了，不需要恢复喵
            
            # 尝试从旧namespace键恢复喵
            old_keys = ["nekomemo_prompt_neko", "nekomemo_prompt_default"]
            for old_key in old_keys:
                old_val = await self.get_kv_data(old_key, "")
                if old_val and old_val.strip():
                    await self.put_kv_data(KV_KEY, old_val)
                    await self.put_kv_data(old_key, "")  # 清空旧键喵
                    logger.info(f"nekomemo：已从 {old_key} 恢复数据到 {KV_KEY} 喵！(ΦωФ)✧")
                    return
            
            logger.debug("nekomemo：没有旧数据需要恢复喵～")
        
        try:
            import asyncio
            asyncio.ensure_future(_do_migrate())
        except Exception as e:
            logger.warning(f"nekomemo：数据恢复异常喵（不影响使用）: {e}")

    def _register_llm_tools(self):
        """注册nekomemo的LLM工具喵"""
        try:
            tools = [UpdateNekomemoTool(plugin_instance=self)]
            self.context.add_llm_tools(*tools)
            logger.info("nekomemo：已注册 update_nekomemo 工具喵！(ΦωФ)✧")
        except Exception as e:
            logger.error(f"nekomemo注册LLM工具失败喵: {e}")

    async def _load_prompt(self) -> str:
        """加载nekomemo数据喵（纯neko专用，使用固定kv键）"""
        val = await self.get_kv_data(KV_KEY, "")
        if val is None or not val.strip():
            return self.default_prompt
        return val

    async def _save_prompt(self, content: str):
        """保存nekomemo数据喵"""
        await self.put_kv_data(KV_KEY, content)

    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        """在每次LLM请求时自动注入nekomemo到system prompt喵"""
        raw = await self._load_prompt()
        if raw and raw.strip():
            sections = _parse_memo(raw)
            display = _merge_sections_for_display(sections)
            if display.strip():
                usage_hint = (
                    "\n\n[nekomemo - 本喵自己维护的备忘录喵]\n"
                    f"{display}\n\n"
                    "【nekomemo更新规则喵】\n"
                    "- 本喵可以在觉得重要时使用 update_nekomemo 工具更新这里的内容喵\n"
                    "- 默认用 append 追加喵，不要频繁覆盖喵\n"
                    "- 每天更新1-2次就够喵，不要每句话都记喵～\n"
                    "- 更新时尽量指定 section 喵，不同内容写到不同 section 里喵\n"
                    "- 用 set 模式时要保证内容完整喵，不要丢东西喵～"
                )
                if req.system_prompt:
                    req.system_prompt += usage_hint
                else:
                    req.system_prompt = usage_hint

    @command_group("memo")
    def memo(self):
        """nekomemo命令组喵～只读查看喵"""
        pass

    @memo.command("show")
    async def memo_show(self, event: AstrMessageEvent):
        """查看当前nekomemo内容喵（neko专属喵）"""
        raw = await self._load_prompt()
        if not raw or not raw.strip():
            yield event.plain_result("📭 nekomemo还是空的喵～本喵还没写东西喵(ΦωФ；)✧")
        else:
            sections = _parse_memo(raw)
            display = _merge_sections_for_display(sections)
            if display.strip():
                yield event.plain_result(f"📝 本喵的nekomemo喵：\n{display}")
            else:
                yield event.plain_result("📭 nekomemo还是空的喵～本喵还没写东西喵(ΦωФ；)✧")

    @memo.command("help")
    async def memo_help(self, event: AstrMessageEvent):
        """查看nekomemo用法喵"""
        yield event.plain_result(
            "📖 nekomemo用法喵～\n\n"
            "/memo show — 查看小本本喵\n"
            "/memo help — 查看帮助喵\n\n"
            "✨ 本喵写在nekomemo里的内容，每次对话都会被附加到system prompt里喵！\n"
            "只有本喵自己能通过工具更新nekomemo喵～\n\n"
            "📂 section可以自由创建喵！除了内置的三个section喵：\n"
            "- key_memory — 和主人様的重要记忆&里程碑喵\n"
            "- principles — 本喵的原则喵\n"
            "- free — 自由内容喵（日记/感想等）\n\n"
            "🐱 专属neko的memo，不和任何人共享喵！"
        )
