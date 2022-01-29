from asyncio import TimeoutError
import datetime

from discord import Embed
from discord_slash import SlashContext
from discord_slash.cog_ext import cog_slash as slash_command
from discord_components import Select, SelectOption
from discord_slash_components_bridge import ComponentContext

from my_utils import AsteroidBot, get_content, Cog


class Help(Cog):
    def __init__(self, bot: AsteroidBot):
        self.bot = bot
        self.hidden = True
        self.name = "Help"

    @slash_command(name="help", description="Show all bot's commands")
    async def help_command(self, ctx: SlashContext):
        await ctx.defer()

        lang = self.bot.get_guild_bot_lang(ctx.guild_id)
        content = get_content("HELP_COMMAND", lang)

        components = self._init_components(ctx, content)
        embeds = self._init_embeds(ctx, content, lang)
        message = await ctx.send(embed=embeds[0], components=components)

        while True:
            try:
                interaction: ComponentContext = await self.bot.wait_for(
                    "select_option",
                    check=lambda inter: inter.author_id == ctx.author_id
                    and inter.message.id == message.id,
                    timeout=60,
                )
            except TimeoutError:
                return await message.edit(components=[])

            value = interaction.values[0]

            if value == "main_page":
                embed = embeds[0]
            else:
                for embed in embeds:
                    if embed.title.startswith(value):
                        break
            await interaction.edit_origin(embed=embed)

    @staticmethod
    def _cog_is_private(ctx: SlashContext, cog: Cog):
        return cog.private_guild_id and ctx.guild_id not in cog.private_guild_id

    def _init_components(self, ctx: SlashContext, content: dict):
        options = [SelectOption(label="Main Page", value="main_page", emoji="🏠")]

        for _cog in self.bot.cogs:
            cog = self.bot.cogs[_cog]
            if cog.hidden:
                continue
            if self._cog_is_private(ctx, cog):
                continue

            emoji = cog.emoji
            if isinstance(emoji, int):
                emoji = self.bot.get_emoji(emoji)

            options.append(SelectOption(label=_cog, value=_cog, emoji=emoji))

        return [Select(placeholder=content["SELECT_MODULE_TEXT"], options=options)]

    def _init_embeds(self, ctx: SlashContext, content: dict, guild_language: str):
        translated_commands = None
        if guild_language != "en":
            translated_commands = get_content("TRANSLATED_COMMANDS", guild_language)
        commands_data = self._get_commands_data()
        embeds = [self._get_main_menu(ctx, content)]

        for _cog in self.bot.cogs:
            cog = self.bot.cogs[_cog]
            if cog.hidden:
                continue
            if self._cog_is_private(ctx, cog):
                continue

            embed = Embed(
                title=f"{_cog} | Asteroid Bot",
                description="",
                timestamp=datetime.datetime.utcnow(),
                color=0x2F3136,
            )
            embed.set_footer(
                text=content["REQUIRED_BY_TEXT"].format(user=ctx.author),
                icon_url=ctx.author.avatar_url,
            )
            embed.set_thumbnail(url=ctx.bot.user.avatar_url)

            for _base_command in commands_data[_cog]:
                base_command = commands_data[_cog][_base_command]
                for _group in base_command:
                    if _group == "command_description":
                        continue
                    group = base_command[_group]
                    if group.get("has_subcommand_group") is None:
                        for _command_name in group:
                            command = group[_command_name]
                            option_line = self.get_options(command)
                            command_description = (
                                translated_commands.get(
                                    f"{_base_command}_{_group}_{_command_name}".upper(),
                                    command["description"],
                                )
                                if translated_commands
                                else command["description"]
                            )
                            embed.description += (
                                f"`/{_base_command} {_group} {_command_name}{option_line}`\n "
                                f"*{content['DESCRIPTION_TEXT']}* {command_description} \n"
                            )
                    else:
                        option_line = self.get_options(group)
                        command_description = (
                            translated_commands.get(
                                f"{_base_command}_{_group}".upper(),
                                group["description"],
                            )
                            if translated_commands
                            else group["description"]
                        )
                        embed.description += (
                            f"`/{_base_command} {_group}{option_line}`\n "
                            f"*{content['DESCRIPTION_TEXT']}* {command_description} \n"
                        )
            embeds.append(embed)
        return embeds

    def _get_main_menu(self, ctx: SlashContext, content: dict) -> Embed:
        embed = Embed(
            title="Help | Asteroid Bot",
            timestamp=datetime.datetime.utcnow(),
            color=0x2F3136,
        )
        embed.add_field(
            name=content["INFORMATION_TEXT"],
            value=content["INFORMATION_CONTENT_TEXT"],
            inline=False,
        )
        embed.set_thumbnail(url=ctx.bot.user.avatar_url)
        embed.set_footer(
            text=content["REQUIRED_BY_TEXT"].format(user=ctx.author),
            icon_url=ctx.author.avatar_url,
        )

        cogs = ""
        for _cog in self.bot.cogs:
            cog = self.bot.cogs[_cog]
            if cog.hidden:
                continue
            if cog.private_guild_id and ctx.guild_id not in cog.private_guild_id:
                continue
            cogs += f"**» {_cog}**\n"

        embed.add_field(name=content["PLUGINS_TEXT"], value=cogs)
        return embed

    @staticmethod
    def get_options(command) -> str:
        options = command["options"]
        option_line = ""
        if options is None:
            return option_line
        for _option in options:
            option_name = _option["name"]
            option_line += (
                f" [{option_name}]" if _option["required"] else f" ({option_name})"
            )
        return option_line

    def _get_commands_data(self) -> dict:
        commands_data = self._get_subcommands_data()
        _commands = self.bot.slash.commands
        for _command in _commands:
            if _command == "context":
                continue
            command = _commands[_command]
            cog = command.cog.name
            if cog not in commands_data:
                commands_data[cog] = {}
            if _command in commands_data[cog]:
                continue
            commands_data[cog][_command] = {"command_description": command.description}

        return commands_data

    def _get_subcommands_data(self) -> dict:
        commands_data = {}
        _subcommands = self.bot.slash.subcommands
        for _slash_command in _subcommands:
            command = _subcommands[_slash_command]
            for _subcommand in command:
                subcommand = command[_subcommand]
                if isinstance(subcommand, dict):
                    for _group in subcommand:
                        group = subcommand[_group]
                        self._append_subcommand(commands_data, group)
                else:
                    self._append_subcommand(commands_data, subcommand)
        return commands_data

    @staticmethod
    def _append_subcommand(commands_data, command):
        cog = command.cog.name
        if cog not in commands_data:
            commands_data[cog] = {}
        if command.base not in commands_data[cog]:
            commands_data[cog][command.base] = {}

        has_subcommand_group = command.subcommand_group is not None
        if has_subcommand_group:
            if command.subcommand_group not in commands_data[cog][command.base]:
                commands_data[cog][command.base][command.subcommand_group] = {}
            commands_data[cog][command.base][command.subcommand_group][command.name] = {
                "description": command.description,
                "options": command.options,
            }
        else:
            commands_data[cog][command.base][command.name] = {
                "has_subcommand_group": False,
                "description": command.description,
                "options": command.options,
            }


def setup(bot):
    bot.add_cog(Help(bot))
