from interactions import (
    ActionRow,
    Button,
    ButtonStyle,
    Channel,
    Choice,
    CommandContext,
    ComponentContext,
    Embed,
    EmbedField,
    Extension,
    GuildMember,
    OptionType,
    Role,
    SelectMenu,
    SelectOption,
)
from interactions import extension_command as command
from interactions import extension_listener as listener
from interactions import option

from core import Asteroid, BotException, StrEnum, Mentions  # isort: skip
from utils import components_from_dict, get_emoji_from_str, create_embed  # isort: skip

COLORS = {
    "Blue": ButtonStyle.PRIMARY.value,
    "Red": ButtonStyle.DANGER.value,
    "Green": ButtonStyle.SUCCESS.value,
    "Gray": ButtonStyle.SECONDARY.value,
}


class CommandsMention(StrEnum):
    DROPDOWN_ADD_ROLE = "</autorole dropdown add-role:1000330305795792997>"
    BUTTON_ADD_ROLE = "</autorole button add-role:1000330305795792997>"


class AutoRoles(Extension):
    def __init__(self, client: Asteroid):
        # I should add type annotation since current annotation is `interactions.Client`
        self.client: Asteroid = client

    @listener
    async def on_guild_member_add(self, member: GuildMember):
        guild_data = await self.client.database.get_guild(int(member.guild_id))
        for role_id in guild_data.settings.on_join_roles:
            await member.add_role(role_id, reason="[AUTOROLE ON_JOIN] Add role")

    @listener
    async def on_component(self, ctx: ComponentContext):
        if ctx.custom_id != "select_autorole" and not ctx.custom_id.startswith("button_autorole"):
            return
        await ctx.defer(ephemeral=True)
        roles = (
            list(map(int, ctx.data.values))
            if ctx.custom_id == "select_autorole"
            else [int(ctx.custom_id.split("|")[-1])]
        )
        added_roles = []
        removed_roles = []
        code = "SELECT" if ctx.custom_id == "select_autorole" else "BUTTONS"
        for role_id in roles:
            if role_id in ctx.author.roles:
                await ctx.author.remove_role(
                    role_id, ctx.guild_id, reason=f"[AUTOROLE {code}] Add role"
                )
                removed_roles.append(role_id)
            else:
                await ctx.author.add_role(
                    role_id, ctx.guild_id, reason=f"[AUTOROLE {code}] Remove role"
                )
                added_roles.append(role_id)

        # TODO: Translate these strings
        to_send = ""
        if added_roles:
            to_send += f"Added roles: {', '.join([Mentions.ROLE.format(id=role_id) for role_id in added_roles])}"
        if removed_roles:
            to_send += f"Removed roles: {', '.join([Mentions.ROLE.format(id=role_id) for role_id in removed_roles])}"

        await ctx.send(to_send)

    @listener
    async def on_autocomplete(self, ctx: CommandContext):
        if ctx.data.name != "autorole":
            return
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        focused_option = [
            _option for _option in ctx.data.options[0].options[0].options if _option.focused
        ][0]
        autorole_type = ctx.data.options[0].name
        autorole_name = [
            _option.value
            for _option in ctx.data.options[0].options[0].options
            if _option.name == "name"
        ]
        if autorole_name:
            autorole_name = autorole_name[0]
        match focused_option.name:
            case "name":
                await ctx.populate(
                    [
                        Choice(name=autorole.name, value=autorole.name)
                        for autorole in guild_data.autoroles
                        if autorole.type == autorole_type
                    ]
                )
            case "button":
                autorole = guild_data.get_autorole(autorole_name)
                choices = []
                for action_row in autorole.component:
                    choices.extend(
                        [
                            Choice(name=button["label"], value=button["custom_id"])
                            for button in action_row["components"]
                            if focused_option.value in button["label"]
                        ]
                    )
                await ctx.populate(choices)
            case "option_name":
                autorole = guild_data.get_autorole(autorole_name)
                choices = [
                    Choice(name=option["label"], value=option["value"])
                    for option in autorole.component[0]["components"][0]["options"]
                    if focused_option.value in option["label"]
                ]
                await ctx.populate(choices)
            case "role":  # `on_join remove` command
                guild = await ctx.get_guild()
                roles = [
                    await guild.get_role(role_id) for role_id in guild_data.settings.on_join_roles
                ]
                choices = [Choice(name=role.name, value=str(role.id)) for role in roles]
                await ctx.populate(choices)

    @command(name="autorole")
    async def autorole(self, ctx: CommandContext):
        """Main command for all autoroles"""
        ...

    @autorole.subcommand()
    async def list(self, ctx: CommandContext):
        """Shows list of autoroles like dropdowns, button, on_joins"""

        def get_autoroles(type: str):
            return [
                f"`{autorole.name}`" for autorole in guild_data.autoroles if autorole.type == type
            ]

        await ctx.defer()

        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        if not guild_data.autoroles and not guild_data.settings.on_join_roles:
            raise BotException(110)
        locale = await self.client.get_locale(ctx.guild_id)

        fields = []
        if guild_data.autoroles:
            if dropdown_roles := get_autoroles("dropdown"):
                fields.append(
                    EmbedField(name=locale["AUTOROLE_DROPDOWN"], value="\n".join(dropdown_roles))
                )
            if button_roles := get_autoroles("button"):
                fields.append(
                    EmbedField(name=locale["AUTOROLE_BUTTON"], value="\n".join(button_roles))
                )
        if guild_data.settings.on_join_roles:
            fields.append(
                EmbedField(
                    name=locale["AUTOROLE_ON_JOIN"],
                    value="".join(
                        [f"<@&{role_id}>" for role_id in guild_data.settings.on_join_roles]
                    ),
                )
            )

        embed = Embed(title=locale["AUTOROLE_LIST"], fields=fields)
        await ctx.send(embeds=embed)

    @autorole.group()
    async def dropdown(self, ctx: CommandContext):
        """Group for dropdown autorole"""
        ...

    @dropdown.subcommand(name="create")
    @option(
        option_type=OptionType.STRING,
        name="name",
        description="The name of autorole",
        required=True,
    )
    @option(
        option_type=OptionType.STRING,
        name="message",
        description="The content of message",
        required=True,
    )
    @option(
        option_type=OptionType.STRING, name="placeholder", description="The dropdown placeholder"
    )
    async def dropdown_create(
        self, ctx: CommandContext, name: str, message: str, placeholder: str = None
    ):
        """Creates a dropdown autorole"""
        await ctx.defer(ephemeral=True)
        components = ActionRow(
            components=[
                SelectMenu(
                    custom_id="select_autorole",
                    placeholder=placeholder,
                    options=[
                        SelectOption(
                            label="None", value="None"
                        )  # We cannot send select without options
                    ],
                    disabled=True,
                )
            ]
        )
        await ctx.get_channel()
        _message = await ctx.channel.send(message, components=components)

        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        await guild_data.add_autorole(
            name=name,
            content=message,
            channel_id=int(ctx.channel_id),
            message_id=int(_message.id),
            type="dropdown",
            component=components._json,
        )
        locale = await self.client.get_locale(ctx.guild_id)
        embed = create_embed(
            locale["DROPDOWN_CREATED"].format(command=CommandsMention.DROPDOWN_ADD_ROLE)
        )
        await ctx.send(embeds=embed)

    @dropdown.subcommand(name="remove")
    @option(
        option_type=OptionType.STRING,
        name="name",
        description="The name of autorole",
        required=True,
        autocomplete=True,
    )
    async def dropdown_remove(self, ctx: CommandContext, name: str):
        """Removes a dropdown autorole"""
        await ctx.defer(ephemeral=True)
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        autorole = guild_data.get_autorole(name)
        if autorole is None:
            raise BotException(100)

        await guild_data.remove_autorole(autorole=autorole)
        locale = await self.client.get_locale(ctx.guild_id)
        embed = create_embed(locale["DROPDOWN_DELETED"])
        await ctx.send(embeds=embed)

    @dropdown.subcommand(name="add-role")
    @option(
        option_type=OptionType.STRING,
        name="name",
        description="The name of autorole",
        required=True,
        autocomplete=True,
    )
    @option(option_type=OptionType.ROLE, name="role", description="The role to set", required=True)
    @option(
        option_type=OptionType.STRING,
        name="option_name",
        description="The name of option. Default is a role name",
    )
    @option(option_type=OptionType.STRING, name="emoji", description="The emoji for option")
    @option(
        option_type=OptionType.STRING, name="description", description="The description of option"
    )
    async def dropdown_add_role(
        self,
        ctx: CommandContext,
        name: str,
        role: Role,
        option_name: str = None,
        emoji: str = None,
        description: str = None,
    ):
        """Adds a role to dropdown"""
        await ctx.defer(ephemeral=True)
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        autorole = guild_data.get_autorole(name)
        if autorole is None:
            raise BotException(100)

        option = SelectOption(
            label=option_name or role.name,
            value=str(role.id),
            emoji=get_emoji_from_str(emoji),
            description=description,
        )
        await ctx.get_guild()
        channel: Channel = await self.client.get(Channel, object_id=autorole.channel_id)
        message = await channel.get_message(autorole.message_id)
        components = components_from_dict(message.components)
        select = components[0].components[0]
        options = select.options
        if len(options) == 25:
            raise BotException(104)
        if options[0].label == "None":
            options.clear()
            select.disabled = False
        options.append(option)  # It's doesn't update json
        select.options = options  # So I need to do this thing
        await message.edit(components=components)
        autorole.component = [component._json for component in components]
        await autorole.update()

        locale = await self.client.get_locale(ctx.guild_id)
        embed = create_embed(locale["OPTION_ADDED"])
        await ctx.send(embeds=embed)

    @dropdown.subcommand(name="remove-role")
    @option(
        option_type=OptionType.STRING,
        name="name",
        description="The name of autorole",
        required=True,
        autocomplete=True,
    )
    @option(
        option_type=OptionType.STRING,
        name="option_name",
        description="The option to remove",
        required=True,
        autocomplete=True,
    )
    async def dropdown_remove_role(self, ctx: CommandContext, name: str, option_name: str):
        """Removes a role of dropdown"""
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        autorole = guild_data.get_autorole(name)
        if autorole is None:
            raise BotException(100)
        await ctx.get_guild()
        channel: Channel = await self.client.get(Channel, object_id=autorole.channel_id)
        message = await channel.get_message(autorole.message_id)
        components = components_from_dict(message.components)
        select = components[0].components[0]
        options = select.options

        for _option in options:
            if _option.value == option_name:  # option_name is value lol
                options.remove(_option)
                break
        else:
            raise BotException(103)

        if len(options) == 0:
            options.append(SelectOption(label="None", value="None"))
            select.disabled = True

        select.options = options
        await message.edit(components=components)
        autorole.component = [component._json for component in components]
        await autorole.update()

        locale = await self.client.get_locale(ctx.guild_id)
        embed = create_embed(locale["OPTION_REMOVED"])
        await ctx.send(embeds=embed)

    @autorole.group()
    async def button(self, ctx: CommandContext):
        """Group for button autorole"""
        ...

    @button.subcommand(name="create")
    @option(
        option_type=OptionType.STRING,
        name="name",
        description="The name of autorole",
        required=True,
    )
    @option(
        option_type=OptionType.STRING,
        name="message",
        description="The content of message",
        required=True,
    )
    async def button_create(self, ctx: CommandContext, name: str, message: str):
        """Creates a button autorole"""
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))

        await ctx.get_channel()
        _message = await ctx.channel.send(content=message)

        await guild_data.add_autorole(
            name=name,
            content=message,
            channel_id=int(ctx.channel_id),
            message_id=int(_message.id),
            component=[],
            type="button",
        )
        locale = await self.client.get_locale(ctx.guild_id)
        embed = create_embed(
            locale["BUTTON_CREATED"].format(command=CommandsMention.BUTTON_ADD_ROLE)
        )
        await ctx.send(embeds=embed)

    @button.subcommand(name="remove")
    @option(
        option_type=OptionType.STRING,
        name="name",
        description="The name of autorole",
        required=True,
        autocomplete=True,
    )
    async def button_remove(self, ctx: CommandContext, name: str):
        """Removes a dropdown autorole"""
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        autorole = guild_data.get_autorole(name)
        if autorole is None:
            raise BotException(100)

        await guild_data.remove_autorole(autorole=autorole)

        locale = await self.client.get_locale(ctx.guild_id)
        embed = create_embed(locale["BUTTON_DELETED"])
        await ctx.send(embeds=embed)

    @button.subcommand(name="add-role")
    @option(
        option_type=OptionType.STRING,
        name="name",
        description="The name of autorole",
        required=True,
        autocomplete=True,
    )
    @option(option_type=OptionType.ROLE, name="role", description="The role to set", required=True)
    @option(
        option_type=OptionType.STRING,
        name="label",
        description="The label of button. Default is a role name",
    )
    @option(option_type=OptionType.STRING, name="emoji", description="The emoji for button")
    @option(
        option_type=OptionType.INTEGER,
        name="color",
        description="The color for button. Default is Gray",
        choices=[Choice(name=name, value=value) for name, value in COLORS.items()],
    )
    async def button_add_role(
        self,
        ctx: CommandContext,
        name: str,
        role: Role,
        label: str = None,
        emoji: str = None,
        color: int = None,
    ):
        """Adds a role to button autorole"""
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        autorole = guild_data.get_autorole(name)
        if autorole is None:
            raise BotException(100)

        button = Button(
            label=label or role.name,
            custom_id=f"button_autorole|{role.id}",
            emoji=get_emoji_from_str(emoji),
            style=color if color is not None else ButtonStyle.SECONDARY,
        )

        channel: Channel = await self.client.get(Channel, object_id=autorole.channel_id)
        message = await channel.get_message(autorole.message_id)

        components = components_from_dict(message.components)
        if not components:
            components = [ActionRow(components=[button])]
        else:
            for action_row in components:
                if len(action_row.components) < 5:
                    _components = action_row.components  # I need to update ._json
                    _components.append(
                        button
                    )  # Simply action_row.components.append(button) does not update ._json
                    action_row.components = _components  # So I can only wait fix
                    break
            else:
                if len(components) < 5:
                    components.append(ActionRow(components=[button]))
                else:
                    raise BotException(105)
        autorole.component = [_._json for _ in components]
        await autorole.update()
        await message.edit(components=components)

        locale = await self.client.get_locale(ctx.guild_id)
        embed = create_embed(locale["BUTTON_ADDED"])
        await ctx.send(embeds=embed)

    @button.subcommand(name="remove-role")
    @option(
        option_type=OptionType.STRING,
        name="name",
        description="The name of autorole",
        required=True,
        autocomplete=True,
    )
    @option(
        option_type=OptionType.STRING,
        name="button",
        description="The button to remove",
        required=True,
        autocomplete=True,
    )
    async def button_remove_role(self, ctx: CommandContext, name: str, button: str):
        """Removes a role of button autorole"""
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        autorole = guild_data.get_autorole(name)
        if autorole is None:
            raise BotException(100)

        channel: Channel = await self.client.get(Channel, object_id=autorole.channel_id)
        message = await channel.get_message(autorole.message_id)
        components = components_from_dict(message.components)
        if not components:
            raise BotException(108)

        _break = False
        for action_row in components:
            for _button in action_row.components:
                if _button.custom_id == button:
                    _components = action_row.components  # I need to update ._json
                    _components.remove(
                        _button
                    )  # Simply action_row.components.append(button) does not update ._json
                    action_row.components = _components  # So I can only wait fix
                    _break = True
            if _break:
                break
        else:
            raise BotException(106)
        await message.edit(components=components)
        autorole.component = [_._json for _ in components]
        await autorole.update()

        locale = await self.client.get_locale(ctx.guild_id)
        embed = create_embed(locale["BUTTON_REMOVED"])
        await ctx.send(embeds=embed)

    @autorole.group()
    async def on_join(self, ctx: CommandContext):
        """Group for on_join roles"""
        ...

    @on_join.subcommand(name="add")
    @option(option_type=OptionType.ROLE, name="role", description="The role to add", required=True)
    async def on_join_add(self, ctx: CommandContext, role: Role):
        """Adds a role"""
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        role_id = int(role.id)
        roles = guild_data.settings.on_join_roles
        if role_id in roles:
            raise BotException(109)

        guild_data.settings.on_join_roles.append(role_id)
        await guild_data.settings.update()
        locale = await self.client.get_locale(ctx.guild_id)
        embed = create_embed(locale["ON_JOIN_ROLE_ADDED"].format(role=role.mention))
        await ctx.send(embeds=embed)

    @on_join.subcommand(name="remove")
    @option(
        option_type=OptionType.STRING,  # Not int because snowflake is too long.
        name="role",
        description="The role to remove",
        required=True,
        autocomplete=True,
    )
    async def on_join_remove(self, ctx: CommandContext, role: str):
        """Removes a role"""
        await ctx.defer()
        role_id = int(role)
        guild_data = await self.client.database.get_guild(int(ctx.guild_id))
        if role_id not in guild_data.settings.on_join_roles:
            raise BotException(107)

        guild_data.settings.on_join_roles.remove(role_id)
        await guild_data.settings.update()
        locale = await self.client.get_locale(ctx.guild_id)
        embed = create_embed(
            locale["ON_JOIN_ROLE_REMOVED"].format(role=Mentions.ROLE.format(id=role_id))
        )
        await ctx.send(embeds=embed)


def setup(client):
    AutoRoles(client)
