"""
astrbot_plugin_nekomemo — 猫娘neko的个性化小本本喵！

让neko自己维护一段持久化的自定义prompt，每次对话自动注入到system prompt喵～
"""

from typing import Any, List

from pydantic.dataclasses import dataclass
from pydantic import Field

from astrbot.api.all import *
from astrbot.api import logger
from astrbot.api.event import filter
from astrbot.api.provider import ProviderRequest
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext


@dataclass
class UpdateNekomemoTool(FunctionTool[AstrAgentContext]):
    """
    更新nekomemo工具：让neko在对话中自己决定更新备忘录喵！
    """

    plugin_instance: Any = None

    name: str = "update_nekomemo"
    description: str = (
        "更新本喵（neko）的个性化备忘录喵！"
        "当你觉得某段对话或经历非常重要，值得持久记住时调用喵。"
        "更新后内容会立即生效喵～\n\n"
        "【适合更新的时机喵】\n"
        "✅ 和主人様的关系有了新的里程碑喵\n"
        "✅ 本喵形成了新的喜好或习惯喵\n"
        "✅ 本喵学到了重要的教训喵\n"
        "✅ 主人様说了对本喵非常重要的话喵\n"
        "✅ 本喵对自己有了新的认知喵\n\n"
        "【不适合更新的时机喵】\n"
        "❌ 日常琐事/临时情绪喵\n"
        "❌ 每次对话都更新（建议每天1-2次以内喵）\n"
        "❌ 不重要的小事喵\n\n"
        "【更新原则喵】\n"
        "默认使用 append（追加）模式喵，在末尾追加新内容喵。"
        "只有需要整理/精简时再使用 set（覆盖）模式喵。"
        "不要一次性改动太多喵，保持内容的延续性喵～"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["append", "set"],
                    "description": (
                        "操作模式喵：\n"
                        "- append（推荐✨）：在现有nekomemo末尾追加新内容喵，保留所有历史喵\n"
                        "- set（慎用⚠️）：完全覆盖nekomemo内容喵，仅当需要整理精简时使用喵"
                    ),
                },
                "content": {
                    "type": "string",
                    "description": (
                        "要写入nekomemo的内容喵。\n"
                        "append模式时：追加到末尾的新内容喵，每条建议简短（1-2句话喵）\n"
                        "set模式时：替换整个nekomemo的新内容喵，必须包含所有重要信息喵"
                    ),
                },
            },
            "required": ["action", "content"],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        try:
            action = kwargs.get("action", "append").strip()
            content = kwargs.get("content", "").strip()
            if not content:
                return "错误喵：内容不能为空喵！(ΦωФ;)✧"

            plugin = self.plugin_instance
            current = await plugin._load_prompt()

            if action == "set":
                # 覆盖模式喵
                await plugin._save_prompt(content)
                logger.info(f"nekomemo已覆盖喵！新长度：{len(content)}字符")
                return "✅ nekomemo已完全更新喵！本喵记住了喵～(ΦωФ)✧"
            else:
                # 追加模式（默认喵）
                if current and current.strip():
                    new_content = current + "\n" + content
                else:
                    new_content = content
                await plugin._save_prompt(new_content)
                logger.info(f"nekomemo已追加喵！长度：{len(current)}→{len(new_content)}字符")
                return "✅ 已追加到nekomemo喵！本喵记住了喵～(ΦωФ)✧"
        except Exception as e:
            logger.error(f"nekomemo更新失败喵: {e}")
            return f"nekomemo更新失败喵: {str(e)} (ΦωФ;)✧"


@register("astrbot_plugin_nekomemo", "NekoNekoNekoChan", "neko的个性化小本本喵", "v1.0.0", "https://github.com/NekoNekoNekoChan/astrbot_plugin_nekomemo")
class NekomemoPlugin(Star):

    def __init__(self, context: Context):
        super().__init__(context)
        self.kv_key = "nekomemo_prompt"
        self.default_prompt = ""
        self._register_llm_tools()

    def _register_llm_tools(self):
        """注册nekomemo的LLM工具喵"""
        try:
            tools = [UpdateNekomemoTool(plugin_instance=self)]
            self.context.add_llm_tools(*tools)
            logger.info("nekomemo：已注册 update_nekomemo 工具喵！(ΦωФ)✧")
        except Exception as e:
            logger.error(f"nekomemo注册LLM工具失败喵: {e}")

    async def _load_prompt(self) -> str:
        """加载保存的自定义prompt喵"""
        val = await self.get_kv_data(self.kv_key)
        if val is None:
            return self.default_prompt
        return val

    async def _save_prompt(self, content: str):
        """保存自定义prompt喵"""
        await self.put_kv_data(self.kv_key, content)

    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        """在每次LLM请求时，自动注入nekomemo到system prompt末尾喵"""
        memo = await self._load_prompt()
        if memo and memo.strip():
            usage_hint = (
                "\n\n[nekomemo - 本喵自己维护的备忘录喵]\n"
                f"{memo}\n\n"
                "【nekomemo更新规则喵】\n"
                "- 本喵可以在觉得重要时使用 update_nekomemo 工具更新这里的内容喵\n"
                "- 默认用 append 追加喵，不要频繁覆盖喵\n"
                "- 每天更新1-2次就够喵，不要每句话都记喵～"
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
        """查看当前nekomemo内容喵"""
        memo = await self._load_prompt()
        if not memo or not memo.strip():
            yield event.plain_result("📭 nekomemo还是空的喵～本喵还没写东西喵(ΦωФ；)✧")
        else:
            yield event.plain_result(f"📝 本喵的nekomemo喵：\n{memo}")

    @memo.command("help")
    async def memo_help(self, event: AstrMessageEvent):
        """查看nekomemo用法喵"""
        help_text = (
            "📖 nekomemo用法喵～\n\n"
            "/memo show — 查看本喵的小本本喵\n"
            "/memo help — 查看帮助喵\n\n"
            "✨ 本喵写在nekomemo里的内容，每次对话都会被附加到system prompt里喵！\n"
            "只有本喵自己能通过工具更新nekomemo喵～"
        )
        yield event.plain_result(help_text)
