from typing import List

from discord import Forbidden, Member, NotFound, Role, TextChannel
from discord.ext.commands import BadArgument
from discord_slash import (
    ActionRow,
    AutoCompleteContext,
    Button,
    ButtonStyle,
    ComponentContext,
    ComponentMessage,
    Select,
    SelectOption,
    SlashCommandOptionType,
    SlashContext,
)
from discord_slash.cog_ext import cog_subcommand as slash_subcommand
from discord_slash.utils.manage_commands import create_choice, create_option
from utils import (
    AsteroidBot,
    Cog,
    GuildData,
    bot_owner_or_permissions,
    cog_is_enabled,
    errors,
    get_content,
    is_enabled,
)


class AutoRole(Cog):
    def __init__(self, bot: AsteroidBot):
        self.bot = bot
        self.name = "AutoRole"
        self.emoji = "✨"

    # ON JOIN ROLE
    @Cog.listener()
    @cog_is_enabled()
    async def on_member_join(self, member: Member):
        if member.bot:
            return

        guild_data = await self.bot.get_guild_data(member.guild.id)
        on_join_roles = guild_data.configuration.on_join_roles
        if not on_join_roles:
            return
        guild = member.guild
        for role_id in on_join_roles:
            role: Role = guild.get_role(role_id)
            await member.add_roles(role)

    @Cog.listener(name="on_autocomplete")
    @cog_is_enabled()
    async def autorole_select_autocomplete(self, ctx: AutoCompleteContext):
        if ctx.name != "autorole":
            return

        guild_data = await self.bot.get_guild_data(ctx.guild_id)
        autoroles = guild_data.autoroles
        choices = []
        match ctx.focused_option:
            case "name":
                _type = (
                    ctx.subcommand_group
                    if ctx.subcommand_group is not None
                    else ctx.options.get("type")
                )
                choices = [
                    create_choice(name=autorole.name, value=autorole.name)
                    for autorole in autoroles
                    if ctx.user_input in autorole.name and autorole.autorole_type == _type
                ]
            case "option":
                autorole = guild_data.get_autorole(ctx.options.get("name"))
                if autorole and autorole.autorole_type == "dropdown":
                    select_options = [option["label"] for option in autorole.component["options"]]
                    choices = [
                        create_choice(name=option_name, value=option_name)
                        for option_name in select_options
                        if ctx.user_input in option_name
                    ]
            case "role":
                on_join_roles = [
                    ctx.guild.get_role(role_id)
                    for role_id in guild_data.configuration.on_join_roles
                ]
                choices = [
                    create_choice(name=role.name, value=str(role.id))
                    for role in on_join_roles
                    if ctx.user_input in role.name
                ]
            case "label":
                autorole = guild_data.get_autorole(ctx.options.get("name"))
                if autorole and autorole.autorole_type == "button":
                    labels = self.get_autorole_labels(autorole.component)
                    choices = [create_choice(name=label, value=label) for label in labels]

        await ctx.populate(choices[:25])

    def get_autorole_labels(self, autorole_components):
        labels = []
        for row in autorole_components:
            if row["type"] == 1:
                for component in row["components"]:
                    if component["type"] == 2:
                        if component["label"] is None:
                            labels.append(component["emoji"]["name"])
                        else:
                            labels.append(component["label"])
        return labels

    @slash_subcommand(
        base="autorole",
        subcommand_group="on_join",
        name="add",
        description="Adds a new on join role",
        base_dm_permission=False,
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_on_join_add(self, ctx: SlashContext, role: Role):
        guild_data = await self.bot.get_guild_data(ctx.guild_id)
        await guild_data.configuration.add_on_join_role(role.id)

        content: dict = get_content("AUTOROLE_ON_JOIN", guild_data.configuration.language)
        await ctx.send(content["ROLE_ADDED_TEXT"].format(role=role.mention))

    @slash_subcommand(
        base="autorole",
        subcommand_group="on_join",
        name="remove",
        description="Removes on join role",
        options=[
            create_option(
                name="role",
                description="Role which gives when member has joined to server",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                autocomplete=True,
            )
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_on_join_remove(self, ctx: SlashContext, role: str):
        if not role.isdecimal:
            raise BadArgument
        guild_data = await self.bot.get_guild_data(ctx.guild_id)
        await guild_data.configuration.remove_on_join_role(int(role))

        content: dict = get_content("AUTOROLE_ON_JOIN", guild_data.configuration.language)
        await ctx.send(content["ROLE_REMOVED_TEXT"].format(role="<@{role}>"))

    # SELECT ROLE

    @Cog.listener()
    @cog_is_enabled()
    async def on_select_option(self, ctx: ComponentContext):
        if ctx.custom_id != "autorole_select":
            return

        member = ctx.author
        values = ctx.selected_options
        added_roles = []
        removed_roles = []
        forbidden_roles = []

        for _role in values:
            role: Role = ctx.guild.get_role(int(_role))
            try:
                await self.__add_remove_role(member, role)
            except Forbidden:
                forbidden_roles.append(f"<@&{_role}>")
            else:
                if role in member.roles:
                    removed_roles.append(f"<@&{_role}>")
                else:
                    added_roles.append(f"<@&{_role}>")

        lang = await self.bot.get_guild_bot_lang(ctx.guild_id)
        content: dict = get_content("AUTOROLE_DROPDOWN", lang)
        message_content = ""
        if added_roles:
            message_content += content["ADDED_ROLES_TEXT"] + ", ".join(added_roles)
        if removed_roles:
            message_content += content["REMOVED_ROLES_TEXT"] + ", ".join(removed_roles)
        if forbidden_roles:
            message_content += content["FORBIDDEN_ROLES_TEXT"] + ", ".join(forbidden_roles)

        await ctx.send(content=message_content, hidden=True)

    @staticmethod
    async def __add_remove_role(member: Member, role: Role):
        if role in member.roles:
            await member.remove_roles(role)
        else:
            await member.add_roles(role)

    @slash_subcommand(
        base="autorole",
        subcommand_group="dropdown",
        name="create",
        description="Creating new dropdown",
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_dropdown_create(
        self,
        ctx: SlashContext,
        name: str,
        message_content: str,
        placeholder: str = None,
    ):
        guild_data = await self.bot.get_guild_data(ctx.guild_id)
        autorole = guild_data.get_autorole(name)
        if autorole is not None:
            raise errors.AutoRoleAlredyExists

        content: dict = get_content("AUTOROLE_DROPDOWN", guild_data.configuration.language)
        select = Select(
            placeholder=placeholder if placeholder is not None else content["NO_OPTIONS_TEXT"],
            options=[SelectOption(label="None", value="None")],
            disabled=True,
            custom_id="autorole_select",
        )

        message = await ctx.channel.send(content=message_content, components=[select])  # type: ignore
        await ctx.send(content["CREATED_DROPDOWN_TEXT"], hidden=True)

        await guild_data.add_autorole(
            name=name,
            content=message_content,
            channel_id=ctx.channel.id,
            message_id=message.id,
            autorole_type="dropdown",
            component=select.to_dict(),
        )

    @slash_subcommand(
        base="autorole",
        subcommand_group="dropdown",
        name="add_option",
        description="Adding role to dropdown",
        options=[
            create_option(
                name="name",
                description="The name of dropdown",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                autocomplete=True,
            ),
            create_option(
                name="option_name",
                description="The name of option",
                option_type=SlashCommandOptionType.STRING,
                required=True,
            ),
            create_option(
                name="role",
                description="Role for option",
                option_type=SlashCommandOptionType.ROLE,
                required=True,
            ),
            create_option(
                name="emoji",
                description="The emoji for option",
                option_type=SlashCommandOptionType.STRING,
                required=False,
            ),
            create_option(
                name="description",
                description="The description of option",
                option_type=SlashCommandOptionType.STRING,
                required=False,
            ),
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_dropdown_add_option(
        self,
        ctx: SlashContext,
        name: str,
        option_name: str,
        role: Role,
        emoji: str = None,
        description: str = None,
    ):
        guild_data = await self.bot.get_guild_data(ctx.guild_id)
        content: dict = get_content("AUTOROLE_DROPDOWN", guild_data.configuration.language)

        autorole, select_component, original_message = await self.check_dropdown(
            ctx, guild_data, name
        )

        if len(select_component.options) == 25:
            raise errors.OptionsOverKill

        if emoji:
            emoji = self.get_emoji(emoji)

        if select_component.options[0].label == "None":
            select_component._options = []
            select_component.disabled = False
            if select_component.placeholder == content["NO_OPTIONS_TEXT"]:
                select_component.placeholder = content["SELECT_ROLE_TEXT"]

        select_component.options.append(
            SelectOption(
                label=option_name,
                value=f"{role.id}",
                emoji=emoji,
                description=description,
            )
        )

        select_component.max_values = len(select_component.options)
        await original_message.edit(components=[select_component])
        await ctx.send(content["ROLE_ADDED_TEXT"], hidden=True)

        await autorole.modify(component=select_component.to_dict())

    @slash_subcommand(
        base="autorole",
        subcommand_group="dropdown",
        name="remove_option",
        description="Removing role from dropdown",
        options=[
            create_option(
                name="name",
                description="The name of dropdown",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                autocomplete=True,
            ),
            create_option(
                name="option",
                description="Option of dropdown",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                autocomplete=True,
            ),
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_dropdown_remove_role(self, ctx: SlashContext, name: str, option: str):
        guild_data = await self.bot.get_guild_data(ctx.guild_id)
        content: dict = get_content("AUTOROLE_DROPDOWN", guild_data.configuration.language)

        autorole, select_component, original_message = await self.check_dropdown(
            ctx, guild_data, name
        )

        select_options = select_component.options
        for _option in select_options:
            if _option.label == option:
                option_index = select_options.index(_option)
                del select_options[option_index]
                break
        else:
            raise errors.OptionNotFound

        if not select_options:
            raise errors.OptionLessThanOne

        select_component.max_values = len(select_options)
        await original_message.edit(components=[select_component])
        await ctx.send(content["ROLE_REMOVED_TEXT"], hidden=True)

        await autorole.modify(component=select_component.to_dict())

    @slash_subcommand(
        base="autorole",
        subcommand_group="dropdown",
        name="set_status",
        description="Set up status on dropdown",
        options=[
            create_option(
                name="name",
                description="The name of dropdown",
                required=True,
                option_type=SlashCommandOptionType.STRING,
                autocomplete=True,
            ),
            create_option(
                name="status",
                description="status of dropdown",
                required=True,
                option_type=SlashCommandOptionType.STRING,
                choices=[
                    create_choice(name="enable", value="enable"),
                    create_choice(name="disable", value="disable"),
                ],
            ),
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_dropdown_set_status(self, ctx: SlashContext, name: str, status: str):
        guild_data = await self.bot.get_guild_data(ctx.guild_id)
        content: dict = get_content("AUTOROLE_DROPDOWN", guild_data.configuration.language)

        _, select_component, original_message = await self.check_dropdown(ctx, guild_data, name)

        select_component.disabled = status == "disable"
        message_content = (
            content["DROPDOWN_ENABLED_TEXT"]
            if status == select_component.disabled
            else content["DROPDOWN_DISABLED_TEXT"]
        )

        await original_message.edit(components=[select_component])
        await ctx.send(message_content, hidden=True)

    @slash_subcommand(
        base="autorole",
        name="copy",
        description="Creates a autorole copy",
        options=[
            create_option(
                name="type",
                description="The type of autorole",
                required=True,
                option_type=SlashCommandOptionType.STRING,
                choices=[
                    create_choice(name=autorole_type, value=autorole_type)
                    for autorole_type in ["dropdown", "button"]
                ],
            ),
            create_option(
                name="name",
                description="The name of autorole to copy",
                required=True,
                option_type=SlashCommandOptionType.STRING,
                autocomplete=True,
            ),
            create_option(
                name="new_name",
                description="The name of autorole",
                required=True,
                option_type=SlashCommandOptionType.STRING,
            ),
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_copy(self, ctx: SlashContext, type: str, name: str, new_name: str):
        def get_components_from_json(components: List[dict]):
            _components = [ActionRow.from_json(row) for row in components]
            return _components

        await ctx.defer(hidden=True)
        guild_data = await self.bot.get_guild_data(ctx.guild_id)
        autorole_obj = await self.__base_autorole_check(
            ctx, guild_data, name, type, return_message=False
        )
        message = await ctx.channel.send(
            content=autorole_obj.content,
            components=get_components_from_json(autorole_obj.component),  # type: ignore
        )
        await guild_data.add_autorole(
            name=new_name,
            channel_id=ctx.channel_id,
            content=autorole_obj.content,
            message_id=message.id,
            autorole_type=type,
            component=autorole_obj.component,
        )
        content: dict = get_content("AUTOROLE_BASE", guild_data.configuration.language)
        await ctx.send(content["SUCCESSFULLY_COPIED"])

    @slash_subcommand(
        base="autorole",
        name="delete",
        description="Deletes autorole from database. Doesn't deletes message!",
        options=[
            create_option(
                name="type",
                description="The type of autorole",
                required=True,
                option_type=SlashCommandOptionType.STRING,
                choices=[
                    create_choice(name=autorole_type, value=autorole_type)
                    for autorole_type in ["dropdown", "button"]
                ],
            ),
            create_option(
                name="name",
                description="The name of autorole to copy",
                required=True,
                option_type=SlashCommandOptionType.STRING,
                autocomplete=True,
            ),
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_delete(
        self, ctx: SlashContext, type: str, name: str
    ):  # `type` for better user UX exp but I don't need this lol.
        guild_data = await self.bot.get_guild_data(ctx.guild_id)
        autoroles = guild_data.autoroles
        if not autoroles:
            raise errors.NotSavedAutoRoles
        autorole = guild_data.get_autorole(name)
        if autorole is None:
            raise errors.AutoRoleNotFound

        await guild_data.remove_autorole(name)
        content: dict = get_content("AUTOROLE_BASE", guild_data.configuration.language)
        await ctx.send(content["AUTOROLE_DELETED"])

    @slash_subcommand(
        base="autorole",
        name="add_role_to_everyone",
        description="Adds role to everyone member on server",
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_add_role_to_everyone(self, ctx: SlashContext, role: Role):
        await ctx.defer()
        for member in ctx.guild.members:
            if role not in member.roles:
                await member.add_roles(role)
        await ctx.send("☑️", hidden=True)

    @slash_subcommand(
        base="autorole",
        name="remove_role_from_everyone",
        description="Removes role from everyone member on server",
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_remove_role_from_everyone(self, ctx: SlashContext, role: Role):
        await ctx.defer()
        for member in ctx.guild.members:
            if role in member.roles:
                await member.remove_roles(role)
        await ctx.send("☑️", hidden=True)

    # Button AutoRole
    @Cog.listener()
    @cog_is_enabled()
    async def on_button_click(self, ctx: ComponentContext):
        if not ctx.custom_id.startswith("autorole_button"):
            return
        content = get_content(
            "AUTOROLE_BUTTON", lang=await self.bot.get_guild_bot_lang(ctx.guild_id)
        )
        role_id = ctx.custom_id.split("|")[1]
        role = ctx.guild.get_role(int(role_id))
        try:
            await self.__add_remove_role(ctx.author, role)
        except Forbidden:
            return await ctx.send(
                content["FORBIDDEN_ROLE_TEXT"].format(f"<@&{role_id}>"), hidden=True
            )

        if role in ctx.author.roles:
            await ctx.send(content["ROLE_REMOVED_TEXT"].format(f"<@&{role_id}>"), hidden=True)
        else:
            await ctx.send(content["ROLE_ADDED_TEXT"].format(f"<@&{role_id}>"), hidden=True)

    @slash_subcommand(
        base="autorole",
        subcommand_group="button",
        name="create",
        description="Send a message for adding buttons",
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_button_create(self, ctx: SlashContext, name: str, message_content: str):
        await ctx.defer(hidden=True)

        guild_data = await self.bot.get_guild_data(ctx.guild_id)
        autorole = guild_data.get_autorole(name)
        if autorole is not None:
            raise errors.AutoRoleAlredyExists

        message = await ctx.channel.send(message_content)
        await guild_data.add_autorole(
            name=name,
            content=message_content,
            autorole_type="button",
            channel_id=ctx.channel.id,
            message_id=message.id,
            component={},
        )
        content = get_content("AUTOROLE_BUTTON", guild_data.configuration.language)
        await ctx.send(content["AUTOROLE_CREATED"], hidden=True)

    @slash_subcommand(
        base="autorole",
        subcommand_group="button",
        name="add_role",
        description="Adds a new button with role",
        options=[
            create_option(
                name="name",
                description="The name of group of buttons",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                autocomplete=True,
            ),
            create_option(
                name="role",
                description="Role",
                option_type=SlashCommandOptionType.ROLE,
                required=True,
            ),
            create_option(
                name="label",
                description="The label of button",
                option_type=SlashCommandOptionType.STRING,
                required=False,
            ),
            create_option(
                name="style",
                description="The style or color of button",
                option_type=SlashCommandOptionType.INTEGER,
                required=False,
                choices=[
                    create_choice(name="Blue", value=ButtonStyle.blue.value),
                    create_choice(name="Gray", value=ButtonStyle.gray.value),
                    create_choice(name="Green", value=ButtonStyle.green.value),
                    create_choice(name="Red", value=ButtonStyle.red.value),
                ],
            ),
            create_option(
                name="emoji",
                description="The emoji of button",
                option_type=SlashCommandOptionType.STRING,
                required=False,
            ),
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_button_add_role(
        self,
        ctx: SlashContext,
        name: str,
        role: Role,
        label: str = None,
        style: int = None,
        emoji: str = None,
    ):
        await ctx.defer(hidden=True)
        guild_data = await self.bot.get_guild_data(ctx.guild_id)
        content = get_content("AUTOROLE_BUTTON", guild_data.configuration.language)
        if not label and not emoji:
            raise errors.LabelOrEmojiRequired

        autorole, original_message = await self.check_buttons(ctx, guild_data, name)

        original_components = original_message.components
        for action_row in original_components:
            for button in action_row:
                if str(role.id) in button.custom_id:  # type: ignore
                    raise errors.DuplicateRole

        button = Button(
            label=label,
            emoji=self.get_emoji(emoji) if emoji else None,
            style=style or ButtonStyle.gray,
            custom_id=f"autorole_button|{role.id}",
        )
        if not original_components:
            original_components = [button]
        else:
            for action_row in original_components:
                if len(action_row) < 5 and not isinstance(action_row[0], Select):
                    action_row.append(button)
                    break
            else:
                if len(original_components) == 5:
                    raise errors.ButtonsOverKill
                else:
                    original_components.append([button])  # type: ignore

        await original_message.edit(components=original_components)
        await ctx.send(content["COMMAND_ROLE_ADDED_TEXT"], hidden=True)

        await autorole.modify(
            component=[action_row.to_dict() for action_row in original_components]
        )

    @slash_subcommand(
        base="autorole",
        subcommand_group="button",
        name="remove_role",
        description="Remove button with role.",
        options=[
            create_option(
                name="name",
                description="The autorole name",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                autocomplete=True,
            ),
            create_option(
                name="label",
                description="The label of button or emoji name",
                option_type=SlashCommandOptionType.STRING,
                required=True,
                autocomplete=True,
            ),
        ],
    )
    @is_enabled()
    @bot_owner_or_permissions(manage_roles=True)
    async def autorole_button_remove_role(self, ctx: SlashContext, name: str, label: str):
        await ctx.defer(hidden=True)
        guild_data = await self.bot.get_guild_data(ctx.guild_id)
        content = get_content("AUTOROLE_BUTTON", guild_data.configuration.language)

        autorole, original_message = await self.check_buttons(ctx, guild_data, name)
        original_components = original_message.components
        for row in original_components:
            for component in row:
                if component.label == label:  # type: ignore
                    row.remove_component(component)
                    break
            else:
                for component in row:
                    emoji_name = (
                        component.emoji["name"]  # type: ignore
                        if isinstance(component.emoji, dict)  # type: ignore
                        else component.emoji.name  # type: ignore
                    )
                    if emoji_name == label:
                        row.remove_component(component)
                        break

            if len(row) == 0:
                original_components.remove(row)

        await original_message.edit(components=original_components)
        await ctx.send(content["COMMAND_ROLE_REMOVED_TEXT"], hidden=True)

        await autorole.modify(
            component=[action_row.to_dict() for action_row in original_components]
        )

    def get_emoji(self, emoji: str):
        if emoji.startswith("<"):
            _emoji = emoji.split(":")[-1].replace(">", "")
            emoji = self.bot.get_emoji(int(_emoji))
        return emoji

    async def __base_autorole_check(
        self,
        ctx: SlashContext,
        guild_data: GuildData,
        autorole_name: str,
        autorole_type: str,
        *,
        return_message: bool = True,
    ):
        exceptions = {"dropdown": errors.NotDropDown, "button": errors.NotButton}
        autoroles = guild_data.autoroles
        if not autoroles:
            raise errors.NotSavedAutoRoles
        autorole = guild_data.get_autorole(autorole_name)
        if autorole is None:
            raise errors.AutoRoleNotFound
        if autorole.autorole_type != autorole_type:
            raise exceptions[autorole_type]

        if not return_message:
            return autorole

        channel_id = autorole.channel_id
        channel: TextChannel = ctx.guild.get_channel(channel_id)
        try:
            original_message: ComponentMessage = await channel.fetch_message(  # type: ignore
                int(autorole.message_id)
            )
        except (NotFound, Forbidden):
            raise errors.AutoRoleNotFound
        return autorole, original_message

    async def check_dropdown(self, ctx: SlashContext, guild_data: GuildData, autorole_name: str):
        autorole, original_message = await self.__base_autorole_check(
            ctx, guild_data, autorole_name, "dropdown"
        )
        select_component: Select = original_message.components[0].components[0]  # type: ignore
        return autorole, select_component, original_message

    async def check_buttons(self, ctx: SlashContext, guild_data: GuildData, autorole_name: str):
        return await self.__base_autorole_check(ctx, guild_data, autorole_name, "button")


def setup(bot):
    bot.add_cog(AutoRole(bot))
